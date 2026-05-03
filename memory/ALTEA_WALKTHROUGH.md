# Walkthrough Altea — Démo des 10 étapes du Cockpit

> Site cobaye : **Altea** (`6867223e-7ea5-45a7-815a-300cd89b7656`) — domaine custom : `altea-home.com` (déjà acheté + vérifié).
> Compte concepteur : `concepteur@conceptfactory.fr` / `Factory2026!`.
> Toute la data IA (9 produits enrichis, 26 landings, 40 glossary, 18 articles, 3 auteurs, about_rich) est déjà en DB — tu peux donc cliquer rapidement sans attendre les générations IA.

## Vue d'ensemble

| # | Étape | Type | Durée | Coût LLM est. | Output visible côté storefront |
|---|---|---|---|---|---|
| 1 | Pricing | ⚡ instantané (data déjà en DB) | <30 s | 0 € | aucun |
| 2 | Import | ⚡ instantané | <30 s | 0 € | catalogue |
| 3 | Upsells | ⚡ instantané | <30 s | 0 € | bloc cross-sell PDP |
| 4 | Forecast | ⚡ instantané | <30 s | 0 € | aucun |
| 5 | Branding | 🤖 IA si `Lancer la création` | 4-6 min | ~3-5 € | header, hero, palette, logo |
| 6 | **Domaine** | 🌐 OVH + Approximated | 2-5 min | 0 € | **SKIPPABLE** (voir ⏭ ci-dessous) |
| 7 | Translate | 🤖 IA × 5 langues | 6-10 min | ~4-7 € | toggle FR/EN/ES/DE/IT/NL |
| 8 | Content (blog) | ⚡ déjà 18 articles | <30 s | 0 € | /blog, /buyer-guides, /glossary |
| 9 | SEO score | ⚡ instantané | <30 s | 0 € | sitemap, schemas, AEO |
| 10 | QA + Go-live | ⚡ checklist + bouton Publier | <30 s | 0 € | passage `staging → live` |

**Coût total Altea (re-cliquage complet sans regeneration)** : ~0 € si tu valides chaque étape avec la data existante. Si tu cliques "Régénérer" sur Branding/Translate ce sera 7-12 € de LLM.

---

## ⏭ Skip étape 6 — pour tester le flow sans domaine

**Backend** :
- `POST /api/sites/{id}/domain/skip` → set `site.domain_skipped=true`, débloque les étapes 7-10 via `_check_domain` (qui voit `optional=true`).
- `POST /api/sites/{id}/domain/unskip` → annule.

**Frontend (page Domains)** :
- Bouton **« Passer cette étape »** (encart pointillé en haut, visible si pas encore de domaine).
- Modal de confirmation avant skip.
- Si skip activé → encart « Étape reportée » avec bouton « Reprendre cette étape ».

**Bandeau persistant** sur toutes les pages cockpit (étapes 7-10) :
> ⚠️ Domaine non configuré. Étape obligatoire avant la mise en ligne — pense à revenir l'ajouter. **Configurer maintenant →**

**Étape 10** :
- Si `domain_skipped=true` ET pas de `custom_domain` → check `domain_configured` = **fail** → encart rouge inrouge en tête de la page QA + `qa.ready=false` → bouton « Mettre en ligne » grisé.
- Le concepteur doit cliquer **« Aller acheter un domaine →»** pour repasser à l'étape 6.

**Admin push Google Ads** :
- `POST /api/admin/sites/{id}/approve-for-ads` rejette **HTTP 409** avec `error: domain_required_for_ads` ou `qa_not_ready` si garde non-OK.

---

## Étape par étape — où cliquer

### 1) Pricing — `/sites/{id}/sourcing` ou cockpit step 1
- Bouton **« Lancer l'analyse pricing IA »** (bloc Sourcing).
- En coulisse : prompt Claude → matrice 15 produits + verdict GO/CAUTION/NO_GO.
- ⚠️ Altea a déjà `pricing_analysis.generated_at` ⇒ check `_check_pricing` retourne directement `completed=true`. Pas besoin de relancer.

### 2) Import — `/sites/{id}/products`
- 9 produits actifs déjà importés.
- Bouton **« Importer un produit »** (AliExpress / CJ / manuel) si tu veux en ajouter.
- Check : `>=5` produits + couverture pays. Altea a `force_partial=False` mais 9 produits ⇒ OK.

### 3) Upsells — `/sites/{id}/upsells`
- Liste de 40+ suggestions IA déjà générées.
- Cocher 3 produits comme `is_upsell=True` ou `role=upsell`.

### 4) Forecast — cockpit step 4
- Bouton **« Calculer le forecast 30j »** (instantané, pas de LLM, juste maths).

### 5) Branding — `/sites/{id}/branding`
- Si tu cliques **« Lancer la création complète »** : Claude génère brand book + Nano Banana génère hero/about images (4-6 min, ~5 €).
- Si tu cliques **« Publier ce design »** sans relancer : ça pousse `design.published=true` instantanément (Altea a déjà tout).

### 6) Domaine — `/sites/{id}/domains`
- 3 chemins :
  1. Acheter via Mollie (~12-25 €/an OVH). Auto-config OVH DNS + Approximated vhost.
  2. Lier un domaine déjà possédé (champ « Saisir un domaine »).
  3. **Skip** (voir ⏭ ci-dessus).

### 7) Translate — `/sites/{id}/translate`
- Bouton **« Traduire vers EN/ES/DE/IT/NL »**. Altea a déjà 6 langues actives.

### 8) Content (blog) — `/sites/{id}/blog-posts`
- 18 articles déjà publiés. Worker auto-publie 4/semaine (Mon/Tue/Thu/Fri 6h UTC).

### 9) SEO — `/sites/{id}/seo`
- Score auto-calculé (sitemap + schema + AEO + keywords). Altea: `seo_score >= 70` ⇒ OK.
- Bouton **« Connecter Google Search Console »** (OAuth) — non bloquant.

### 10) QA + Go-live — `/sites/{id}/qa`
- 22 checks. Score Altea : ~88/100.
- Bouton **« Mettre en ligne »** activé si `ready=true` (tous les fail résolus, dont `domain_configured`).
- Au clic : `status: staging → live` + IndexNow ping + email Resend de confirmation.

---

## Voir le rendu final

| Cas | URL |
|---|---|
| Domaine custom set + verified | `https://altea-home.com/` |
| Domaine skipped (pas de custom) | `/shop/6867223e-7ea5-45a7-815a-300cd89b7656/` (preview interne) |
| PDP enrichie (AEO + alt text) | `https://altea-home.com/products/fauteuil-releveur-electrique-avec-massage-et-relaxation` |
| Buyer guide | `https://altea-home.com/buyer-guides/comment-choisir-fauteuil-releveur-electrique-2026` |
| Glossary | `https://altea-home.com/glossary/releveur-electrique` |
| Comparison | `https://altea-home.com/compare/fauteuil-releveur-electrique-avec-massage-et-relaxation-vs-fauteuil-relaxation` |
| Top list | `https://altea-home.com/top/top-3-fauteuil-releveur-electrique-petit-salon` |
| Auteur | `https://altea-home.com/team/marie-claire-rousseau` |
| Sitemap | `https://altea-home.com/api/public/sites/6867223e-7ea5-45a7-815a-300cd89b7656/sitemap.xml` |

---

## Reset rapide (si besoin de re-tester de zéro)

```bash
# Reset à l'étape 5 (garde toutes les data, remet juste le gating au début)
curl -s -b cookies.txt -X POST \
  http://localhost:8001/api/admin/sites/6867223e-7ea5-45a7-815a-300cd89b7656/reset-to-step5
```

Le reset préserve : produits, design, narrations, images IA, blog, landings, glossary, about, authors, custom_domain.
Il efface uniquement les `manual_step_overrides` et remet `status=staging`.
