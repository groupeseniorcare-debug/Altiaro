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


async def _execute_step_background(step_id: str, prompt_text: str, provider: str, model: str) -> None:
    """Runs Claude in background, writes result back to step document. Never raises."""
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
        ).with_model(provider, model)
        message = UserMessage(text=prompt_text)
        last_exc = None
        ai_text = None
        for attempt in range(2):
            try:
                response = await asyncio.wait_for(chat.send_message(message), timeout=180)
                ai_text = response if isinstance(response, str) else str(response)
                break
            except Exception as e:
                last_exc = e
                err_low = str(e).lower()
                if attempt == 0 and any(s in err_low for s in ("502", "503", "504", "bad gateway", "timeout", "overloaded", "rate limit")):
                    logger.warning(f"[bg-exec] transient error, retrying once: {str(e)[:150]}")
                    await asyncio.sleep(2)
                    continue
                raise
        if ai_text is None and last_exc is not None:
            raise last_exc

        now = datetime.now(timezone.utc).isoformat()
        await db.steps.update_one(
            {"id": step_id},
            {"$set": {
                "ai_response": ai_text,
                "ai_model_used": f"{provider}/{model}",
                "ai_executed_at": now,
                "ai_executing": False,
                "ai_error": None,
                "updated_at": now,
            }},
        )
        logger.info(f"[bg-exec] step {step_id} completed ({len(ai_text)} chars)")
    except Exception as e:
        logger.exception(f"[bg-exec] step {step_id} failed")
        err_str = str(e)
        if "budget" in err_str.lower():
            msg = "Budget Emergent LLM Key épuisé. Rechargez depuis Profile → Universal Key → Add Balance."
        elif any(s in err_str.lower() for s in ("502", "503", "504", "overloaded", "bad gateway")):
            msg = "Claude est momentanément surchargé. Cliquez à nouveau sur Exécuter — c'est passager."
        elif "timeout" in err_str.lower():
            msg = "Timeout : Claude n'a pas répondu dans les 3 minutes. Réessayez."
        else:
            msg = f"Erreur IA : {err_str[:250]}"
        try:
            await db.steps.update_one(
                {"id": step_id},
                {"$set": {"ai_executing": False, "ai_error": msg, "updated_at": datetime.now(timezone.utc).isoformat()}},
            )
        except Exception:
            pass


@router.post("/steps/{step_id}/execute")
async def execute_step_with_ai(step_id: str, data: StepExecuteInput, user: dict = Depends(get_current_user)):
    step = await db.steps.find_one({"id": step_id}, {"_id": 0})
    if not step:
        raise HTTPException(status_code=404, detail="Étape introuvable")
    site = await _check_site_access(step["site_id"], user)
    if step["status"] == "locked":
        raise HTTPException(status_code=400, detail="Étape verrouillée")
    if step.get("ai_executing"):
        raise HTTPException(status_code=409, detail="Une exécution IA est déjà en cours pour cette étape")

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

    # Mark the step as executing and fire-and-forget background task
    now = datetime.now(timezone.utc).isoformat()
    await db.steps.update_one(
        {"id": step_id},
        {"$set": {"ai_executing": True, "ai_error": None, "ai_executing_started_at": now, "updated_at": now}},
    )
    asyncio.create_task(_execute_step_background(step_id, prompt_text, data.model_provider, data.model_name))
    return {"status": "executing", "message": "Génération en cours — la réponse apparaîtra sous 30-90 secondes."}


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
