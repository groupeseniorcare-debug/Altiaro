# Migration Anthropic + Google GenAI directs (plan, non exécuté)

> But : couper l'intermédiaire Emergent LLM pour : (a) éliminer le cap
> récurrent de la Universal Key, (b) récupérer la marge ~30 % prise par le
> proxy, (c) avoir un suivi de coût au centime via le header litellm
> `x-litellm-response-cost` (ou `response.usage` natif).

## 1. Inventaire des callsites

```
137 références au total dans 38 fichiers

→ Entrypoints isolés (couche wrapper, à toucher à 95 %) :
   backend/services/llm_resilience.py   (22 refs) ← point de migration principal
   backend/services/llm_async.py        (3 refs)  ← wrapper to_thread

→ Callers indirects (via safe_* helpers, rien à migrer) :
   safe_claude_text   : 16 callsites
   safe_claude_json   : 24 callsites
   safe_nano_banana   : 35 callsites
   LlmChat direct     : 1 callsite (brand_story.py — à refactorer)

→ Scripts one-shot (migration optionnelle) :
   scripts/fix1_*.py, scripts/fix2_*.py, scripts/lotG_*.py, scripts/lot_c_*.py
```

**Bonne nouvelle** : l'architecture `llm_resilience.safe_*` est une facade
propre. **La migration se fait dans UN seul fichier** (`llm_resilience.py`) —
les ~75 callers `safe_claude_*` et `safe_nano_banana*` continueront à
fonctionner sans modification.

## 2. Stratégie

### Anthropic (texte — brand, content, narrative, SEO, QA, translate)

SDK : `anthropic` (version ≥0.39, déjà transitive via emergentintegrations).

Pattern de remplacement dans `safe_claude_text()` / `safe_claude_json()` :
```python
# AVANT
from emergentintegrations.llm.chat import LlmChat, UserMessage
chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=sid, system_message=system)
chat.with_model("anthropic", resolved_model)
raw = await send_message_threaded(chat, UserMessage(text=user))

# APRÈS
from anthropic import AsyncAnthropic
client = AsyncAnthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
response = await client.messages.create(
    model=resolved_model,
    max_tokens=8192,
    system=system,
    messages=[{"role": "user", "content": user}],
)
raw = response.content[0].text
# Cost tracking : response.usage.input_tokens + response.usage.output_tokens
```

Modèles à conserver identiques : `claude-sonnet-4-5-20250929` (premium), `claude-haiku-4-5-20251001` (rapide).

### Google GenAI (images — Nano Banana)

SDK : `google-genai` (déjà dans `requirements.txt` comme `google-genai==0.x`).

Pattern de remplacement dans `safe_nano_banana*()` :
```python
# AVANT
chat = LlmChat(api_key=EMERGENT_LLM_KEY, ...).with_model("gemini", NANO_MODEL)
chat.with_params(modalities=["image", "text"])
_, images = await send_multimodal_threaded(chat, msg)

# APRÈS
from google import genai
client = genai.Client(api_key=os.environ["GOOGLE_AI_STUDIO_KEY"])
response = client.models.generate_content(
    model="gemini-2.5-flash-image",  # nano-banana = gemini image gen
    contents=[prompt, reference_image_pil]  # img-to-img si ref
)
# Parser response.candidates[0].content.parts pour extraire l'inline_data.data
image_bytes = base64.b64decode(part.inline_data.data)
```

## 3. Coût comparé

| Modèle | Emergent proxy | Anthropic direct | Google direct |
|---|---|---|---|
| Claude Sonnet 4.5 | ~$3 in / $15 out / M tok | **$3 in / $15 out / M tok** (identique) | — |
| Claude Haiku 4.5 | ~$1 in / $5 out / M tok | **$1 in / $5 out / M tok** (identique) | — |
| Nano Banana (gemini-2.5-flash-image) | Facturé par Emergent | — | **~$0.039 / image** (tarif public Google) |
| **Marge Emergent estimée** | +20-30 % sur la facturation | — | — |

**Conclusion coût** : passer en direct **n'est PAS moins cher au token**
(Anthropic facture son API au même tarif). Le gain réel vient de :
1. **Suppression du cap arbitraire Emergent** ($70 → $96 palier $2)
2. **Suppression de la marge proxy** (~25 %) → économie réelle 20-25 %
3. **Visibilité `response_cost` en temps réel** (remplace mon estimateur
   qui sous-estime de 50 %)

## 4. Circuit-breaker / retry

`llm_resilience.py:safe_llm_call()` reste intact — c'est une fonction
générique qui wrap n'importe quel callable avec :
- retry exponentiel (3 tentatives, backoff 2/4/8 s)
- timeout (default 90 s)
- circuit-breaker par provider (ouvert après 5 échecs)
- logging structuré

→ **Zéro refactor nécessaire** sur cette couche.

## 5. Estimation effort

| Étape | Durée |
|---|---|
| Ajout env vars + install `anthropic` + `google-genai` (déjà présent) | 15 min |
| Refactor `safe_claude_text` + `safe_claude_json` (une fonction) | 30 min |
| Refactor `safe_nano_banana_bytes` + `safe_nano_banana_url` | 45 min |
| Refactor du callsite direct `LlmChat` dans `brand_story.py` | 10 min |
| Feature flag `LLM_PROVIDER=anthropic\|emergent` | 20 min |
| Tests smoke (1 appel Claude + 1 appel Nano Banana) | 15 min |
| **Total** | **~2 h 15** |

## 6. Variables d'environnement à ajouter

```bash
# Dans backend/.env
LLM_PROVIDER=anthropic              # "anthropic" | "emergent" (fallback)
ANTHROPIC_API_KEY=sk-ant-api03-...  # https://console.anthropic.com/settings/keys
GOOGLE_AI_STUDIO_KEY=AI...          # https://aistudio.google.com/app/apikey
# EMERGENT_LLM_KEY reste dans .env comme fallback
```

Permissions :
- **Anthropic** : créer une clé avec scope "Write" sur l'organisation.
  Mettre un hard budget cap dans le dashboard Anthropic (ex: $500/mois)
  pour éviter la surconsommation ; ils envoient email à 50/75/100 %.
- **Google AI Studio** : clé gratuite jusqu'à 1 500 requêtes/jour Nano
  Banana, puis Tier 1 payant. Pas de cap automatique nécessaire.

## 7. Feature flag de repli

Dans `llm_resilience.py`, lire `LLM_PROVIDER` une fois :
```python
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "emergent").lower()
# Sélectionne le client à l'appel
if LLM_PROVIDER == "anthropic":
    return await _claude_anthropic_direct(...)
return await _claude_emergent(...)
```

Permet de switch à chaud sans redéploiement et de rouler un A/B test court.

## 8. Checklist de déploiement

- [ ] Obtenir `ANTHROPIC_API_KEY` (console.anthropic.com) + poser hard cap $500
- [ ] Obtenir `GOOGLE_AI_STUDIO_KEY` (aistudio.google.com)
- [ ] Ajouter les vars dans `backend/.env`
- [ ] Installer : `pip install anthropic google-genai` (les deux déjà
      présents via dépendances transitives, mais vérifier versions)
- [ ] Implémenter `_claude_anthropic_direct()` + `_nano_banana_google_direct()`
      dans `llm_resilience.py`
- [ ] Ajouter feature flag `LLM_PROVIDER`
- [ ] Smoke test : 1 launch Altea de test sur un site jetable (`MAX_COLOR_VARIANTS_AI=1`)
- [ ] Comparer `cost_summary.total_usd` vs `x-litellm-response-cost` pour
      confirmer que l'estimateur local est maintenant précis
- [ ] Basculer `LLM_PROVIDER=anthropic` en prod
- [ ] Garder `EMERGENT_LLM_KEY` en fallback 30 jours, puis supprimer

## 9. Risques identifiés

| Risque | Mitigation |
|---|---|
| Anthropic rate limit sur l'organisation | Monitoring + backoff (déjà dans `safe_llm_call`) |
| Google AI Studio rate limit tier gratuit | Passer Tier 1 si > 1500 imgs/jour |
| Format de réponse différent (Anthropic vs Emergent) | Tests smoke + adapter du parsing |
| `emergentintegrations` utilisé en transitive dans un import caché | Grep exhaustif déjà fait, 38 fichiers couverts |
| Feature flag mal géré → inconsistance runtime | Lire la valeur une seule fois au boot, pas par appel |

---

*Plan établi — non exécuté. Déclencher quand l'utilisateur valide.*
