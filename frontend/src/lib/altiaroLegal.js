/**
 * Données légales société Altiaro — miroir frontend de
 * `backend/altiaro_legal.py` (PLATFORM_COMPANY).
 * Statique : pas d'appel réseau pour les pages /legal/*. Si la société
 * change, mettre à jour ici ET dans le fichier Python.
 */
export const ALTIARO_COMPANY = {
  nom: "Altiaro",
  forme_juridique: "Société",
  siren: "883 803 967",
  siret: "883 803 967 00016",
  date_creation: "30/05/2020",
  rne_inscription: "Inscrit au Registre National des Entreprises (RNE) le 30/05/2020",
  tva_intra: "Non applicable",
  tva_mention_cgv: "TVA non applicable, art. 293 B du CGI",
  code_naf: "4782Z",
  activite:
    "Commerce de détail sur éventaires et marchés (activité principale APE 4782Z) — e-commerce premium",
  adresse: "4 IMP CLOS FLEURI, 42320 FARNAY, France",
  email: "contact@altiaro.com",
  telephone: "+33 6 95 18 17 03",
  directeur_publication: "Altiaro",
  hebergeur_nom: "Emergent Labs",
  hebergeur_adresse: "Infrastructure Kubernetes (Cloudflare devant)",
  site_web: "https://altiaro.com",
  juridiction: "Tribunal de commerce de Saint-Étienne",
  dpo_email: "contact@altiaro.com",
  mediateur_nom: "Médiateur de la consommation",
  mediateur_url: "https://www.economie.gouv.fr/mediation-conso",
};

export const ALTIARO_LEGAL_LAST_UPDATE = "29 avril 2026";
