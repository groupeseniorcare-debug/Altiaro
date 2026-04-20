"""
AI Copilot : assistant conversationnel Claude Sonnet 4.5 avec function calling maison (ReAct).

À chaque tour, Claude renvoie un JSON soit :
  {"thought": "...", "function_call": {"name": "...", "arguments": {...}}}
  {"thought": "...", "final_answer": "texte markdown à afficher au user"}

Le backend exécute la fonction demandée (scoped au rôle de l'utilisateur), renvoie le résultat à Claude,
et recommence jusqu'à `final_answer` ou MAX_ITERATIONS.

Sessions persistées dans `copilot_messages` pour l'historique multi-turn.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from deps import db, get_current_user, EMERGENT_LLM_KEY

logger = logging.getLogger("conceptfactory.copilot")
router = APIRouter(prefix="/copilot")

MAX_ITERATIONS = 6


# ================= Tool registry ================= #
class Tool:
    def __init__(self, name: str, description: str, parameters: dict, handler, admin_only: bool = False):
        self.name = name
        self.description = description
        self.parameters = parameters  # JSON schema-like
        self.handler = handler
        self.admin_only = admin_only


def _trim_doc(doc: dict, keep: list) -> dict:
    return {k: doc.get(k) for k in keep if k in doc}


async def _can_access_site(user: dict, site_id: str) -> Optional[dict]:
    site = await db.sites.find_one({"id": site_id}, {"_id": 0})
    if not site:
        return None
    if user["role"] == "admin":
        return site
    if site.get("operator_id") == user["id"]:
        return site
    return None


# ---- Handlers ---- #
async def h_list_my_sites(user: dict, args: dict) -> dict:
    q = {} if user["role"] == "admin" else {"operator_id": user["id"]}
    sites = await db.sites.find(q, {"_id": 0}).sort("created_at", -1).to_list(100)
    return {
        "count": len(sites),
        "sites": [
            _trim_doc(s, ["id", "name", "niche", "status", "selected_countries", "daily_budget_eur",
                          "custom_domain", "custom_domain_verified", "scale_batch_id", "scaled_from"])
            for s in sites
        ],
    }


async def h_get_site_details(user: dict, args: dict) -> dict:
    site_id = args.get("site_id")
    site = await _can_access_site(user, site_id)
    if not site:
        return {"error": "site introuvable ou accès refusé"}

    products_total = await db.products.count_documents({"site_id": site_id})
    products_active = await db.products.count_documents({"site_id": site_id, "status": "active"})
    orders_total = await db.orders.count_documents({"site_id": site_id})
    steps_validated = await db.steps.count_documents({"site_id": site_id, "status": "validated"})

    return {
        **_trim_doc(site, ["id", "name", "niche", "status", "selected_countries",
                           "daily_budget_eur", "custom_domain", "custom_domain_verified",
                           "primary_language", "scale_batch_id", "scaled_from"]),
        "products_total": products_total,
        "products_active": products_active,
        "orders_total": orders_total,
        "steps_validated": steps_validated,
        "steps_total": 50,
    }


async def h_get_site_orders(user: dict, args: dict) -> dict:
    site_id = args.get("site_id")
    limit = min(int(args.get("limit") or 10), 50)
    if not await _can_access_site(user, site_id):
        return {"error": "site introuvable ou accès refusé"}
    orders = (
        await db.orders.find(
            {"site_id": site_id},
            {"_id": 0, "_meta_ip": 0, "items": 0},  # skip heavy fields
        )
        .sort("created_at", -1)
        .limit(limit)
        .to_list(limit)
    )
    return {
        "site_id": site_id,
        "count": len(orders),
        "orders": [
            _trim_doc(o, ["id", "order_number", "status", "total", "currency", "created_at"])
            for o in orders
        ],
    }


async def h_get_site_products(user: dict, args: dict) -> dict:
    site_id = args.get("site_id")
    status = args.get("status")
    if not await _can_access_site(user, site_id):
        return {"error": "site introuvable ou accès refusé"}
    q: dict = {"site_id": site_id}
    if status:
        q["status"] = status
    prods = await db.products.find(q, {"_id": 0, "description": 0}).to_list(500)
    return {
        "site_id": site_id,
        "count": len(prods),
        "products": [
            {
                "id": p["id"],
                "name": p.get("name", {}).get("fr") or p.get("name", {}).get("en") or "—",
                "price": p.get("price"),
                "currency": p.get("currency"),
                "status": p.get("status"),
                "featured": p.get("featured"),
            }
            for p in prods
        ],
    }


async def h_update_product_price(user: dict, args: dict) -> dict:
    site_id = args.get("site_id")
    product_id = args.get("product_id")
    new_price = args.get("new_price")
    try:
        new_price = float(new_price)
    except Exception:
        return {"error": "new_price doit être un nombre"}
    if new_price < 0 or new_price > 100000:
        return {"error": f"prix hors bornes (0-100000) : {new_price}"}
    if not await _can_access_site(user, site_id):
        return {"error": "site introuvable ou accès refusé"}
    result = await db.products.update_one(
        {"id": product_id, "site_id": site_id},
        {"$set": {
            "price": new_price,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }},
    )
    if result.matched_count == 0:
        return {"error": "produit introuvable"}
    return {"ok": True, "site_id": site_id, "product_id": product_id, "new_price": new_price}


async def h_batch_update_prices(user: dict, args: dict) -> dict:
    site_id = args.get("site_id")
    pct_change = args.get("pct_change")
    status_filter = args.get("status_filter")
    try:
        pct = float(pct_change)
    except Exception:
        return {"error": "pct_change doit être un nombre (ex: 10 pour +10%, -5 pour -5%)"}
    if abs(pct) > 50:
        return {"error": f"variation demandée trop large ({pct}%). Max ±50% pour éviter les erreurs."}
    if not await _can_access_site(user, site_id):
        return {"error": "site introuvable ou accès refusé"}

    q: dict = {"site_id": site_id}
    if status_filter:
        q["status"] = status_filter
    prods = await db.products.find(q, {"_id": 0, "id": 1, "price": 1}).to_list(500)
    factor = 1 + (pct / 100.0)
    updated = 0
    for p in prods:
        old = float(p.get("price") or 0)
        new = round(old * factor, 2)
        if new != old:
            await db.products.update_one(
                {"id": p["id"]},
                {"$set": {"price": new, "updated_at": datetime.now(timezone.utc).isoformat()}},
            )
            updated += 1
    return {
        "ok": True,
        "site_id": site_id,
        "pct_change": pct,
        "status_filter": status_filter or "ALL",
        "products_checked": len(prods),
        "products_updated": updated,
    }


async def h_search_sites(user: dict, args: dict) -> dict:
    query = (args.get("query") or "").strip()
    if not query:
        return {"error": "query vide"}
    base: dict = {} if user["role"] == "admin" else {"operator_id": user["id"]}
    pattern = {"$regex": re.escape(query), "$options": "i"}
    base["$or"] = [{"name": pattern}, {"niche": pattern}]
    sites = await db.sites.find(base, {"_id": 0}).limit(20).to_list(20)
    return {
        "query": query,
        "count": len(sites),
        "sites": [_trim_doc(s, ["id", "name", "niche", "status", "selected_countries"]) for s in sites],
    }


async def h_list_scale_family(user: dict, args: dict) -> dict:
    site_id = args.get("site_id")
    site = await _can_access_site(user, site_id)
    if not site:
        return {"error": "site introuvable ou accès refusé"}
    batch_id = site.get("scale_batch_id")
    source_id = site.get("scaled_from") or site_id
    if batch_id:
        siblings = await db.sites.find(
            {"$or": [{"scale_batch_id": batch_id}, {"id": source_id}]},
            {"_id": 0},
        ).to_list(20)
    else:
        children = await db.sites.find({"scaled_from": site_id}, {"_id": 0}).to_list(20)
        siblings = [site] + children
    return {
        "source_id": source_id,
        "batch_id": batch_id,
        "count": len(siblings),
        "siblings": [_trim_doc(s, ["id", "name", "selected_countries", "primary_language", "status"])
                     for s in siblings],
    }


async def h_empire_overview(user: dict, args: dict) -> dict:
    if user["role"] != "admin":
        return {"error": "Cette vue est réservée à l'admin."}
    # Lightweight version — minimal KPIs
    sites = await db.sites.count_documents({})
    active = await db.sites.count_documents({"status": "active"})
    orders = await db.orders.find({"status": {"$in": ["paid", "shipped", "delivered"]}}, {"_id": 0, "total": 1, "site_id": 1}).to_list(50000)
    gmv = sum(o.get("total", 0) for o in orders)
    return {
        "total_sites": sites,
        "active_sites": active,
        "total_orders_settled": len(orders),
        "total_gmv_eur": round(gmv, 2),
        "admin_share_eur": round(gmv * 0.5, 2),
        "concepteur_share_eur": round(gmv - gmv * 0.5, 2),
    }


TOOLS: List[Tool] = [
    Tool("list_my_sites", "Liste tous les sites auxquels l'utilisateur a accès (admin = tous, concepteur = les siens).",
         {"type": "object", "properties": {}}, h_list_my_sites),
    Tool("get_site_details", "Détails complets d'un site (progress, nb produits, nb commandes).",
         {"type": "object", "properties": {"site_id": {"type": "string"}}, "required": ["site_id"]}, h_get_site_details),
    Tool("get_site_orders", "Liste les commandes récentes d'un site.",
         {"type": "object", "properties": {"site_id": {"type": "string"}, "limit": {"type": "integer", "default": 10}}, "required": ["site_id"]}, h_get_site_orders),
    Tool("get_site_products", "Liste les produits d'un site. Filtre optionnel sur status (draft/active/archived).",
         {"type": "object", "properties": {"site_id": {"type": "string"}, "status": {"type": "string"}}, "required": ["site_id"]}, h_get_site_products),
    Tool("update_product_price", "Met à jour le prix d'un seul produit (valeur absolue, en devise du site).",
         {"type": "object", "properties": {"site_id": {"type": "string"}, "product_id": {"type": "string"}, "new_price": {"type": "number"}}, "required": ["site_id", "product_id", "new_price"]}, h_update_product_price),
    Tool("batch_update_prices", "Met à jour le prix de TOUS les produits d'un site en pourcentage (±50% max). status_filter optionnel (ex: 'active').",
         {"type": "object", "properties": {"site_id": {"type": "string"}, "pct_change": {"type": "number"}, "status_filter": {"type": "string"}}, "required": ["site_id", "pct_change"]}, h_batch_update_prices),
    Tool("search_sites", "Recherche des sites par nom ou niche (regex insensible à la casse).",
         {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}, h_search_sites),
    Tool("list_scale_family", "Liste tous les sites clonés de la même source (famille scaled cross-pays).",
         {"type": "object", "properties": {"site_id": {"type": "string"}}, "required": ["site_id"]}, h_list_scale_family),
    Tool("empire_overview", "Vue macro Admin : KPIs cross-pays, total GMV, split 50/50.",
         {"type": "object", "properties": {}}, h_empire_overview, admin_only=True),
]

TOOLS_BY_NAME = {t.name: t for t in TOOLS}


def _tools_catalog_for_prompt(user_role: str) -> str:
    """Serialize the tools catalog as a clear English list Claude can reason about."""
    lines = []
    for t in TOOLS:
        if t.admin_only and user_role != "admin":
            continue
        params = json.dumps(t.parameters, ensure_ascii=False)
        lines.append(f"- {t.name}({params}) — {t.description}")
    return "\n".join(lines)


SYSTEM_PROMPT_TEMPLATE = """Tu es CONCEPT COPILOT, l'assistant IA de Concept Factory (SaaS e-commerce multi-tenant Silver Economy EU).

Rôle utilisateur : {role}
Utilisateur : {user_name} ({user_email})

OUTILS DISPONIBLES (tu dois utiliser EXACTEMENT ces noms, pas de variante) :
{tools}

À CHAQUE TOUR, tu réponds STRICTEMENT en JSON avec l'une de ces 2 formes :

1) Appel d'outil (utilise UN des noms ci-dessus, pas d'invention) :
{{"thought": "brève réflexion", "function_call": {{"name": "nom_exact_de_la_liste", "arguments": {{...}}}}}}

2) Réponse finale à l'utilisateur (markdown, max ~200 mots, français) :
{{"thought": "brève réflexion", "final_answer": "Réponse markdown"}}

Règles :
- N'invente JAMAIS de nom d'outil : utilise uniquement les noms listés ci-dessus.
- N'invente JAMAIS d'ID — utilise search_sites ou list_my_sites d'abord.
- Pour les opérations d'écriture (update_product_price, batch_update_prices), enchaîne sans redemander si l'utilisateur a été explicite.
- Réponds toujours en français, ton amical + concret.
- Si tu n'as pas assez d'info, pose UNE question précise dans final_answer.
- Pas de markdown dans thought.
- Ne cite pas les IDs techniques dans final_answer sauf si demandé.
- Si un outil retourne une erreur 'outil inconnu', regarde la liste ci-dessus et utilise le bon nom.
"""


JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def _strip_json_fence(text: str) -> str:
    return JSON_FENCE_RE.sub("", text).strip()


def _extract_first_json(text: str) -> Optional[dict]:
    """Find the first balanced JSON object in `text`. Claude sometimes adds prose."""
    text = _strip_json_fence(text)
    # Fast path
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    depth = 0
    start = -1
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start != -1:
                try:
                    return json.loads(text[start:i + 1])
                except json.JSONDecodeError:
                    start = -1
    return None


async def _call_claude(system: str, history: List[dict], session_id: str) -> str:
    """Send full history + fresh user turn, get raw text back."""
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    # We feed all prior turns as "initial_messages" + send the latest user message
    if not history:
        raise ValueError("history must not be empty")
    *prior, latest = history
    initial = [{"role": m["role"], "content": m["content"]} for m in prior]
    chat = (
        LlmChat(api_key=EMERGENT_LLM_KEY, session_id=session_id,
                system_message=system, initial_messages=initial)
        .with_model("anthropic", "claude-sonnet-4-5-20250929")
    )
    msg = UserMessage(text=latest["content"])
    try:
        resp = await asyncio.wait_for(chat.send_message(msg), timeout=60)
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Le Copilot met trop de temps à répondre. Réessayez.")
    except Exception as e:
        err = str(e)
        if "Budget has been exceeded" in err or "budget" in err.lower():
            raise HTTPException(status_code=402, detail="Budget LLM épuisé. Profile → Universal Key → Add Balance.")
        logger.exception("Copilot LLM call failed")
        raise HTTPException(status_code=500, detail=f"Erreur Copilot : {err[:150]}")
    return resp if isinstance(resp, str) else str(resp)


# ================= API Models ================= #
class ChatInput(BaseModel):
    session_id: Optional[str] = None
    message: str


class MessageDoc(BaseModel):
    role: str  # user | assistant | tool
    content: str  # for tool: JSON of {name, result}. for assistant: final_answer text.
    kind: Optional[str] = None  # "final" | "tool_call" (assistant subkind)
    tool_name: Optional[str] = None
    tool_args: Optional[Dict[str, Any]] = None
    tool_result: Optional[Any] = None
    timestamp: Optional[str] = None


# ================= Routes ================= #
@router.post("/chat")
async def copilot_chat(data: ChatInput, user: dict = Depends(get_current_user)):
    """Run a ReAct loop : user msg → Claude → optional tool calls → final answer."""
    session_id = data.session_id or str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    # Fetch existing history (persisted)
    past = await db.copilot_messages.find(
        {"user_id": user["id"], "session_id": session_id},
        {"_id": 0},
    ).sort("ts_seq", 1).to_list(500)

    # Build "history" in provider format : user / assistant text turns (skip tool & internal reasoning from past)
    history: List[dict] = []
    for m in past:
        if m.get("role") in ("user", "assistant_final"):
            r = "user" if m["role"] == "user" else "assistant"
            history.append({"role": r, "content": m.get("content", "")})

    # Append the new user message
    history.append({"role": "user", "content": data.message})
    await _persist_message(user["id"], session_id, {
        "role": "user",
        "content": data.message,
        "ts": now,
    })

    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        role=user["role"],
        user_name=user.get("name", ""),
        user_email=user.get("email", ""),
        tools=_tools_catalog_for_prompt(user["role"]),
    )

    tool_trace: List[Dict[str, Any]] = []
    final_answer: Optional[str] = None

    for step in range(MAX_ITERATIONS):
        raw = await _call_claude(system_prompt, history, session_id)
        parsed = _extract_first_json(raw)
        if not parsed:
            # Fallback : treat the raw text as the final answer to avoid locking the user
            final_answer = raw.strip()
            history.append({"role": "assistant", "content": raw})
            break

        # Record the thought (internal)
        thought = parsed.get("thought", "")

        if "final_answer" in parsed:
            final_answer = str(parsed["final_answer"]).strip() or "(réponse vide)"
            history.append({"role": "assistant", "content": json.dumps(parsed, ensure_ascii=False)})
            break

        if "function_call" in parsed:
            fc = parsed["function_call"] or {}
            tool_name = fc.get("name")
            tool_args = fc.get("arguments") or {}
            tool = TOOLS_BY_NAME.get(tool_name)
            if not tool:
                visible = [t.name for t in TOOLS if not t.admin_only or user["role"] == "admin"]
                result = {
                    "error": f"outil inconnu : {tool_name!r}",
                    "hint": f"Noms valides (copie exactement) : {visible}",
                }
            elif tool.admin_only and user["role"] != "admin":
                result = {"error": "outil réservé à l'admin"}
            else:
                try:
                    result = await tool.handler(user, tool_args)
                except Exception as e:
                    logger.exception(f"Tool {tool_name} failed")
                    result = {"error": f"exception : {str(e)[:200]}"}

            tool_trace.append({
                "name": tool_name,
                "arguments": tool_args,
                "result": result,
                "thought": thought,
            })
            # Feed result back to Claude
            history.append({"role": "assistant", "content": json.dumps(parsed, ensure_ascii=False)})
            history.append({
                "role": "user",
                "content": json.dumps(
                    {"tool_name": tool_name, "tool_result": result}, ensure_ascii=False
                ),
            })
            continue

        # Unknown shape → bail
        final_answer = raw.strip()
        history.append({"role": "assistant", "content": raw})
        break

    if final_answer is None:
        final_answer = (
            "⚠️ Je n'ai pas pu aboutir à une réponse en "
            f"{MAX_ITERATIONS} étapes. Reformulez ou simplifiez la demande."
        )

    # Persist the final assistant message + tool trace
    await _persist_message(user["id"], session_id, {
        "role": "assistant_final",
        "content": final_answer,
        "tool_trace": tool_trace,
        "ts": datetime.now(timezone.utc).isoformat(),
    })

    return {
        "session_id": session_id,
        "final_answer": final_answer,
        "tool_trace": tool_trace,
    }


async def _persist_message(user_id: str, session_id: str, msg: dict):
    # Monotonic ts_seq for ordering
    last = await db.copilot_messages.find_one(
        {"user_id": user_id, "session_id": session_id},
        {"_id": 0, "ts_seq": 1},
        sort=[("ts_seq", -1)],
    )
    seq = (last.get("ts_seq", 0) if last else 0) + 1
    doc = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "session_id": session_id,
        "ts_seq": seq,
        **msg,
    }
    await db.copilot_messages.insert_one(doc)


@router.get("/sessions")
async def list_sessions(user: dict = Depends(get_current_user)):
    """Return all sessions for the current user with last message preview."""
    pipeline = [
        {"$match": {"user_id": user["id"]}},
        {"$sort": {"ts_seq": -1}},
        {"$group": {
            "_id": "$session_id",
            "last_msg": {"$first": "$content"},
            "last_role": {"$first": "$role"},
            "last_ts": {"$first": "$ts"},
            "count": {"$sum": 1},
        }},
        {"$sort": {"last_ts": -1}},
        {"$limit": 20},
    ]
    cur = db.copilot_messages.aggregate(pipeline)
    out = []
    async for s in cur:
        out.append({
            "session_id": s["_id"],
            "message_count": s["count"],
            "last_message_preview": (s.get("last_msg") or "")[:120],
            "last_role": s.get("last_role"),
            "last_at": s.get("last_ts"),
        })
    return out


@router.get("/sessions/{session_id}")
async def get_session(session_id: str, user: dict = Depends(get_current_user)):
    msgs = await db.copilot_messages.find(
        {"user_id": user["id"], "session_id": session_id},
        {"_id": 0},
    ).sort("ts_seq", 1).to_list(500)
    return {"session_id": session_id, "messages": msgs}


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str, user: dict = Depends(get_current_user)):
    res = await db.copilot_messages.delete_many(
        {"user_id": user["id"], "session_id": session_id},
    )
    return {"deleted": res.deleted_count}


@router.get("/tools")
async def list_tools(user: dict = Depends(get_current_user)):
    """Expose available tools so the UI can show capabilities."""
    return [
        {"name": t.name, "description": t.description, "admin_only": t.admin_only}
        for t in TOOLS
        if not t.admin_only or user["role"] == "admin"
    ]
