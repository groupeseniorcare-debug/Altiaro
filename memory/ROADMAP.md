# Concept Factory — ROADMAP

Backlog priorisé. Voir CHANGELOG.md pour l'historique de ce qui a été livré.

## ✅ Livré (résumé haut niveau)
Auth JWT · Sites CRUD · Workflow 50 étapes (4 blocs) · Dashboard · Finances · Users · Niche Engine 20×6 · Catalogue i18n avec `cost_price_ht` · Storefront multilingue **dynamique** · Cart + Orders (snapshot HT) · Ops Center · Niche Analyzer · Ads Copy Generator · Site Duplication · Multi-domain CNAME · Scale 6 pays · Empire Dashboard · Mega-Block Execute · AI Copilot · Mollie Checkout + CB mandate + IBAN · **Virements 50% marge brute HT (1er/15)** · **Site Designer IA-first (Claude + Nano Banana logo + pages dynamiques)** · **Pages légales auto**

## 🔴 P0 — Automatisation remontée data

### Google Ads READ-ONLY sync
- [ ] Setup OAuth2 Admin (compte MCC + Developer Token)
- [ ] Mapping site ↔ campagne par **URL de destination finale** (choix C)
- [ ] Cron quotidien : pull spend, conversions, CPC, CTR, ROAS
- [ ] Alimente automatiquement le débit hebdo 50% du VRAI spend (vs. estimation daily_budget × 7)
- [ ] Affichage des KPIs réels dans Empire Dashboard + page site

## 🟡 P1 — Finitions billing & communication
- [ ] **Mollie Refunds** : déclencher des remboursements clients depuis Ops Center Admin
- [ ] **Notification email Admin** le 1er/15 : « X virements prêts pour Y € » (Resend)
- [ ] **Email SAV client** : notification au Concepteur quand un nouveau lead `/contact` arrive
- [ ] **Page Leads** dans SiteDetail pour que le Concepteur voie ses messages reçus

## 🟡 P2 — Améliorations Site Designer
- [ ] **Historique des designs** (rollback version-1) — actuellement écrase
- [ ] **A/B tests de design** : 2 variations générées, split 50/50
- [ ] **Diff reviewer** : mode « voilà la nouvelle proposition de l'IA, accepte section par section »
- [ ] **Images de catégorie / hero background** via Nano Banana (pas juste logo)
- [ ] **SEO sitemap.xml** auto-généré
- [ ] **Favicon** auto depuis logo

## 🟢 P3 — Extensions
- [ ] API bancaire (Wise/GoCardless/Qonto) pour virements 100% auto
- [ ] DataForSEO recalibrage Niche Engine
- [ ] Copilot tools étendus (refund, export CSV, change product status)
- [ ] Role granularity (super-admin, lead-concepteur)
- [ ] Webhooks Concepteurs (Zapier, Make)

## 🚀 Next action items
1. Validation utilisateur du Site Designer (tester un vrai cycle génération sur un site)
2. Google Ads READ-ONLY sync (clés API requises)
3. Email notifications via Resend
