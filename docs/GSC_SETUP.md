# Google Search Console — Guide d'activation (5 minutes)

Pour afficher la **position Google moyenne** et les **clics / impressions / CTR**
réels dans le widget Pulse SEO de chaque site, il faut créer un projet Google
Cloud et un client OAuth 2.0. Cette manipulation se fait **une seule fois au
niveau plateforme** — ensuite chaque Concepteur peut connecter sa propre
Search Console en un clic.

---

## 1 · Créer un projet Google Cloud

1. Rendez-vous sur <https://console.cloud.google.com> (compte Google de la
   société, pas un compte perso).
2. En haut à gauche, cliquez sur **« Select a project »** → **« New Project »**.
3. Nommez-le `Altiaro Pulse SEO` → **Create**.

## 2 · Activer l'API Search Console

1. Dans le menu latéral, **APIs & Services → Library**.
2. Cherchez **« Google Search Console API »** → cliquez dessus → **Enable**.

## 3 · Configurer l'écran de consentement OAuth

1. **APIs & Services → OAuth consent screen**.
2. Type d'utilisateur : **External** → Create.
3. Remplissez :
   - App name : `Altiaro Pulse SEO`
   - User support email : votre email
   - Developer contact email : votre email
4. Scopes : cliquez **Add or Remove Scopes**, cherchez
   `https://www.googleapis.com/auth/webmasters.readonly`, cochez-le → Update.
5. Test users (pendant la phase de test) : ajoutez l'email du Concepteur
   qui va tester. En prod, passez l'app en **Publishing status: In production**.

## 4 · Créer un Client OAuth 2.0

1. **APIs & Services → Credentials → + Create Credentials → OAuth client ID**.
2. Application type : **Web application**.
3. Name : `Altiaro Backend`.
4. **Authorized redirect URIs** : ajouter l'URL exacte suivante
   (adaptée au backend en production) :
   ```
   https://senior-france.preview.emergentagent.com/api/gsc/oauth/callback
   ```
   (Remplacez par votre domaine en production — doit matcher à la virgule près
   avec la variable `GOOGLE_REDIRECT_URI` du fichier `.env`.)
5. **Create** → Google affiche votre `Client ID` et `Client Secret`.

## 5 · Copier les clés dans le backend

Ajoutez dans `/app/backend/.env` (sans guillemets, sans commentaire) :

```
GOOGLE_CLIENT_ID=xxxxxxxxxxxxxxxxxxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-xxxxxxxxxxxxx
GOOGLE_REDIRECT_URI=https://senior-france.preview.emergentagent.com/api/gsc/oauth/callback
```

Puis `sudo supervisorctl restart backend`.

## 6 · Brancher un site

Côté admin Concepteur :
1. Aller sur le cockpit d'un site (`/sites/:id`).
2. Dans le widget **Pulse SEO**, cliquer sur **« Connecter GSC »** dans la
   bande du bas.
3. Une popup Google s'ouvre → sélectionner le compte qui possède la propriété
   Search Console → autoriser.
4. Au retour dans le cockpit (redirect auto avec `?gsc=connected`), la bande
   affiche la **position moyenne, les clics, les impressions, le CTR** sur 28 jours.

---

## Détails techniques

- **Scope** : `https://www.googleapis.com/auth/webmasters.readonly` (lecture seule).
- **Stockage** : `site.design.gsc.refresh_token` dans MongoDB (tenant-scoped).
- **Refresh** : le backend échange le `refresh_token` contre un `access_token`
  à chaque appel metrics (short-lived, ~1 h).
- **CSRF** : collection `gsc_oauth_states` avec TTL 10 min.
- **Quota** : Search Console API = 1 200 requêtes/min. Le widget cache
  implicitement via React mount (1 appel par ouverture de cockpit).

## En cas d'erreur

| Symptôme | Solution |
|----------|----------|
| « redirect_uri_mismatch » | L'URL dans Google Cloud doit matcher à l'identique avec `GOOGLE_REDIRECT_URI`. Vérifier `http` vs `https`, port, slash final. |
| « No refresh token received » | Révoquez l'app dans <https://myaccount.google.com/permissions> puis réessayez — Google ne renvoie un refresh_token que lors du premier consent. |
| 403 `insufficient_permission` | Le compte Google qui a consenti n'est pas propriétaire de la propriété Search Console. Vérifier dans GSC → Settings → Users. |
