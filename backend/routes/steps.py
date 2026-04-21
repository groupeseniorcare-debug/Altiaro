"""Steps workflow (list, update, submit, validate, reject, execute IA, upload files)."""
import asyncio
import uuid
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from pydantic import BaseModel

from deps import (
    db, get_current_user, require_admin, _check_site_access,
    EMERGENT_LLM_KEY, UPLOAD_DIR,
)
from routes.step_side_effects import schedule_side_effect

router = APIRouter()
logger = logging.getLogger("conceptfactory.steps")


class StepUpdateInput(BaseModel):
    deliverable_url: Optional[str] = None
    deliverable_notes: Optional[str] = None
    ai_response: Optional[str] = None


class StepValidateInput(BaseModel):
    comment: Optional[str] = ""


class StepRejectInput(BaseModel):
    reason: str


class StepExecuteInput(BaseModel):
    model_provider: str = "anthropic"
    model_name: str = "claude-sonnet-4-5-20250929"
    user_variables: Optional[dict] = None


@router.get("/sites/{site_id}/steps")
async def list_steps(site_id: str, user: dict = Depends(get_current_user)):
    await _check_site_access(site_id, user)
    steps = await db.steps.find({"site_id": site_id}, {"_id": 0}).sort("number", 1).to_list(200)
    return steps


@router.get("/steps/{step_id}")
async def get_step(step_id: str, user: dict = Depends(get_current_user)):
    step = await db.steps.find_one({"id": step_id}, {"_id": 0})
    if not step:
        raise HTTPException(status_code=404, detail="Étape introuvable")
    await _check_site_access(step["site_id"], user)
    return step


@router.patch("/steps/{step_id}")
async def update_step(step_id: str, data: StepUpdateInput, user: dict = Depends(get_current_user)):
    step = await db.steps.find_one({"id": step_id}, {"_id": 0})
    if not step:
        raise HTTPException(status_code=404, detail="Étape introuvable")
    await _check_site_access(step["site_id"], user)
    if step["status"] == "locked":
        raise HTTPException(status_code=400, detail="Cette étape est verrouillée")
    if step["status"] == "validated":
        raise HTTPException(status_code=400, detail="Cette étape est déjà validée")

    update = {k: v for k, v in data.model_dump().items() if v is not None}
    update["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.steps.update_one({"id": step_id}, {"$set": update})
    return await db.steps.find_one({"id": step_id}, {"_id": 0})


@router.post("/steps/{step_id}/submit")
async def submit_step(step_id: str, user: dict = Depends(get_current_user)):
    step = await db.steps.find_one({"id": step_id}, {"_id": 0})
    if not step:
        raise HTTPException(status_code=404, detail="Étape introuvable")
    await _check_site_access(step["site_id"], user)
    if step["status"] == "locked":
        raise HTTPException(status_code=400, detail="Étape verrouillée")
    if step["status"] == "validated":
        raise HTTPException(status_code=400, detail="Étape déjà validée")
    if not (step.get("deliverable_url") or step.get("deliverable_notes") or step.get("deliverable_files") or step.get("ai_response")):
        raise HTTPException(status_code=400, detail="Ajoutez au moins un livrable (URL, notes, fichier ou réponse IA) avant de valider")

    now = datetime.now(timezone.utc).isoformat()
    await db.steps.update_one(
        {"id": step_id},
        {"$set": {
            "status": "validated",
            "submitted_at": now,
            "validated_at": now,
            "validated_by": user["id"],
            "updated_at": now,
        }},
    )
    next_step = await db.steps.find_one({"site_id": step["site_id"], "number": step["number"] + 1})
    if next_step and next_step["status"] == "locked":
        await db.steps.update_one(
            {"id": next_step["id"]},
            {"$set": {"status": "in_progress", "updated_at": now}},
        )
    updated_step = await db.steps.find_one({"id": step_id}, {"_id": 0})
    # Fire-and-forget : apply automatic side effects for key steps (#6/#9/#16/#17)
    if updated_step:
        schedule_side_effect(updated_step)
    return updated_step


@router.post("/steps/{step_id}/validate")
async def validate_step(step_id: str, data: StepValidateInput, admin: dict = Depends(require_admin)):
    step = await db.steps.find_one({"id": step_id}, {"_id": 0})
    if not step:
        raise HTTPException(status_code=404, detail="Étape introuvable")
    now = datetime.now(timezone.utc).isoformat()
    await db.steps.update_one(
        {"id": step_id},
        {"$set": {
            "status": "validated",
            "validated_at": now,
            "validated_by": admin["id"],
            "validation_comment": data.comment or "",
            "updated_at": now,
        }},
    )
    next_step = await db.steps.find_one({"site_id": step["site_id"], "number": step["number"] + 1})
    if next_step and next_step["status"] == "locked":
        await db.steps.update_one(
            {"id": next_step["id"]},
            {"$set": {"status": "in_progress", "updated_at": now}},
        )
    updated_step = await db.steps.find_one({"id": step_id}, {"_id": 0})
    if updated_step:
        schedule_side_effect(updated_step)
    return updated_step


@router.post("/steps/{step_id}/reject")
async def reject_step(step_id: str, data: StepRejectInput, admin: dict = Depends(require_admin)):
    step = await db.steps.find_one({"id": step_id}, {"_id": 0})
    if not step:
        raise HTTPException(status_code=404, detail="Étape introuvable")
    now = datetime.now(timezone.utc).isoformat()
    await db.steps.update_one(
        {"id": step_id},
        {"$set": {
            "status": "rejected",
            "rejection_reason": data.reason,
            "validated_by": admin["id"],
            "updated_at": now,
        }},
    )
    return await db.steps.find_one({"id": step_id}, {"_id": 0})


@router.post("/steps/{step_id}/execute")
async def execute_step_with_ai(step_id: str, data: StepExecuteInput, user: dict = Depends(get_current_user)):
    step = await db.steps.find_one({"id": step_id}, {"_id": 0})
    if not step:
        raise HTTPException(status_code=404, detail="Étape introuvable")
    site = await _check_site_access(step["site_id"], user)
    if step["status"] == "locked":
        raise HTTPException(status_code=400, detail="Étape verrouillée")

    variables = data.user_variables or {}
    prompt_text = step["prompt"]
    defaults = {
        "[NICHE]": site.get("niche", ""),
        "[NOM_MARQUE]": site.get("name", ""),
        "[NOM]": site.get("name", ""),
        "[NOM_CHOISI]": site.get("name", ""),
        "[DOMAINE]": site.get("domain", ""),
        "[URL_ADMIN]": site.get("shopify_url", ""),
        "[MON_SHOPIFY]": site.get("shopify_url", ""),
    }
    for k, v in defaults.items():
        if v:
            prompt_text = prompt_text.replace(k, str(v))
    for k, v in variables.items():
        prompt_text = prompt_text.replace(f"[{k}]", str(v)).replace(f"{{{k}}}", str(v))

    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        system_msg = (
            "Tu es un expert e-commerce, SEO, copywriting et ops. Tu réponds en français. "
            "Tu fournis des livrables concrets, structurés, prêts à l'emploi. "
            "Tu utilises des tableaux markdown, des listes, et des exemples chiffrés quand pertinent."
        )
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"step-{step_id}",
            system_message=system_msg,
        ).with_model(data.model_provider, data.model_name)
        message = UserMessage(text=prompt_text)
        response = await asyncio.wait_for(chat.send_message(message), timeout=50)
        ai_text = response if isinstance(response, str) else str(response)
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail="Le modèle met trop de temps à répondre (>50s). Réessayez ou changez de modèle."
        )
    except Exception as e:
        logger.exception("LLM execution failed")
        err_str = str(e)
        if "Budget has been exceeded" in err_str or "budget" in err_str.lower():
            raise HTTPException(
                status_code=402,
                detail="Budget Emergent LLM Key épuisé. Allez dans Profile → Universal Key → Add Balance pour recharger, puis réessayez."
            )
        if "invalid_api_key" in err_str.lower() or "unauthorized" in err_str.lower():
            raise HTTPException(
                status_code=401,
                detail="Clé LLM invalide ou expirée. Contactez l'administrateur."
            )
        raise HTTPException(status_code=500, detail=f"Erreur LLM : {err_str[:300]}")

    now = datetime.now(timezone.utc).isoformat()
    await db.steps.update_one(
        {"id": step_id},
        {"$set": {
            "ai_response": ai_text,
            "ai_model_used": f"{data.model_provider}/{data.model_name}",
            "ai_executed_at": now,
            "updated_at": now,
        }},
    )
    return {"ai_response": ai_text, "model": f"{data.model_provider}/{data.model_name}"}


@router.post("/steps/{step_id}/upload")
async def upload_step_file(step_id: str, file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    step = await db.steps.find_one({"id": step_id}, {"_id": 0})
    if not step:
        raise HTTPException(status_code=404, detail="Étape introuvable")
    await _check_site_access(step["site_id"], user)

    ext = Path(file.filename).suffix
    safe_name = f"{uuid.uuid4().hex}{ext}"
    target = UPLOAD_DIR / safe_name
    content = await file.read()
    if len(content) > 15 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Fichier trop volumineux (max 15 Mo)")
    target.write_bytes(content)

    file_record = {
        "original_name": file.filename,
        "stored_name": safe_name,
        "url": f"/api/uploads/{safe_name}",
        "size": len(content),
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "uploaded_by": user["id"],
    }
    await db.steps.update_one(
        {"id": step_id},
        {"$push": {"deliverable_files": file_record},
         "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}},
    )
    return file_record


@router.get("/validations")
async def validation_queue(admin: dict = Depends(require_admin)):
    """Monitoring admin des étapes complétées récemment (audit, pas de gating)."""
    steps = await db.steps.find({"status": "validated"}, {"_id": 0}).sort("validated_at", -1).limit(100).to_list(100)
    site_ids = list({s["site_id"] for s in steps})
    sites = await db.sites.find({"id": {"$in": site_ids}}, {"_id": 0, "id": 1, "name": 1, "niche": 1}).to_list(200)
    sites_by_id = {s["id"]: s for s in sites}
    for s in steps:
        s["site"] = sites_by_id.get(s["site_id"])
    return steps
