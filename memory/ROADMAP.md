# Concept Factory — ROADMAP

Backlog priorisé. Voir CHANGELOG.md pour l'historique de ce qui a été livré.

## ✅ Livré (résumé haut niveau)
Auth JWT · Sites CRUD · Workflow 50 étapes (4 blocs logiques) · Dashboard KPIs · Finances manuelles · Users CRUD · Niche Engine 20×6 · Catalogue i18n · Storefront multilingue · Cart + Orders · Admin Ops Center · Niche Analyzer IA · Ads Copy Generator · Site Duplication · Multi-domain CNAME · Scale 6 pays · Empire Dashboard · Mega-Block Execute · AI Copilot conversationnel

## 🔴 P1 — Phase 5 : Paiement réel (⏳ attente clés user)
- [ ] **Mollie** (paiement + payouts) — requiert clé API Mollie (test_xxx + live_xxx)
- [ ] **Resend** (emails transactionnels FR/EN/DE/NL) — requiert clé API + domaine vérifié
- [ ] **TVA multi-pays** (FR 20%, DE 19%, BE 21%, NL 21%, UK 20%, CH import)
- [ ] **Moteur 50/50** : calcul Marge Brute Partageable par commande (vs actuel flat 50%)
- [ ] **SAV workflow** : tickets, messages client, refunds partiels

## 🟡 P2 — Phase 6 : Scale & Automation
- [ ] **Google Ads Center** admin (lancement + monitoring via API, requiert clé Google Ads)
- [ ] **DataForSEO** : recalibrage métriques Niche Engine avec données réelles (clé DataForSEO)
- [ ] **Notifications admin** (email nouvelle commande, alertes auto → Slack/email)
- [ ] **Copilot étendu** : ajouter tools "refund_order", "change_product_status", "export_orders_csv"

## 🟢 P3 — Nice to have
- [ ] **Refactor seed_prompts.py en profondeur** — réécrire les 50 prompts en 4 mega-prompts (bénéfice UX marginal vs Mega-Block Execute déjà livré)
- [ ] **Public API docs** (OpenAPI auto-générée exposée via `/api/docs`)
- [ ] **Role granularity** : admin vs super-admin, concepteur vs lead-concepteur
- [ ] **Multi-langue UI** : l'interface admin/concepteur en plusieurs langues
- [ ] **Webhooks** Concepteurs → notifications externes (Zapier, Make)
- [ ] **Scheduled actions** (ex: baisser prix de 5% chaque lundi)

## 🚀 Next action items
1. **Phase 5** quand l'user fournit clés Mollie + Resend → feature la plus impactante
2. **Google Ads Center** quand clé Google Ads API fournie
3. **Copilot tools étendus** (refund, export) — aucune clé requise, poursuivre l'expérience AI-first
