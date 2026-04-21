# Concept Factory — ROADMAP

Backlog priorisé.

## ✅ Livré
Auth · Sites CRUD · Quick Scan Go/No-Go multi-marchés async · Analyseur deep v2 · Catalogue i18n + cost_price_ht · Storefront dynamique (composants modulaires) · Orders + snapshot HT · Ads Copy · Duplication · Multi-domain · Scale 6 pays · Empire Dashboard · Mega-Blocks · AI Copilot · Mollie Checkout + CB + IBAN · Virements 50% marge brute HT (1er/15) · Site Designer IA-first (Prompt Studio 7 sections) · Pages légales auto · Sourcing CJ + AliExpress backend · Wizard 10 étapes guidées · SEO avancé (sitemap multi-pays hreflang, robots.txt, merchant-feed.xml RSS 2.0 par pays, Schema.org JSON-LD, Open Graph) · OVH domain purchase flow via Mollie (10€ markup) · Google Ads OAuth + Keyword Planner + Campaigns read · APScheduler cron auto-DNS · Thème UI Light (Ultra Premium Digital 2.0 light variant)

## 🔴 P0 — Prochaine session

### Google Merchant Center OAuth + push feed auto
**Blocké sur actions user Google (voir CHANGELOG 2026-04-21 Sprint 22 pour checklist)**
- [ ] User : créer GMC account + demander conversion MCA
- [ ] User : activer Content API dans Google Cloud Console
- [ ] User : ajouter scope `content` au OAuth consent screen + re-soumission vérification (3-5j)
- [ ] User : vérifier domaine + lier à Google Ads
- [ ] User : fournir Merchant ID
- [ ] **Puis côté code** : OAuth flow GMC (même pattern que Google Ads), sub-account management, push auto feed via APScheduler, UI Admin `/admin/merchant-center`, meta tag domain verification injecté auto dans storefront

### Marketplace des analyses (P1)
- [ ] Afficher toutes les deep analyses globalement aux Concepteurs
- [ ] Lock niche 7 jours par Concepteur
- [ ] UI browse + filter + "Réserver cette niche"

## 🟡 P1
- [ ] Fix CJ search : UX pour forcer les mots-clés en anglais côté UI (le user gère lui-même le sourcing, mais le frontend gagne à avertir)
- [ ] Sourcing alternatif pour matériel médicalisé senior (Spocket/Syncee/Modalyst EU) si la verticale fauteuil releveur reste cible
- [ ] Trust badges dynamiques, scarcity countdown, social proof (nb commandes 7j), upsell cart, exit-intent popup
- [ ] DeepL API pour traduction pro (alternative à Claude translate)

## 🟡 P2
- [ ] Page Leads Concepteur (formulaires contact storefront)
- [ ] Mollie Refunds depuis Ops Center
- [ ] Notification email Admin 1er/15 payouts (Resend)
- [ ] AliExpress Affiliate API integration (en attente validation compte)
- [ ] Fix OVH `"Your preferred payment method is not valid"` : le compte OVH plateforme doit avoir une CB par défaut (action infra, pas code)

## 🟢 P3 — Extensions
- [ ] API bancaire (Wise/GoCardless/Qonto) pour virements 100% auto
- [ ] Historique des designs avec rollback
- [ ] A/B tests de design (2 variations split 50/50)
- [ ] Copilot tools étendus
- [ ] Webhooks Concepteurs (Zapier)

## ❌ Retiré (décision user)
- ~~Google Ads Campaign Management depuis UI Admin~~ — user ne veut pas gérer les ads depuis l'admin (Google Ads OAuth reste en place pour Keyword Planner + lecture campagnes)

## 🚀 Next action items
1. **User-side Google Merchant Center setup** (checklist ci-dessus) — pré-requis bloquant
2. Implémenter GMC OAuth + push feed dès user ready
3. Marketplace des analyses
