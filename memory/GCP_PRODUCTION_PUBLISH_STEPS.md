# GCP Production Publish — Procédure étape-par-étape (OAuth consent screen)

> **Dernière mise à jour : Sprint 1 — Altiaro industrialisation**  
> **Objectif** : sortir le projet Google Cloud Altiaro du mode "Testing" pour que le `refresh_token` Google Master cesse d'expirer tous les 7 jours.  
> **Impact** : débloque GSC, GMC, Google Ads Keyword Planner, GA4 Admin API, siteVerification.  
> **Durée** : 5–10 minutes + éventuellement attente de vérification Google si scopes sensibles.

---

## ⚠️ Pourquoi c'est P0

Quand un projet Google Cloud est en **Testing**, Google documente explicitement :

> *A Google Cloud Platform project with an OAuth consent screen configured for an external user type and a publishing status of "Testing" is issued a refresh token expiring in **7 days**.*  
> — [https://developers.google.com/identity/protocols/oauth2#expiration](https://developers.google.com/identity/protocols/oauth2#expiration)

Symptôme observé toutes les 48 h à 7 j dans les logs Altiaro :

```
oauthlib.oauth2.rfc6749.errors.InvalidGrantError:
(invalid_grant) Token has been expired or revoked.
```

Toutes les API dérivées tombent en cascade : GMC, GSC, Ads, GA4, siteVerification.

---

## Étape 1 — Ouvrir OAuth consent screen

URL exacte :

```
https://console.cloud.google.com/apis/credentials/consent
```

En haut à gauche, **vérifier que le sélecteur de projet affiche bien `Altiaro`** (ou le nom réel du projet GCP du `.env` → `GOOGLE_PROJECT_ID`). Si le mauvais projet est sélectionné, cliquer dessus et changer.

### À quoi doit ressembler l'écran

- Titre : **"OAuth consent screen"**
- Panneau central : bandeau **"Testing"** avec texte gris *"Publishing status: Testing"*.
- Bouton visible : **`PUBLISH APP`** (bleu, à droite du bandeau).
- Si le bandeau est déjà jaune avec **"In production"** → **rien à faire**, passer à l'Étape 6 (vérification post-publication).

---

## Étape 2 — Vérifier que tous les champs requis sont remplis

Google refuse de publier si un champ requis manque. Ouvrir `EDIT APP` en haut à droite du panneau et parcourir l'assistant en 4 pages.

### Page 1 — "App information"

| Champ | Valeur attendue |
|---|---|
| **App name** | `Altiaro` |
| **User support email** | email admin (ex. `admin@altiaro.com`) |
| **App logo** (optionnel mais recommandé) | PNG 120×120 max 1 MB. Uploader le wordmark Altiaro. |
| **App domain — Application home page** | `https://altiaro.com` |
| **App domain — Application privacy policy link** | `https://altiaro.com/legal/confidentialite` |
| **App domain — Application terms of service link** | `https://altiaro.com/legal/cgv` |
| **Authorized domains** | Ajouter `altiaro.com` (1 seule entrée, racine uniquement). Si custom domains concepteurs sont prévus en OAuth tenant unique, n'ajouter QUE `altiaro.com`. |
| **Developer contact information** | email admin (même ou autre) |

Cliquer `SAVE AND CONTINUE`.

### Page 2 — "Scopes"

Scopes à déclarer (tous ceux déjà demandés dans `GOOGLE_SCOPES` côté backend) :

```
https://www.googleapis.com/auth/webmasters
https://www.googleapis.com/auth/webmasters.readonly
https://www.googleapis.com/auth/content
https://www.googleapis.com/auth/adwords
https://www.googleapis.com/auth/analytics.edit
https://www.googleapis.com/auth/analytics.readonly
https://www.googleapis.com/auth/siteverification
openid
https://www.googleapis.com/auth/userinfo.email
https://www.googleapis.com/auth/userinfo.profile
```

**Classement Google** :
- `userinfo.email`, `userinfo.profile`, `openid` → **Non-sensitive**
- `siteverification` → **Sensitive**
- `webmasters`, `content`, `adwords`, `analytics.edit` → **Restricted** (les pires côté verif)

Cocher tous ces scopes via le bouton `ADD OR REMOVE SCOPES`. Google affichera un warning "Your app will need verification" — **pas bloquant** pour publier. Cliquer `UPDATE` puis `SAVE AND CONTINUE`.

### Page 3 — "Test users" (uniquement visible en mode Testing)

Cette page disparaît après publication. On peut la laisser telle quelle.

### Page 4 — "Summary"

Cliquer `BACK TO DASHBOARD`.

---

## Étape 3 — Cliquer PUBLISH APP

Depuis la page `/apis/credentials/consent` (bandeau "Testing") :

1. Cliquer **`PUBLISH APP`** (bleu, bien visible).
2. Une modale s'ouvre :

   > **Push to production?**  
   > Your app will be available to any user with a Google account. Make sure your OAuth consent screen meets [Google's user data policy](https://developers.google.com/terms/api-services-user-data-policy).
3. Cliquer **`CONFIRM`**.
4. Le bandeau passe en jaune **"In production"** (status = `IN_PRODUCTION`). **C'est fait.**

### Si Google affiche "Verification needed" au lieu de "In production"

Parce qu'on a coché les scopes `restricted` (`webmasters`, `content`, `adwords`, `analytics.edit`). Deux options :

#### Option A (single-tenant Altiaro uniquement — recommandée maintenant)

- Le bandeau peut afficher **"Verification in progress"** ou un warning jaune "Unverified app" persistant.
- **L'app reste utilisable** : à chaque OAuth, l'utilisateur voit un écran rouge Google *"This app isn't verified — Continue only if you trust the developer"*. Cliquer `Advanced` → `Go to Altiaro (unsafe)`.
- **Le refresh_token ne sera plus révoqué au bout de 7 jours** dès que le status = `IN_PRODUCTION` (même sans verification complète).
- ✅ C'est l'état cible immédiat pour débloquer le projet.

#### Option B (si on veut supprimer le warning rouge à terme)

- Cliquer `Submit for verification`.
- Fournir :
  - **Domain ownership** de `altiaro.com` (via Search Console — déjà fait, réutiliser le TXT record).
  - **Video demo YouTube (unlisted)** de 2–5 min montrant chaque scope restricted en action (login → appel Ads → appel GSC → appel GMC → appel Analytics).
  - **Justification écrite** par scope (pourquoi on en a besoin).
- Délai Google : **4–6 semaines** pour les restricted, ~72 h pour les sensitive seuls.
- Pas de coût (sauf App Security Assessment si > 100 users ou scopes "critical").

**→ Pour maintenant on reste en Option A.**

---

## Étape 4 — (Optionnel) Vérifier credentials OAuth client

URL :

```
https://console.cloud.google.com/apis/credentials
```

- Vérifier qu'il existe bien un **OAuth 2.0 Client ID** de type `Web application` nommé `Altiaro Master` (ou équivalent).
- `Authorized redirect URIs` doit contenir :
  - `https://altiaro.com/google-master/callback`
  - `https://altiaro.com/google-ads/callback`
  - `https://altiaro.com/merchant/callback`
  - `https://altiaro.com/google/callback`
  - éventuellement `https://{PREVIEW_HOST}/google-master/callback` pour tester depuis preview
- Si un redirect URI manque → l'ajouter, puis **télécharger le `client_secret.json`** (icône ↓) et vérifier que `GOOGLE_CLIENT_ID` + `GOOGLE_CLIENT_SECRET` du `.env` correspondent.

---

## Étape 5 — Activer les APIs nécessaires (idempotent)

URL :

```
https://console.cloud.google.com/apis/library
```

Vérifier que les APIs suivantes sont **Enabled** dans le projet Altiaro :

| API | Nom Google | Nécessaire pour |
|---|---|---|
| `webmasters.googleapis.com` | Search Console API | GSC (sitemap + indexing) |
| `content.googleapis.com` | Content API for Shopping | Google Merchant Center |
| `googleads.googleapis.com` | Google Ads API | Ads + Keyword Planner |
| `analyticsadmin.googleapis.com` | Google Analytics Admin API | GA4 provisioning (Sprint 3) |
| `analyticsdata.googleapis.com` | Google Analytics Data API | GA4 reporting |
| `siteverification.googleapis.com` | Site Verification API | Vérif domaine |
| `indexing.googleapis.com` | Indexing API (Job Postings only) | **NON** — non utilisé par Altiaro |

Chaque API absente → cliquer dessus → `ENABLE`. Aucun quota à tuning pour le volume Altiaro (10 sites/j × 14 posts → largement sous les quotas gratuits).

---

## Étape 6 — Vérification post-publication

### 6.1 Reconnecter Google Master côté Altiaro

1. Aller sur `https://altiaro.com/admin/google-master`
2. Cliquer **`Reconnect`** / **`Déconnecter puis reconnecter`** (le bouton dépend de l'état actuel).
3. Autoriser **tous les scopes** demandés (écran Google avec liste).
4. L'URL de callback doit retomber sur `https://altiaro.com/google-master/callback` et afficher "Google Master connected ✓".

### 6.2 Test santé OAuth

```bash
cd /app/backend && python3 -c "
import asyncio
from services.google_oauth_health import google_master_health_tick
print(asyncio.run(google_master_health_tick()))
"
```

Attendu : `{"ok": True, "access_token_valid": True, "scopes_ok": True, ...}`

### 6.3 Test GSC auto-provision sur Altea

```bash
cd /app/backend && python3 -c "
import asyncio, os
from dotenv import load_dotenv
load_dotenv('/app/backend/.env')
from services.gsc_provisioning import provision_for_site
# Altea site_id
print(asyncio.run(provision_for_site('6867223e-7ea5-45a7-815a-300cd89b7656')))
"
```

Attendu (après `Reconnect`) :
```json
{"ok": true, "property": {...}, "sitemap": {"ok": true, "submitted": true}}
```

### 6.4 Test Keyword Planner (critique pour Sprint 1)

```bash
cd /app/backend && python3 -c "
import asyncio
from routes.google_ads import fetch_keyword_volumes
out = asyncio.run(fetch_keyword_volumes({'FR': ['fauteuil releveur', 'monte-escalier']}))
print(out)
"
```

Attendu : dict avec `volume`, `competition`, `cpc_low_eur`, `cpc_high_eur` par mot-clé.

### 6.5 Contrôle long-terme (optionnel)

Attendre **> 7 jours** et re-lancer `google_master_health_tick()`. Si `{"ok": True}` après J+8 → le passage en Production est **définitivement** effectif. Un cron `google_oauth_health` tourne toutes les 6 h et crée une `admin_notifications` si le token meurt malgré tout (filet de sécurité).

---

## FAQ & pièges fréquents

### Q : J'ai cliqué PUBLISH APP mais je vois "Verification in progress" et ça bloque l'auth.

Ça ne **bloque pas** l'auth. L'écran rouge Google pendant le consent reste skippable via `Advanced → Go to Altiaro (unsafe)`. Le refresh_token fonctionne.

### Q : Je veux supprimer le warning rouge "Unverified" sans passer la verification.

Impossible sans verification. Soit verification complète (Option B), soit on accepte le warning pour les utilisateurs Altiaro admin.

### Q : Le user a révoqué manuellement les permissions sur myaccount.google.com.

Le refresh_token meurt **immédiatement** quel que soit le mode Testing/Production. Reconnect requis.

### Q : J'ai perdu le `client_secret.json`, comment le régénérer ?

- `https://console.cloud.google.com/apis/credentials`
- Cliquer sur le client ID concerné
- Onglet `Download JSON` ou `Reset secret` (⚠️ `Reset secret` invalide l'ancien → downtime prévoir)

### Q : Faut-il publier le même OAuth client pour Ads + GMC + GSC ?

- **Oui, un seul client suffit** si on utilise le même redirect URI pattern et qu'on a bien tous les scopes déclarés dans le consent screen.
- Altiaro utilise actuellement **2 clients OAuth distincts** :
  - `Altiaro Master` → GSC + GMC + GA4 + siteVerification (scopes dans `GOOGLE_CLIENT_ID`)
  - `Altiaro Ads` → Google Ads uniquement (scopes dans `GOOGLE_ADS_CLIENT_ID`)
- Les **deux clients partagent le même projet GCP** → **publier le projet publie les 2 clients en même temps**. Une seule action PUBLISH APP suffit.

### Q : Que se passe-t-il côté users existants ?

Les `refresh_token` émis en mode Testing restent valides tant qu'ils ne meurent pas (7 j max). Dès qu'ils meurent, la prochaine reconnexion émettra un nouveau refresh_token sans limite de 7 j (Production). En pratique : **tous les users devront se reconnecter une dernière fois dans les 7 j suivant le PUBLISH APP**. Ensuite c'est stable.

---

## Checklist pour le rapport

- [ ] Projet GCP sélectionné = projet Altiaro réel (vérifier `GOOGLE_PROJECT_ID` du `.env`)
- [ ] Tous les champs requis remplis dans `EDIT APP` (page 1 → 4)
- [ ] Bouton `PUBLISH APP` cliqué
- [ ] Dialog `CONFIRM` validé
- [ ] Bandeau = **"In production"** (jaune) ou **"Verification in progress"**
- [ ] APIs activées : webmasters + content + googleads + analyticsadmin + analyticsdata + siteverification
- [ ] Reconnect fait sur `/admin/google-master` (tous scopes)
- [ ] `google_master_health_tick()` retourne `{"ok": True}`
- [ ] `fetch_keyword_volumes()` retourne des volumes réels (≠ 0 et ≠ placeholder)

À partir du moment où ces 9 cases sont cochées, **Altiaro est déverrouillé industriellement** côté Google.
