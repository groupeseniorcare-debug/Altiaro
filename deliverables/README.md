# `/app/deliverables/` — dossier de livrables produit

## ⚠️ Contenu archivé (obsolète)

Les 2 fichiers du dossier `archive/` sont des **playbooks produit historiques** rédigés avant la Phase 4 de refonte (avril 2026). Ils décrivent une architecture cible **Shopify + React headless** qui **n'est plus la stack actuelle d'Altiaro**.

La stack réelle du projet est **100% custom FARM** :
- Backend : FastAPI + MongoDB (async via Motor)
- Frontend : React 19 + Craco + Tailwind 3 + shadcn/ui
- Pas de Shopify, pas de CMS externe — tout custom

Les playbooks archivés contiennent des références à `cart.js` Shopify, des checkout flows Shopify, des webhooks Shopify, etc. → **ne pas s'y fier pour implémenter du neuf**.

## 📚 Sources de vérité actuelles

| Sujet | Fichier |
|---|---|
| **Les 50 prompts** (cœur du playbook, 8 blocs thématiques) | `/app/backend/seed_prompts.py` (chargé au startup backend) |
| **Exigences produit** (65+ items, statut par item) | `/app/memory/PRD.md` |
| **Backlog priorisé** (P0/P1/P2/P3 roadmap) | `/app/memory/ROADMAP.md` |
| **Historique des sprints** (décisions + livraisons) | `/app/memory/CHANGELOG.md` |
| **Parcours technique** | `/app/README.md` (racine) |

## Pourquoi on garde les archives malgré tout

- Certains concepts (narratif "Silver Economy", tone of voice, parcours client) restent pertinents et pourraient servir d'inspiration copywriting.
- Traçabilité : l'historique de la vision produit est utile pour comprendre certaines décisions.

Si tu es dev et tu ouvres ces fichiers : **lis d'abord `/app/memory/PRD.md`**, puis reviens ici si besoin de contexte narratif.

## Futur usage de `/app/deliverables/`

Ce dossier peut servir à stocker des **livrables finaux** destinés au client / aux parties prenantes :
- Rapports de performance
- Presentations investisseurs
- Exports PDF / docs de synthèse

**Ne pas y mettre** de code source, de tests, ni de documentation technique (qui va dans `/app/docs/` ou `/app/memory/`).
