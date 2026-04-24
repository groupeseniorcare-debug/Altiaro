# Altiaro

**Usine à sites e-commerce premium pour la Silver Economy** — SaaS multi-tenant permettant à des Concepteurs de lancer jusqu'à 10 boutiques premium par jour, avec IA pour le design/contenu/visuels, data Google réelle pour la recherche produit, SEO/AEO de pointe pour un trafic organique fort dès le lancement, et automatisation complète (fulfillment dropshipping, tracking, emails, paiements).

## Quick start

```bash
# 1. Installer les dépendances
cd /app/backend && pip install -r requirements.txt --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/
cd /app/frontend && yarn install

# 2. Créer les fichiers .env à partir des exemples
cp /app/backend/.env.example /app/backend/.env       # puis remplir les clés
cp /app/frontend/.env.example /app/frontend/.env     # puis remplir REACT_APP_BACKEND_URL

# 3. S'assurer que MongoDB tourne (déjà fait via supervisord dans le container)
sudo supervisorctl status mongodb

# 4. Démarrer backend + frontend
sudo supervisorctl restart all

# 5. Les seeds tournent automatiquement au startup :
#    - 20 niches dans le catalogue
#    - 50 prompts du playbook (8 blocs thématiques)
#    - Admin seed + Concepteur seed (cf. "Comptes seedés" plus bas)
```

## Architecture

Trois rôles distincts, scopés strictement par `user.role` + `operator_id` :

1. **Admin** (fondateur) : vue globale multi-concepteurs / multi-sites, lance Google Ads, valide les sites avant mise en ligne, pilote les finances globales (ledger, payouts 50% marge brute HT le 1er et 15 du mois), gère les commandes côté fournisseurs.
2. **Concepteur** (opérateur) : ne voit que ses sites, monte des boutiques via le wizard magique, choisit des produits (data Google réelle), génère design + contenu + visuels IA, traite SAV et remboursements.
3. **Client final** (public, non authentifié) : achète sur `/shop/{siteId}` ou `https://custom.domain.com` (multi-langues FR/EN/DE/NL), sans compte obligatoire.

## Stack

**Backend** — FastAPI 0.110 + Motor (MongoDB async) + APScheduler (11 jobs cron)
- Auth : JWT httpOnly cookies + bcrypt + anti-brute force
- LLM : Emergent LLM Key (Claude Sonnet 4.5) + Nano Banana (Gemini 3.1 Flash image preview)
- Intégrations : Mollie (paiements) · Resend (emails) · OVH (domaines) · AliExpress + CJ Dropshipping · Google Ads + Search Console · IndexNow

**Frontend** — React 19 + Craco + Tailwind 3.4
- UI : shadcn/ui (27 composants Radix UI) + Phosphor icons + lucide-react
- Animations : framer-motion 12
- Router : React Router v7
- Forms : react-hook-form + zod
- Charts : recharts

**Infra** — Supervisord (backend, frontend, mongodb, nginx-code-proxy)

## Structure des dossiers

```
/app
├── backend/                    FastAPI — 59 routers + orchestrateur server.py
│   ├── server.py               Monte tous les routers + APScheduler + seeds
│   ├── deps.py                 DB, auth JWT, helpers
│   ├── seed_niches.py          20 niches × 6 pays
│   ├── seed_prompts.py         50 prompts / 8 blocs (source de vérité playbook)
│   ├── legal_templates.py      Templates CGV / mentions / confidentialité / etc.
│   ├── conftest.py             Charge .env avant collecte pytest
│   ├── requirements.txt
│   ├── routes/                 59 fichiers — 257+ endpoints préfixés /api
│   ├── tests/                  30+ fichiers pytest (unit + integration)
│   └── uploads/                heroes · logos · products_ai · testimonials_ai
│
├── frontend/                   React 19 + Craco
│   ├── package.json
│   ├── tailwind.config.js
│   ├── craco.config.js
│   └── src/
│       ├── App.js              Routeur principal
│       ├── pages/              53 pages (cockpit + admin + storefront)
│       ├── components/         30+ composants métier + site-design/ + storefront/ + ui/
│       ├── lib/                api, auth, brandText, cart, customerAuth, i18n, utils
│       └── hooks/              use-toast
│
├── memory/                     Mémoire produit (versionnée git)
│   ├── PRD.md                  Source de vérité des exigences produit
│   ├── ROADMAP.md              Backlog P0/P1/P2/P3
│   ├── CHANGELOG.md            Historique des sprints
│   └── test_credentials.md     Comptes seedés (cf. section dédiée)
│
├── deliverables/               2 playbooks markdown (legacy — désynchronisés avec seed_prompts.py)
├── docs/GSC_SETUP.md           Guide OAuth Google Search Console
├── design_guidelines.json      Blueprint UI (palette, typo, patterns)
├── test_reports/pytest/        Rapports JSON par itération
└── README.md                   (ce fichier)
```

## Services & ports

| Service    | Port interne | Accès externe                          |
|------------|-------------:|----------------------------------------|
| Backend    | **8001**     | via `REACT_APP_BACKEND_URL` + préfixe `/api` |
| Frontend   | **3000**     | idem (Kubernetes ingress)              |
| MongoDB    | **27017**    | local uniquement (`MONGO_URL`)         |
| OpenAPI docs | —          | `/api/docs` (Swagger) + `/api/redoc` + `/api/openapi.json` |

**Règle Kubernetes ingress** : toutes les routes préfixées `/api/*` → port 8001 · tout le reste → port 3000.

## Variables d'environnement

Voir `/app/backend/.env.example` et `/app/frontend/.env.example` pour la liste exhaustive (45+ variables) avec commentaire par clé et exemple de format.

**À retenir** :
- `MONGO_URL`, `DB_NAME`, `JWT_SECRET` sont **obligatoires** au démarrage (le backend crashe sans).
- Toutes les intégrations externes (Mollie, Resend, OVH, AliExpress, CJ, Google Ads, GSC, Emergent LLM) sont **optionnelles au boot** — les parcours qui en dépendent retournent `config_missing` tant que les clés sont vides.
- **Ne jamais modifier** `REACT_APP_BACKEND_URL` (frontend) ni `MONGO_URL` (backend) — valeurs gérées par la plateforme Emergent.

## Comptes seedés

Créés automatiquement au startup backend (et re-synchronisés à chaque boot si password différent). Référence complète dans `/app/memory/test_credentials.md`.

| Rôle       | Email                              | Password         |
|------------|------------------------------------|------------------|
| Admin      | `admin@conceptfactory.fr`          | `Factory2026!`   |
| Concepteur | `concepteur@conceptfactory.fr`     | `Concepteur2026!`|

## Tests

```bash
# Unit tests purs Python (rapides, sans HTTP) — doivent tous passer
cd /app
/root/.venv/bin/python -m pytest backend/tests/test_brand_sanitizer.py \
  backend/tests/test_internal_linking.py \
  backend/tests/test_blog_auto_plan.py \
  backend/tests/test_seo_badges.py \
  backend/tests/test_ae_deals_watcher.py -q

# Collect only (pour vérifier qu'aucun fichier ne plante au import)
/root/.venv/bin/python -m pytest backend/tests --collect-only -q

# Full test suite (inclut iteration*.py — nécessite un site de démo + cookies auth)
/root/.venv/bin/python -m pytest backend/tests -q
```

Le `backend/conftest.py` charge automatiquement `.env` avant l'import des modules testés (sinon `deps.py` crashe au top-level sur `os.environ["MONGO_URL"]`).

## Jobs planifiés (APScheduler)

Tous démarrent à l'init du backend (`server.py` `@app.on_event("startup")`). 11 jobs au total :

| Job                       | Fréquence                 | Rôle                                                    |
|---------------------------|---------------------------|---------------------------------------------------------|
| weekly_debits             | Lundi 03h UTC             | Prélèvements hebdo concepteurs (Mollie mandate)         |
| bimonthly_payouts         | 1er & 15 du mois · 03h UTC| Génère payouts admin (50 % marge brute HT)              |
| reviews_check_due         | Quotidien 04h UTC         | Envoie invitations review J+14 post-livraison (Resend)  |
| ae_tracking_sync          | Quotidien 05h30 UTC       | Sync tracking AliExpress                                |
| cj_tracking_sync          | Toutes les 2h             | Sync tracking CJ                                        |
| opportunity_scan          | Lundi 05h UTC             | Détection spikes via Google Keyword Planner             |
| dns_auto_config           | Toutes les 5 min          | Config DNS auto pour domaines `status=purchased` (OVH)  |
| monthly_blog_cluster      | 1er du mois · 06h UTC     | 1 pilier + 4 satellites par site (Claude)               |
| weekly_seo_coach          | Lundi 08h UTC             | Digest email alerts SEO hebdo + snapshot E-E-A-T        |
| citation_tracker_weekly   | Jeudi 08h UTC             | Mesure citation IA (Claude panel) sur 5 Q/site          |
| ae_deals_watch            | Mardi 06h UTC             | Scan AliExpress deals ≥ 20 % drop ≥ 500 commandes       |

## Conventions importantes

- **Tous les endpoints backend sont préfixés `/api`** (Kubernetes ingress rule).
- **UUIDs partout**, jamais d'`ObjectId` Mongo exposé (non sérialisable JSON).
- Cookies `httpOnly` uniquement pour le JWT (access + refresh).
- Data scope strict : tout est filtré par `site_id` et `operator_id` côté Concepteur.
- **Ne jamais supprimer `<html translate="no">`** dans `index.html` (bug Mac Chrome auto-translate crash React).
- Emergent LLM Key via `emergentintegrations.llm.chat.LlmChat`, jamais en direct.

## Mémoire produit

Toute décision significative DOIT être tracée dans :
- `/app/memory/PRD.md` — si elle ajoute/modifie une exigence produit
- `/app/memory/ROADMAP.md` — si elle ajoute/retire du backlog
- `/app/memory/CHANGELOG.md` — livraisons effectives (date, périmètre, tests)

## Intégrations externes — état opérationnel

Voir le dernier rapport d'audit dans la conversation (tour par tour). En bref :
- ✅ Emergent LLM · Mollie · Resend · OVH · CJ · IndexNow opérationnels
- ⚠️ AliExpress : clés OK, OAuth callback à finaliser
- 🔑 Google Ads + Google Search Console : OAuth client ID/secret manquants (en attente user)
- 🔑 Google Merchant Center : code à écrire (P0 ROADMAP)
