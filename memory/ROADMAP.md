# Concept Factory — ROADMAP

> **Mise à jour : 2026-05-04** — purge des items obsolètes, cap sur le Sprint 5+.

## ✅ Livré (récapitulatif synthétique)

**Core platform** : Auth JWT + 2 rôles · Sites CRUD + wizard 50 étapes · Storefront i18n (6 langues, 11 pays EU) · Catalogue + cost_price_ht + commandes · Mollie checkout + CB + IBAN · Virements 50% marge brute (1er/15) · Dashboard Empire · AI Copilot · Mega-Blocks · Site Designer IA-first · Pages légales auto centralisées (KBIS Altiaro).

**Sourcing & ads** : CJ Dropshipping + AliExpress (search + import 1-clic) · Google Ads OAuth + Keyword Planner + Campaigns read · Quick Scan Go/No-Go multi-marché async · Niche Engine 20×6.

**Marque & SEO** : SEO avancé (sitemap hreflang, robots.txt, merchant-feed RSS 2.0, Schema.org, OG, canonical) · Storefront monochrome éditorial · Blog IA pilier+satellites + cluster mensuel · AEO Readiness (18-22 Q/R par produit) · Maillage interne automatique · AI Citation Tracker · Coach SEO + Pulse SEO + EEAT history · IndexNow auto-submit · Google Search Console multi-tenant (UI + backend, en attente reconnect master OAuth).

**Industrialisation 2026-04 → 2026-05** :
- Phase 0 — Résilience LLM (circuit breaker + retry expo + degraded_steps) ✅
- Phase 0.5 — Migration LLM complète (0 LlmChat direct dans `routes/`) ✅
- Bloc 1 — Optimisations coût LLM (Haiku 4.5 standard, Sonnet 4.5 premium) + Alerte budget LLM ✅
- Bloc 1 — RGPD bannière + politique cookies (CNIL-compliant) ✅
- Bloc 2 — Centralisation légale KBIS + anonymisation absolue ✅
- **Sprints SEO 1-4** — 9 AEO snippets + 9 alt-texts + 5 buyer guides + 40 termes glossaire + 12 comparisons + 5 top lists + About/Team ✅
- **Approximated.app** — custom domains reverse-proxy + SSL auto (Altea live sur altea-home.com) ✅
- **Domain skip Step 6** + enforcement QA Step 10 ✅
- **GMC Auto-onboarding** (identité légale + shipping + returns + feed XML, 1 clic) ✅
- **Marketing Off-Page** : 20 annuaires senior/silver-eco + Pinterest stub + Featured.com worker ✅
- **Dynamic Rendering** pour bots (`/api/seo/prerender/`, `robots.smart.txt`, `sitemap-prerender.xml`) ✅
- **GSC auto-provisioning** sur verify_custom_domain (idempotent) ✅
- **Token-swap admin** Pinterest + Featured (probe + persist .env + live-reload) ✅
- **Doc OAuth Production** (rotation 7j → PUBLISH APP) ✅

**Statut système actuel** : 76 routers · **404 endpoints** · 24 jobs APScheduler · 4 sites en base (Altea staging, Demo Hero, Projet Matelas, Auralia draft).

## 🔴 P0 — Actions user requises (bloquantes)

- [ ] **Reconnecter Google Master OAuth** : `https://altiaro.com/admin/google-master` → bouton « Reconnecter » (refresh_token actuel expiré → `invalid_grant` sur GMC/GSC/Ads/SiteVerification). Cf `memory/GOOGLE_OAUTH_PRODUCTION_SETUP.md`.
- [ ] **Passer GCP en mode Production** (PUBLISH APP sur OAuth consent screen) pour stopper la rotation tous les 7 jours.
- [ ] **Pinterest** : générer un nouveau PAT avec scopes `boards:write` + `pins:write` (https://developers.pinterest.com/apps/) puis `POST /api/admin/integrations/pinterest/update-token`.
- [ ] **Featured.com** : récupérer `FEATURED_API_KEY` (https://featured.com → settings → API) puis `POST /api/admin/integrations/featured/update-key`.

## 🟡 P1 — Code à faire

- [ ] **Server-side WebP/AVIF conversion** sur `GET /api/uploads/*?format=webp|avif` (le storefront a déjà les `<picture>` côté front, fallback PNG/JPG actuel).
- [ ] **Featured.com — finaliser le worker** (parser réponses queries, mapper aux pitches AI, suivi statut). En attente API key user.
- [ ] **Pinterest publisher** — activer la création réelle de boards + pins une fois le PAT à jour.

## 🟡 P2

- [ ] Edge-level UA routing pour bots SSR (alternative au `robots.smart.txt` actuel — uniquement si certains bots ignorent robots.txt).
- [ ] Marketplace des analyses (deep analyses partagées globalement aux Concepteurs, lock 7j).
- [ ] Page Leads Concepteur (formulaires contact storefront → CRM lite).
- [ ] Mollie Refunds depuis Ops Center.
- [ ] DeepL API pour traduction pro (alternative à Claude translate).
- [ ] Trust badges dynamiques, scarcity countdown, social proof, exit-intent popup.

## 🟢 P3 — Extensions

- [ ] API bancaire (Wise/GoCardless/Qonto) pour virements 100% auto.
- [ ] Historique des designs avec rollback.
- [ ] A/B tests de design (split 50/50).
- [ ] Copilot tools étendus.
- [ ] Webhooks Concepteurs (Zapier).

## ❌ Retiré (décision user)

- ~~Mollie Connect — split commission 5% Altiaro~~ — décision 2026-04-27, ROI faible vs complexité.
- ~~Google Ads Campaign Management depuis UI Admin~~ — user gère les Ads à part (OAuth reste pour Keyword Planner + lecture campagnes).
- ~~Cloudflare for SaaS / Caddy~~ — remplacé par Approximated.app le 2026-05-01.

## 🚀 Next action items (par priorité)

1. **User-side** : Reconnecter Google Master + PUBLISH APP GCP.
2. **User-side** : Pinterest PAT avec write scopes + Featured API key.
3. **Code P1** : WebP/AVIF backend (perf storefront + Lighthouse).
4. **Code P1** : finaliser pipeline Featured dès key reçue.
5. **Cible produit** : finaliser Altea de `staging` → `active` (premier site officiel), puis valider la cadence 10 sites/jour/concepteur.
