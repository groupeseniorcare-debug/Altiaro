"""
Pages légales plateforme Altiaro — fallback HTML server-side.

OBJECTIF : sur le domaine `altiaro.com` (Emergent Native Deploy + Cloudflare),
le frontend React production peut être figé sur un build qui ne contient pas
encore les routes `/legal/*` ajoutées récemment. Pour ne pas bloquer la
validation Google Merchant Center MCA (qui crawle les URLs soumises dans les
24-48 h), on expose ici les 5 mêmes pages directement depuis FastAPI, en HTML
pur premium, MONTÉES AU NIVEAU DE `app` (sans préfixe `/api`).

Côté preview Kubernetes, l'ingress route `/legal/*` au frontend port 3000,
donc ces routes ne sont JAMAIS appelées sur le sandbox — le SPA React
continue de gérer les pages légales en preview comme avant. Côté prod
Emergent Native Deploy, FastAPI sert généralement à la fois l'API et le
frontend statique : les routes définies ici prennent alors la priorité sur
le fallback SPA et garantissent un HTML 200 valide pour Google.

⚠️ Toutes les modifications de contenu doivent rester synchronisées avec :
   - frontend/src/pages/PlatformLegal{Retours,Livraison,Cgv,...}.jsx
   - backend/altiaro_legal.py::PLATFORM_COMPANY (source de vérité société)
"""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, RedirectResponse

from altiaro_legal import PLATFORM_COMPANY

# IMPORTANT : ce router est MONTÉ DIRECTEMENT DANS `app`, pas dans le router
# `/api`. Il sert des URLs publiques `/legal/*` (sans préfixe /api).
router = APIRouter(tags=["public-legal-html"], include_in_schema=False)

LEGAL_LAST_UPDATE_FR = "29 avril 2026"


def _company():
    """Retourne le dict société Altiaro (statique, pas d'I/O DB)."""
    return PLATFORM_COMPANY


# ──────────────────────────── Layout HTML ──────────────────────────── #


def _render(title: str, eyebrow: str, current_slug: str, body_html: str) -> HTMLResponse:
    """Génère la page légale HTML complète (head + sidebar + contenu + pied
    société + footer). Style inline pour ne dépendre d'aucun CSS externe.
    """
    c = _company()
    sections = [
        ("mentions", "Mentions légales", "/legal/mentions"),
        ("cgv", "Conditions générales de vente", "/legal/cgv"),
        ("confidentialite", "Politique de confidentialité", "/legal/confidentialite"),
        ("livraison", "Politique de livraison", "/legal/livraison"),
        ("retours", "Politique de retour", "/legal/retours"),
    ]
    sidebar_links = "\n".join(
        f'<a href="{path}" class="nav-link {"is-active" if slug == current_slug else ""}">{label}</a>'
        for slug, label, path in sections
    )
    year = date.today().year

    css = """
:root { color-scheme: light; }
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; }
body {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  background: #F5F2EB;
  color: #3F3F3F;
  font-size: 15px;
  line-height: 1.7;
  min-height: 100vh;
  -webkit-font-smoothing: antialiased;
}
a { color: #1A1A1A; text-decoration: underline; text-underline-offset: 2px; transition: color .2s ease; }
a:hover { color: #0F6E4D; }
header.platform-header {
  border-bottom: 1px solid #E8E2D5;
  background: #FDFCF9;
}
header.platform-header .inner {
  max-width: 1100px;
  margin: 0 auto;
  padding: 18px 28px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}
.brand-logo {
  font-family: 'Cormorant Garamond', Georgia, serif;
  font-weight: 500;
  font-size: 26px;
  letter-spacing: -0.01em;
  color: #1A1A1A;
  text-decoration: none;
}
header.platform-header .home-link {
  font-size: 12px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: #6B6B6B;
  text-decoration: none;
}
header.platform-header .home-link:hover { color: #1A1A1A; }
.layout {
  max-width: 1100px;
  margin: 0 auto;
  padding: 48px 28px 64px;
  display: grid;
  grid-template-columns: 260px 1fr;
  gap: 48px;
}
@media (max-width: 880px) {
  .layout { grid-template-columns: 1fr; gap: 24px; padding: 28px 18px 48px; }
}
.sidebar .eyebrow {
  font-size: 10px;
  letter-spacing: 0.3em;
  text-transform: uppercase;
  color: #8B8174;
  margin-bottom: 14px;
}
.sidebar nav { display: flex; flex-direction: column; gap: 2px; }
.nav-link {
  display: block;
  padding: 10px 14px;
  font-size: 14px;
  text-decoration: none;
  color: #6B6B6B;
  border-left: 2px solid transparent;
  transition: all .2s ease;
}
.nav-link:hover { color: #1A1A1A; background: rgba(255,255,255,.6); }
.nav-link.is-active {
  background: #FFFFFF;
  color: #1A1A1A;
  font-weight: 500;
  border-left-color: #1A1A1A;
}
article.legal-article {
  background: #FFFFFF;
  border: 1px solid #E8E2D5;
  border-radius: 2px;
  padding: 40px 48px;
}
@media (max-width: 880px) { article.legal-article { padding: 24px 22px; } }
article .eyebrow {
  font-size: 10px;
  letter-spacing: 0.32em;
  text-transform: uppercase;
  color: #8B8174;
  margin-bottom: 14px;
}
article h1 {
  font-family: 'Cormorant Garamond', Georgia, serif;
  font-weight: 400;
  font-size: 42px;
  line-height: 1.1;
  letter-spacing: -0.01em;
  color: #1A1A1A;
  margin: 0 0 28px 0;
}
@media (max-width: 880px) { article h1 { font-size: 32px; } }
.legal-content h2 {
  font-family: 'Cormorant Garamond', Georgia, serif;
  font-weight: 500;
  font-size: 22px;
  line-height: 1.25;
  color: #1A1A1A;
  margin: 28px 0 10px 0;
}
.legal-content h2:first-child { margin-top: 0; }
.legal-content h3 {
  font-family: 'Cormorant Garamond', Georgia, serif;
  font-weight: 500;
  font-size: 17px;
  color: #1A1A1A;
  margin: 22px 0 6px 0;
}
.legal-content p { margin: 12px 0; color: #3F3F3F; }
.legal-content ul { padding-left: 22px; margin: 12px 0; }
.legal-content ul li { margin: 6px 0; }
.legal-content strong { font-weight: 600; color: #1A1A1A; }
.legal-content em { font-style: italic; }
.legal-content table {
  width: 100%;
  border-collapse: collapse;
  margin: 14px 0 18px;
  font-size: 13.5px;
}
.legal-content table thead { background: #FAF7F0; }
.legal-content table th, .legal-content table td {
  border: 1px solid #E8E2D5;
  padding: 9px 11px;
  text-align: left;
  vertical-align: top;
}
.legal-content table th {
  font-weight: 600;
  font-size: 11.5px;
  letter-spacing: .04em;
  text-transform: uppercase;
  color: #6B6B6B;
}
.last-update {
  margin-top: 36px;
  padding-top: 20px;
  border-top: 1px solid #E8E2D5;
  font-size: 12px;
  color: #8B8174;
}
.company-block {
  margin-top: 24px;
  background: #FDFCF9;
  border: 1px solid #E8E2D5;
  border-radius: 2px;
  padding: 24px 28px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 18px;
  font-size: 13px;
  line-height: 1.65;
  color: #6B6B6B;
}
@media (max-width: 720px) { .company-block { grid-template-columns: 1fr; } }
.company-block .label {
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: .26em;
  color: #8B8174;
  margin-bottom: 8px;
}
.company-block strong { color: #1A1A1A; font-weight: 600; }
footer.platform-footer {
  margin-top: 48px;
  padding: 26px 0;
  text-align: center;
  font-size: 12px;
  color: #8B8174;
  border-top: 1px solid #E8E2D5;
  background: #FDFCF9;
}
"""

    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta name="description" content="{title} — Altiaro, plateforme e-commerce premium." />
  <link rel="canonical" href="https://altiaro.com/legal/{current_slug}" />
  <title>{title} · Altiaro</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;500;600&family=Inter:wght@400;500;600&display=swap" rel="stylesheet" />
  <style>{css}</style>
</head>
<body>
  <header class="platform-header">
    <div class="inner">
      <a href="/" class="brand-logo">Altiaro</a>
      <a href="/" class="home-link">← Retour à l'accueil</a>
    </div>
  </header>

  <div class="layout">
    <aside class="sidebar">
      <div class="eyebrow">Informations légales</div>
      <nav>{sidebar_links}</nav>
    </aside>

    <main>
      <article class="legal-article">
        <div class="eyebrow">{eyebrow}</div>
        <h1>{title}</h1>
        <div class="legal-content">{body_html}</div>
        <div class="last-update">Dernière mise à jour : {LEGAL_LAST_UPDATE_FR}.</div>
      </article>

      <div class="company-block">
        <div>
          <div class="label">Éditeur</div>
          <strong>{c['nom']}</strong><br/>
          {c['forme_juridique']}<br/>
          SIREN&nbsp;{c['siren']}<br/>
          SIRET&nbsp;{c['siret']}<br/>
          APE&nbsp;{c['code_naf']}<br/>
          {c['adresse']}
        </div>
        <div>
          <div class="label">Contact</div>
          Email : <a href="mailto:{c['email']}">{c['email']}</a><br/>
          Téléphone : {c['telephone']}<br/>
          Directeur de publication : {c['directeur_publication']}<br/><br/>
          Hébergement : {c['hebergeur_nom']} — {c['hebergeur_adresse']}
        </div>
      </div>
    </main>
  </div>

  <footer class="platform-footer">© {year} {c['nom']}. Tous droits réservés.</footer>
</body>
</html>"""
    return HTMLResponse(content=html, status_code=200)


# ──────────────────────────── Contenus ──────────────────────────── #


def _retours_body() -> str:
    c = _company()
    return f"""
<h2>Préambule</h2>
<p>Altiaro est une plateforme SaaS qui héberge des boutiques en ligne créées et gérées par des
concepteurs indépendants. Chaque boutique hébergée dispose de sa propre politique de retour,
conforme aux dispositions du Code de la consommation, accessible depuis la fiche produit
ainsi que depuis le pied de page de la boutique concernée.</p>
<p>La présente politique décrit&nbsp;: (i) le cadre commun applicable aux achats effectués sur les
boutiques hébergées par la plateforme Altiaro, et (ii) le régime applicable aux services
Altiaro souscrits par les concepteurs.</p>

<h2>1. Achats effectués sur une boutique hébergée par Altiaro</h2>
<h3>1.1. Délai de rétractation</h3>
<p>Conformément à l'article L221-18 du Code de la consommation, le consommateur dispose d'un
<strong>délai de rétractation de 30 jours</strong> à compter de la réception du produit pour
exercer son droit de retour, sans avoir à motiver sa décision ni à supporter d'autres coûts
que ceux prévus aux articles L221-23 à L221-25 du même Code.</p>
<h3>1.2. Conditions du retour</h3>
<ul>
  <li>Le produit doit être retourné non utilisé, dans son emballage d'origine ;</li>
  <li>Tous les accessoires, notices et documents fournis doivent être joints ;</li>
  <li>Une copie de la confirmation de commande (numéro commençant par <em>CF-XXXX</em>) doit accompagner l'envoi.</li>
</ul>
<h3>1.3. Frais de retour</h3>
<p>Les frais de retour sont à la charge de l'acheteur, sauf en cas de défaut du produit, de
non-conformité, ou d'erreur du marchand, auquel cas ils sont intégralement pris en charge
par la boutique vendeuse.</p>
<h3>1.4. Remboursement</h3>
<p>Le remboursement intervient dans un délai maximum de <strong>14 jours</strong> à compter de
la réception et de l'inspection du produit retourné, conformément à l'article L221-24 du
Code de la consommation. Le remboursement est effectué par le même moyen de paiement que
celui utilisé lors de la commande, sauf accord exprès du consommateur.</p>
<h3>1.5. Procédure</h3>
<p>Pour initier une demande de retour, le consommateur contacte le service client de la
boutique vendeuse via la page Contact de cette boutique (les coordonnées figurent dans les
CGV de la boutique concernée).</p>
<h3>1.6. Produits exclus du droit de rétractation</h3>
<p>Conformément à l'article L221-28 du Code de la consommation, certains biens sont exclus du
droit de rétractation, notamment&nbsp;: les biens confectionnés selon les spécifications du
consommateur ou nettement personnalisés, les biens scellés ne pouvant être renvoyés pour
des raisons d'hygiène ou de protection de la santé après ouverture, et les biens descellés
après livraison ne pouvant être renvoyés.</p>

<h2>2. Services Altiaro souscrits par les concepteurs</h2>
<p>Les abonnements et frais de plateforme Altiaro souscrits par les concepteurs sont régis
par les <a href="/legal/cgv">Conditions générales de vente Altiaro</a>. Conformément à
l'article L221-28 1° du Code de la consommation, les services pleinement exécutés avant la
fin du délai de rétractation, avec l'accord exprès préalable du concepteur, ne sont pas
soumis à rétractation.</p>

<h2>3. Médiation de la consommation</h2>
<p>Conformément à l'article L612-1 du Code de la consommation, le consommateur peut, en cas
de litige non résolu amiablement, recourir gratuitement à un médiateur de la consommation.
Plus d'informations sur&nbsp;:
<a href="{c['mediateur_url']}" target="_blank" rel="noreferrer noopener">{c['mediateur_url']}</a>.</p>

<h2>4. Droit applicable et juridiction</h2>
<p>La présente politique est soumise au droit français. En cas de litige, et après échec d'une
tentative de résolution amiable, le consommateur peut saisir, à son choix, l'une des
juridictions territorialement compétentes en vertu du Code de procédure civile, ou la
juridiction du lieu où il demeurait au moment de la conclusion du contrat ou de la
survenance du fait dommageable.</p>

<h2>5. Contact Altiaro</h2>
<p>Pour toute question relative à la présente politique&nbsp;:<br/>
Email&nbsp;: <a href="mailto:{c['email']}">{c['email']}</a><br/>
Adresse&nbsp;: {c['adresse']}</p>
"""


def _livraison_body() -> str:
    c = _company()
    return f"""
<h2>Préambule</h2>
<p>Altiaro est une plateforme SaaS qui héberge des boutiques en ligne créées et exploitées par
des concepteurs indépendants. Chaque boutique hébergée définit, dans ses propres conditions
générales, les modalités précises d'expédition (transporteurs, délais régionaux, frais de
port). La présente politique décrit le cadre commun applicable.</p>

<h2>1. Zones de livraison</h2>
<p>Les boutiques hébergées sur la plateforme Altiaro livrent prioritairement en France
métropolitaine, dans l'Union européenne et au Royaume-Uni. La liste exacte des pays
desservis et les frais associés sont précisés sur chaque fiche produit avant validation de
la commande, ainsi qu'à l'étape de paiement.</p>

<h2>2. Délais de livraison</h2>
<ul>
  <li><strong>Préparation de commande</strong>&nbsp;: 1 à 3 jours ouvrés à compter de la confirmation de paiement.</li>
  <li><strong>Expédition France métropolitaine</strong>&nbsp;: 3 à 7 jours ouvrés (standard), 1 à 3 jours (express le cas échéant).</li>
  <li><strong>Expédition Union européenne</strong>&nbsp;: 5 à 12 jours ouvrés.</li>
  <li><strong>Expédition Royaume-Uni</strong>&nbsp;: 7 à 14 jours ouvrés (formalités douanières post-Brexit prises en charge par le transporteur).</li>
</ul>
<p>Les délais indicatifs sont susceptibles d'évoluer pendant les périodes de forte activité
(soldes, fêtes de fin d'année). Le délai contractuel maximum, conformément à l'article
L216-2 du Code de la consommation, est de <strong>30 jours</strong> à compter de la
conclusion du contrat, sauf accord exprès et écrit pour un délai différent.</p>

<h2>3. Transporteurs</h2>
<p>Les boutiques hébergées font appel à des transporteurs professionnels reconnus, tels
que&nbsp;: La Poste / Colissimo, Mondial Relay, Chronopost, DPD, UPS et FedEx. Le
transporteur retenu pour chaque commande est précisé sur la confirmation de commande et
dans l'email de suivi d'expédition.</p>

<h2>4. Frais de port</h2>
<p>Les frais de port sont calculés en temps réel au moment du panier, en fonction du poids
total, du volume, du pays de livraison et de l'option d'expédition retenue. L'utilisateur
les visualise et les valide expressément avant le paiement.</p>
<p>Certaines boutiques proposent la <strong>livraison gratuite</strong> au-delà d'un montant
minimum d'achat ou pour des produits éligibles. Cette mention figure alors sur la fiche
produit.</p>

<h2>5. Suivi de commande</h2>
<p>Dès l'expédition, le client reçoit un email contenant le numéro de suivi et un lien vers la
page <em>Suivi de commande</em> de la boutique concernée. Cette page permet de suivre
l'acheminement du colis en temps réel.</p>

<h2>6. Retard, perte ou avarie</h2>
<p>En cas de retard significatif (au-delà du délai contractuel maximum de 30 jours), de perte
ou d'avarie constatée à la réception, le client peut&nbsp;: (i) contacter le service client
de la boutique pour ouvrir une réclamation, et (ii) résoudre le contrat conformément à
l'article L216-6 du Code de la consommation. Le remboursement intervient alors dans un
délai maximum de 14 jours.</p>

<h2>7. Réception et vérification</h2>
<p>Le destinataire est invité à vérifier l'état du colis à la réception. En cas de colis
endommagé, il doit émettre des réserves précises auprès du transporteur et notifier la
boutique vendeuse dans les meilleurs délais (idéalement sous 48 heures), photos à l'appui.</p>

<h2>8. Adresse de livraison incorrecte</h2>
<p>Il appartient au client de vérifier l'exactitude de l'adresse de livraison saisie. Toute
erreur ou omission entraînant un échec de livraison ou un retour à l'expéditeur peut donner
lieu à une nouvelle facturation des frais de port pour réexpédition.</p>

<h2>9. Contact</h2>
<p>Pour toute question relative à la livraison d'une commande passée sur l'une des boutiques
hébergées, contacter le service client de la boutique via sa page Contact. Pour toute
question relative à la plateforme Altiaro elle-même&nbsp;:<br/>
Email&nbsp;: <a href="mailto:{c['email']}">{c['email']}</a><br/>
Adresse&nbsp;: {c['adresse']}</p>
"""


def _cgv_body() -> str:
    c = _company()
    return f"""
<h2>Article 1. Objet</h2>
<p>Les présentes Conditions générales de vente (« CGV ») ont pour objet de définir les
modalités contractuelles applicables entre {c['nom']} (« Altiaro »), éditeur de la plateforme
accessible à l'adresse <a href="{c['site_web']}">{c['site_web']}</a>, et toute personne
physique ou morale (« le Concepteur ») souscrivant aux services de création et d'hébergement
de boutiques en ligne proposés par Altiaro.</p>
<p>Toute souscription implique l'acceptation pleine et entière des présentes CGV.</p>

<h2>Article 2. Éditeur — Identité</h2>
<ul>
  <li>Dénomination&nbsp;: {c['nom']}</li>
  <li>Forme juridique&nbsp;: {c['forme_juridique']}</li>
  <li>SIREN&nbsp;: {c['siren']} · SIRET&nbsp;: {c['siret']} · APE&nbsp;: {c['code_naf']}</li>
  <li>Activité&nbsp;: {c['activite']}</li>
  <li>{c['rne_inscription']}</li>
  <li>{c['tva_mention_cgv']}</li>
  <li>Siège social&nbsp;: {c['adresse']}</li>
  <li>Email&nbsp;: <a href="mailto:{c['email']}">{c['email']}</a> · Téléphone&nbsp;: {c['telephone']}</li>
</ul>

<h2>Article 3. Description des services</h2>
<p>Altiaro met à la disposition des Concepteurs un environnement logiciel permettant la
création, la personnalisation et l'exploitation d'une boutique en ligne&nbsp;: hébergement
technique, outils d'aide à la conception (génération de contenu, visuels, recommandations),
modules de paiement intégrés, modules d'analyse de performance et outils SEO/AEO.</p>

<h2>Article 4. Souscription — Compte concepteur</h2>
<p>L'accès aux services suppose la création d'un compte. Le Concepteur garantit l'exactitude
des informations transmises et s'engage à les maintenir à jour. Il est responsable de la
confidentialité de ses identifiants. Toute action effectuée via son compte est réputée être
de son fait.</p>

<h2>Article 5. Tarifs et facturation</h2>
<p>Les tarifs des services sont indiqués sur la plateforme Altiaro et lors de la souscription.
La mention <strong>« {c['tva_mention_cgv']} »</strong> s'applique aux prestations facturées.
Les prix sont exprimés en euros, sans TVA à ce titre.</p>
<p>La facturation intervient selon la périodicité souscrite (mensuelle, annuelle ou à la
prestation). Les factures sont adressées par voie électronique.</p>

<h2>Article 6. Modalités de paiement</h2>
<p>Le paiement est réalisé via les prestataires de paiement intégrés (notamment Mollie). En
cas de défaut de paiement et après mise en demeure infructueuse, Altiaro se réserve la
faculté de suspendre l'accès aux services jusqu'à régularisation et, à défaut, de résilier
le contrat de plein droit.</p>

<h2>Article 7. Droit de rétractation</h2>
<p>Conformément à l'article L221-28 1° du Code de la consommation, le droit de rétractation
ne peut s'exercer pour les services pleinement exécutés avant la fin du délai de
rétractation, lorsque cette exécution a commencé après accord préalable exprès du
consommateur et renoncement exprès à son droit de rétractation.</p>

<h2>Article 8. Obligations du Concepteur</h2>
<ul>
  <li>Respecter les lois et règlements applicables au commerce électronique, à la consommation et à la protection des données personnelles ;</li>
  <li>Ne pas vendre de produits illicites, contrefaits, dangereux ou prohibés ;</li>
  <li>Disposer des droits et autorisations nécessaires sur les contenus mis en ligne ;</li>
  <li>Répondre des relations contractuelles avec ses propres clients (livraison, SAV, retours, médiation) ;</li>
  <li>Maintenir des conditions de vente et politiques (CGV, livraison, retours) accessibles depuis sa boutique.</li>
</ul>

<h2>Article 9. Propriété intellectuelle</h2>
<p>La plateforme Altiaro, son architecture logicielle, ses interfaces graphiques, ses contenus
éditoriaux et les marques associées sont la propriété exclusive de {c['nom']}. Toute
reproduction ou utilisation non autorisée est strictement prohibée. Le Concepteur conserve
l'entière propriété intellectuelle des contenus qu'il publie sur sa boutique.</p>

<h2>Article 10. Données personnelles</h2>
<p>Les modalités de traitement des données personnelles sont détaillées dans la
<a href="/legal/confidentialite">politique de confidentialité</a>, qui fait partie intégrante
des présentes CGV.</p>

<h2>Article 11. Disponibilité et maintenance</h2>
<p>Altiaro met en œuvre les moyens raisonnables pour assurer la disponibilité des services,
sans garantir une disponibilité ininterrompue. Des opérations de maintenance peuvent
entraîner des interruptions temporaires, qui seront, dans la mesure du possible, annoncées
au préalable.</p>

<h2>Article 12. Responsabilité</h2>
<p>La responsabilité d'Altiaro est limitée aux dommages directs prouvés. Altiaro ne pourra
être tenue responsable des dommages indirects, ni des conséquences d'un usage non conforme
de la plateforme par le Concepteur ou par les clients de sa boutique.</p>

<h2>Article 13. Résiliation</h2>
<p>Le Concepteur peut résilier son abonnement à tout moment depuis son espace de gestion.
Altiaro peut résilier le contrat en cas de manquement grave et persistant aux présentes CGV
après mise en demeure infructueuse pendant 15 jours.</p>

<h2>Article 14. Garanties légales</h2>
<p>Lorsque l'utilisateur est un consommateur au sens du Code de la consommation, il bénéficie
de plein droit de la garantie légale de conformité (articles L217-3 à L217-20 du Code de la
consommation) et de la garantie légale des vices cachés (articles 1641 à 1648 et 2232 du
Code civil).</p>

<h2>Article 15. Médiation</h2>
<p>Conformément à l'article L612-1 du Code de la consommation, le consommateur peut recourir
gratuitement à un médiateur de la consommation. Plus d'informations sur&nbsp;:
<a href="{c['mediateur_url']}" target="_blank" rel="noreferrer noopener">{c['mediateur_url']}</a>.</p>

<h2>Article 16. Droit applicable et juridiction compétente</h2>
<p>Les présentes CGV sont régies par le droit français. À défaut de résolution amiable, tout
litige sera porté devant le tribunal compétent ({c['juridiction']}), sous réserve des règles
impératives applicables aux consommateurs en matière de compétence territoriale.</p>
"""


def _confidentialite_body() -> str:
    c = _company()
    return f"""
<h2>Préambule</h2>
<p>La présente politique décrit la manière dont {c['nom']} (« Altiaro ») collecte, utilise,
conserve et protège les données à caractère personnel, conformément au Règlement (UE)
2016/679 (RGPD) et à la loi n° 78-17 du 6 janvier 1978 modifiée (Informatique et Libertés).</p>

<h2>1. Responsable de traitement</h2>
<p>Le responsable de traitement est&nbsp;: {c['nom']}, {c['adresse']}. Pour toute question
relative aux données personnelles&nbsp;:
<a href="mailto:{c['dpo_email']}">{c['dpo_email']}</a>.</p>
<p>Lorsque le visiteur navigue sur une boutique hébergée, le concepteur indépendant qui
exploite cette boutique est, le cas échéant, responsable de traitement conjoint pour les
traitements liés à la commande, à la livraison et à la relation client. Altiaro agit en
sous-traitant au sens de l'article 28 du RGPD pour les traitements liés à l'hébergement et
aux outils logiciels.</p>

<h2>2. Données collectées</h2>
<ul>
  <li><strong>Données de compte concepteur</strong>&nbsp;: nom, email, mot de passe haché, informations de facturation.</li>
  <li><strong>Données de compte client (boutiques)</strong>&nbsp;: nom, email, adresses, historique de commandes.</li>
  <li><strong>Données de paiement</strong>&nbsp;: traitées directement par Mollie. Altiaro ne stocke pas les numéros de carte.</li>
  <li><strong>Données de navigation</strong>&nbsp;: adresses IP, identifiants techniques, journaux de connexion, statistiques d'usage.</li>
  <li><strong>Cookies et traceurs</strong>&nbsp;: voir section 7.</li>
</ul>

<h2>3. Finalités et bases légales</h2>
<table>
  <thead>
    <tr><th>Finalité</th><th>Base légale</th><th>Conservation</th></tr>
  </thead>
  <tbody>
    <tr><td>Exécution du contrat de service</td><td>Article 6.1.b RGPD</td><td>Durée du contrat + 5 ans</td></tr>
    <tr><td>Gestion des commandes</td><td>Article 6.1.b RGPD</td><td>10 ans (art. L123-22 C. com.)</td></tr>
    <tr><td>Marketing direct (newsletters)</td><td>Article 6.1.a RGPD — consentement</td><td>3 ans</td></tr>
    <tr><td>Sécurité et anti-fraude</td><td>Article 6.1.f RGPD — intérêts légitimes</td><td>1 an</td></tr>
    <tr><td>Mesure d'audience</td><td>Article 6.1.f ou consentement</td><td>13 mois maximum</td></tr>
  </tbody>
</table>

<h2>4. Destinataires</h2>
<p>Les données sont destinées aux équipes habilitées d'Altiaro, aux concepteurs responsables
des boutiques (pour leurs propres clients) et aux sous-traitants techniques&nbsp;:</p>
<ul>
  <li>Hébergement&nbsp;: {c['hebergeur_nom']}.</li>
  <li>Paiements&nbsp;: Mollie B.V., agréé PSP par la DNB (Pays-Bas).</li>
  <li>Email transactionnel&nbsp;: Resend, Inc.</li>
  <li>Outils Google (Search Console, Analytics, Merchant)&nbsp;: Google Ireland Limited.</li>
  <li>Sourcing produits&nbsp;: AliExpress / CJ Dropshipping selon paramétrage.</li>
</ul>
<p>Tous les sous-traitants sont liés par un contrat conforme à l'article 28 du RGPD.</p>

<h2>5. Transferts hors UE</h2>
<p>Certains prestataires (Google, AliExpress) peuvent traiter des données hors UE. Ces
transferts sont encadrés par une décision d'adéquation (Data Privacy Framework pour les
prestataires américains adhérents) ou par les clauses contractuelles types adoptées par la
Commission européenne.</p>

<h2>6. Sécurité</h2>
<p>Altiaro met en œuvre des mesures techniques et organisationnelles appropriées&nbsp;:
chiffrement TLS, hachage des mots de passe (bcrypt), contrôles d'accès par rôles,
journalisation des actions sensibles, sauvegardes régulières.</p>

<h2>7. Cookies et traceurs</h2>
<p>La plateforme utilise des cookies strictement nécessaires (session, sécurité), des cookies
de mesure d'audience et, le cas échéant, des cookies marketing soumis à consentement. Le
visiteur peut accepter, refuser ou paramétrer ces cookies depuis le bandeau de
consentement.</p>

<h2>8. Droits des personnes</h2>
<p>Conformément aux articles 15 à 22 du RGPD, toute personne dispose des droits&nbsp;:
accès, rectification, effacement, limitation, opposition, portabilité, retrait du
consentement à tout moment, et droit de définir des directives relatives au sort des
données après décès.</p>
<p>Pour exercer ces droits&nbsp;: <a href="mailto:{c['dpo_email']}">{c['dpo_email']}</a>. Une
réponse est apportée dans un délai d'un mois.</p>
<p>En cas de désaccord, possibilité de réclamation auprès de la CNIL (3 place de Fontenoy,
TSA 80715, 75334 Paris Cedex 07 — <a href="https://www.cnil.fr" target="_blank" rel="noreferrer noopener">www.cnil.fr</a>).</p>

<h2>9. Mineurs</h2>
<p>Les services Altiaro et les boutiques hébergées ne sont pas destinés aux mineurs de moins
de 15 ans sans le consentement du titulaire de l'autorité parentale.</p>

<h2>10. Évolution de la politique</h2>
<p>La présente politique peut évoluer. Toute modification substantielle sera portée à la
connaissance des utilisateurs par tout moyen approprié.</p>
"""


def _mentions_body() -> str:
    c = _company()
    return f"""
<h2>1. Éditeur du site</h2>
<ul>
  <li>Dénomination&nbsp;: {c['nom']}</li>
  <li>Forme juridique&nbsp;: {c['forme_juridique']}</li>
  <li>SIREN&nbsp;: {c['siren']} · SIRET&nbsp;: {c['siret']} · APE&nbsp;: {c['code_naf']}</li>
  <li>Activité&nbsp;: {c['activite']}</li>
  <li>{c['rne_inscription']}</li>
  <li>TVA&nbsp;: {c['tva_intra']} · {c['tva_mention_cgv']}</li>
  <li>Siège social&nbsp;: {c['adresse']}</li>
  <li>Email&nbsp;: <a href="mailto:{c['email']}">{c['email']}</a></li>
  <li>Téléphone&nbsp;: {c['telephone']}</li>
  <li>Directeur de la publication&nbsp;: {c['directeur_publication']}</li>
</ul>

<h2>2. Hébergement</h2>
<p>La plateforme Altiaro est hébergée par&nbsp;: {c['hebergeur_nom']} —
{c['hebergeur_adresse']}.</p>

<h2>3. Activité</h2>
<p>Altiaro est une plateforme SaaS qui permet à des concepteurs indépendants de créer,
personnaliser et exploiter des boutiques en ligne premium. Altiaro fournit l'infrastructure,
les outils logiciels (génération de contenu, visuels, SEO/AEO, paiement, analytique) et
l'assistance technique. Les transactions commerciales réalisées sur les boutiques hébergées
sont conclues entre les concepteurs et leurs clients respectifs.</p>

<h2>4. Propriété intellectuelle</h2>
<p>L'ensemble des éléments accessibles sur la plateforme (textes, images, graphismes, logos,
icônes, sons, logiciels) sont protégés par le droit français et international de la
propriété intellectuelle. Sauf autorisation préalable et expresse, toute reproduction,
représentation, modification, publication ou adaptation est interdite.</p>
<p>Les marques et logos cités à des fins illustratives ou techniques (Google, Mollie, Resend,
AliExpress, etc.) sont la propriété de leurs détenteurs respectifs.</p>

<h2>5. Liens hypertextes</h2>
<p>La plateforme peut contenir des liens vers des sites tiers. Altiaro n'exerce aucun contrôle
sur ces sites et décline toute responsabilité quant à leur contenu, leurs pratiques ou leur
disponibilité.</p>

<h2>6. Données personnelles</h2>
<p>Le traitement des données personnelles est détaillé dans la
<a href="/legal/confidentialite">politique de confidentialité</a>.</p>

<h2>7. Cookies</h2>
<p>Le paramétrage des cookies est exposé dans la
<a href="/legal/confidentialite">politique de confidentialité</a>, section
« Cookies et traceurs ».</p>

<h2>8. Droit applicable et juridiction</h2>
<p>Les présentes mentions sont régies par le droit français. Toute contestation relative à
leur interprétation ou à leur exécution relèvera, à défaut de règlement amiable, du
tribunal compétent ({c['juridiction']}).</p>
"""


# ──────────────────────────── Routes ──────────────────────────── #


# Legacy URLs (slugs francisés longs) → 301 vers la nouvelle structure /legal/*.
# Permet aux moteurs de recherche et aux backlinks externes pointant vers
# `/legal/mentions-legales` (etc.) de ne jamais retourner un 404. Servi aussi
# sous host custom (altea-home.com → backend FastAPI) car le middleware
# `custom_domain_middleware.py` court-circuite explicitement `/legal/*`.
_LEGAL_LEGACY_REDIRECTS = {
    "/legal/mentions-legales": "/legal/mentions",
    "/legal/conditions-generales": "/legal/cgv",
    "/legal/conditions-generales-de-vente": "/legal/cgv",
    "/legal/politique-confidentialite": "/legal/confidentialite",
    "/legal/politique-de-confidentialite": "/legal/confidentialite",
    "/legal/politique-de-retour": "/legal/retours",
    "/legal/politique-de-livraison": "/legal/livraison",
}


@router.get("/legal/mentions-legales", include_in_schema=False)
async def legal_redirect_mentions_legales():
    return RedirectResponse(url="/legal/mentions", status_code=301)


@router.get("/legal/conditions-generales", include_in_schema=False)
async def legal_redirect_conditions_generales():
    return RedirectResponse(url="/legal/cgv", status_code=301)


@router.get("/legal/conditions-generales-de-vente", include_in_schema=False)
async def legal_redirect_conditions_generales_de_vente():
    return RedirectResponse(url="/legal/cgv", status_code=301)


@router.get("/legal/politique-confidentialite", include_in_schema=False)
async def legal_redirect_politique_confidentialite():
    return RedirectResponse(url="/legal/confidentialite", status_code=301)


@router.get("/legal/politique-de-confidentialite", include_in_schema=False)
async def legal_redirect_politique_de_confidentialite():
    return RedirectResponse(url="/legal/confidentialite", status_code=301)


@router.get("/legal/politique-de-retour", include_in_schema=False)
async def legal_redirect_politique_de_retour():
    return RedirectResponse(url="/legal/retours", status_code=301)


@router.get("/legal/politique-de-livraison", include_in_schema=False)
async def legal_redirect_politique_de_livraison():
    return RedirectResponse(url="/legal/livraison", status_code=301)


@router.get("/legal/retours", response_class=HTMLResponse)
async def legal_retours():
    return _render(
        title="Politique de retour",
        eyebrow="Altiaro · Légal",
        current_slug="retours",
        body_html=_retours_body(),
    )


@router.get("/legal/livraison", response_class=HTMLResponse)
async def legal_livraison():
    return _render(
        title="Politique de livraison",
        eyebrow="Altiaro · Légal",
        current_slug="livraison",
        body_html=_livraison_body(),
    )


@router.get("/legal/cgv", response_class=HTMLResponse)
async def legal_cgv():
    return _render(
        title="Conditions générales de vente",
        eyebrow="Altiaro · Légal",
        current_slug="cgv",
        body_html=_cgv_body(),
    )


@router.get("/legal/confidentialite", response_class=HTMLResponse)
async def legal_confidentialite():
    return _render(
        title="Politique de confidentialité",
        eyebrow="Altiaro · Légal",
        current_slug="confidentialite",
        body_html=_confidentialite_body(),
    )


@router.get("/legal/mentions", response_class=HTMLResponse)
async def legal_mentions():
    return _render(
        title="Mentions légales",
        eyebrow="Altiaro · Légal",
        current_slug="mentions",
        body_html=_mentions_body(),
    )
