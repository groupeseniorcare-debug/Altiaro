# Concept Factory — ROADMAP

Backlog priorisé. Voir CHANGELOG.md pour l'historique de ce qui a été livré.

## ✅ Livré (résumé haut niveau)
Auth JWT · Sites CRUD · Workflow 50 étapes (4 blocs logiques) · Dashboard KPIs · Finances manuelles · Users CRUD · Niche Engine 20×6 · Catalogue i18n (avec `cost_price_ht`) · Storefront multilingue · Cart + Orders (snapshot HT + cost) · Admin Ops Center · Niche Analyzer IA · Ads Copy Generator · Site Duplication · Multi-domain CNAME · Scale 6 pays · Empire Dashboard · Mega-Block Execute · AI Copilot conversationnel · **Mollie Checkout + CB mandate Concepteurs + IBAN** · **Virements Concepteurs auto = 50% × marge brute HT**

## 🔴 P0 — Automatisation remontée data

### Google Ads READ-ONLY sync (prochain chantier)
- [ ] Setup OAuth2 Admin (compte MCC + Developer Token)
- [ ] Mapping site ↔ campagne par **URL de destination finale** (choix utilisateur : option C)
- [ ] Cron quotidien : pull spend, conversions, CPC, CTR, ROAS
- [ ] Alimente automatiquement le débit hebdo 50% du VRAI spend (vs. estimation daily_budget × 7)
- [ ] Affichage des KPIs réels dans Empire Dashboard + page site

## 🟡 P1 — Finitions billing
- [ ] **Mollie Refunds** : déclencher des remboursements clients depuis Ops Center Admin (avec impact ledger inverse)
- [ ] **Notification email Admin** le 1er/15 : "X virements prêts pour Y €" (Resend) — actuellement juste stocké en DB
- [ ] **SAV workflow** : tickets, messages client, refunds partiels

## 🟡 P2 — Automatisation virements
- [ ] Option d'intégrer une **API bancaire** (Wise, GoCardless, API Qonto) pour déclencher les virements sans clic manuel — pour l'instant l'Admin copie l'IBAN + montant et exécute depuis sa banque

## 🟢 P3 — Extensions
- [ ] **Resend** emails transactionnels multi-langue
- [ ] **DataForSEO** recalibrage Niche Engine
- [ ] **Copilot tools étendus** (refund_order, export_orders_csv, change_product_status)
- [ ] **Role granularity** (super-admin vs admin, lead-concepteur)
- [ ] **Webhooks Concepteurs** (Zapier, Make)
- [ ] **Scheduled actions** (ex: baisser prix 5% chaque lundi)

## 🚀 Next action items
1. **Google Ads API sync** dès que l'Admin obtient Dev Token + OAuth credentials (guide à fournir)
2. **Mollie Refunds** (clés Mollie déjà présentes)
3. **Email Admin notifications** le 1er/15 (clé Resend requise)
