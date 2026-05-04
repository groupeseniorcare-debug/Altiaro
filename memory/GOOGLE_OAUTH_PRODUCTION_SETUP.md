# Google OAuth Master — passage en "Production" pour eviter l'expiration 7j

## Probleme constate

Le refresh_token Google Master expire toutes les **48h-7j** dans cet environnement. Symptome :
```
invalid_grant: Token has been expired or revoked.
```
Toutes les API derivees (GMC, GSC, Ads, GA4, siteVerification) tombent en panne.

## Cause

Quand un projet Google Cloud est en mode **"Testing"** dans l'OAuth consent screen, **les refresh_token expirent au bout de 7 jours** ([doc officielle](https://developers.google.com/identity/protocols/oauth2#expiration)) :

> A Google Cloud Platform project with an OAuth consent screen configured for an external user type and a publishing status of "Testing" is issued a refresh token expiring in 7 days.

C'est le cas actuel du projet Altiaro.

## Procedure pour passer en "Production" (5 min)

1. Ouvrir https://console.cloud.google.com/apis/credentials/consent
2. Selectionner le projet **Altiaro** (verifier en haut a gauche).
3. Verifier que l'**OAuth consent screen** affiche User type = `External`.
4. Cliquer **PUBLISH APP**. Confirmer dans le dialog.
5. La banniere passe en jaune "In production" (ou "Verification needed" si on a des scopes sensibles).
6. Verifier que tous les champs requis sont remplis :
   - App name = "Altiaro"
   - User support email = email admin
   - Developer contact email
   - Logo (128x128 PNG)
   - Application home page = `https://altiaro.com`
   - Privacy policy = `https://altiaro.com/legal/confidentialite`
   - Terms of service = `https://altiaro.com/legal/cgv`
7. Sauver. Refresh.

## Si Google demande "verification"

Des que tu utilises des scopes sensibles (`adwords`, `content`, `analytics`) Google peut demander une verification de l'app. C'est **skippable tant que tu utilises l'app pour ton propre compte uniquement** (single-tenant).

- Cliquer "Continue without verification"
- Confirmer "I understand the risks"
- L'app reste utilisable mais montre un warning ecran a chaque OAuth

Quand tu voudras onboarder d'autres utilisateurs Altiaro plus tard, il faudra :
- Soumettre l'app pour verification Google (delai : 4-6 semaines)
- Fournir une video d'usage des scopes sensibles
- Domain verification du site `altiaro.com`
- App security assessment si scopes "restricted"

Pour l'instant, **single-tenant + skip verification = OK**.

## Verification post-publication

1. Aller sur `https://altiaro.com/admin/google-master` -> Reconnect
2. Authoriser tous les scopes
3. Persister
4. Test : `python3 -c "import asyncio; from services.google_oauth_health import google_master_health_tick; print(asyncio.run(google_master_health_tick()))"`
5. Attendre **>7j** et re-tester. Si `{ok: True}` apres 8j -> probleme resolu.
6. Le cron `google_oauth_health` (toutes les 6h) creera une `admin_notifications` si jamais le token re-expire.

## Notes

- Les access_token (cours validite ~1h) sont rafraichis automatiquement -> pas besoin de toucher.
- Si le user revoque manuellement les permissions sur https://myaccount.google.com/permissions, le refresh_token meurt **immediatement** -> reconnect requis quel que soit le statut Production/Testing.
- L'app peut rester "In production" sans avoir 100M users. C'est juste un changement de statut OAuth.
- Les webhooks Google ne sont pas necessaires.
