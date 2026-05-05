import React, { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import axios from "axios";
import { ArrowRight, Clock, CaretLeft } from "@phosphor-icons/react";
import StorefrontLayout, { fetchPublicSite } from "../components/StorefrontLayout";
import SEOHead from "../components/SEOHead";
import { pickLang } from "../lib/i18n";
import { buildHreflangs, designAccents } from "../components/storefront/storefrontUtils";
import { useShopSiteId } from "../lib/shopSiteId";

const BACKEND_URL = "";

/* Same fallback posts as BlogTeaser, full body included */
const FALLBACK_POSTS = [
  {
    slug: "bien-choisir-fauteuil-releveur",
    category: "Guide d'achat",
    title: "Bien choisir son fauteuil releveur : le guide complet",
    excerpt: "Moteur, hauteur d'assise, position médicale… tout ce qu'il faut savoir avant d'acheter.",
    image: "https://images.unsplash.com/photo-1493663284031-b7e3aefcae8e?w=1400&auto=format&fit=crop",
    read_minutes: 6,
    published_at: "2026-03-12",
    author: "L'équipe Sereniva",
    body: `Le fauteuil releveur n'est pas un simple fauteuil. C'est un équipement médical léger qui peut transformer le quotidien d'une personne avec mobilité réduite — à condition de bien le choisir.

## 1. Moteur simple ou double ?

Un **fauteuil à 1 moteur** relève et allonge en un seul mouvement. Simple d'utilisation, plus abordable (599-899 €), il convient pour les besoins légers.

Un **fauteuil à 2 moteurs** permet de dissocier le dossier et le repose-jambes : vous pouvez être allongé tout en restant assis, par exemple. C'est la référence pour un usage quotidien intensif ou médical (à partir de 899 €).

## 2. La hauteur d'assise — critère clé

Mesurez la distance du sol à l'arrière du genou en position assise. C'est la hauteur d'assise cible. Elle varie selon la morphologie : 45 cm pour les personnes de 1m60, 50 cm pour 1m80.

## 3. Tissu ou cuir ?

Le tissu anti-taches (type "Aquaclean") est le meilleur compromis silver-eco : confortable, chaud en hiver, et se nettoie à l'eau.

Le cuir véritable dure plus longtemps mais demande un entretien régulier et peut être froid.

## 4. Livraison & installation

Demandez systématiquement une **installation offerte à domicile**. Un bon vendeur vous envoie un technicien qui monte le fauteuil, teste les moteurs avec vous, et emporte l'ancien fauteuil si besoin.

## En résumé

Pour la majorité des personnes, le combo gagnant est : **2 moteurs, tissu anti-taches, hauteur adaptée, installation incluse, garantie 2 ans**. Budget indicatif : 899 à 1 299 €.

Et surtout : testez avant d'acheter. Un fauteuil releveur doit vous épouser, pas vous contraindre.`
  },
  {
    slug: "maintien-domicile-5-essentiels",
    category: "Maintien à domicile",
    title: "Maintien à domicile : les 5 équipements essentiels",
    excerpt: "Barres d'appui, détecteurs de chute, éclairages automatiques : notre sélection pour vivre sereinement chez soi.",
    image: "https://images.unsplash.com/photo-1579684385127-1ef15d508118?w=1400&auto=format&fit=crop",
    read_minutes: 4,
    published_at: "2026-02-28",
    author: "L'équipe Sereniva",
    body: `Rester chez soi en vieillissant est le souhait de 85% des seniors français. Voici les 5 équipements qui font vraiment la différence au quotidien.

## 1. Barres d'appui salle de bain

60% des chutes domestiques ont lieu dans la salle de bain. Une barre d'appui bien placée (hauteur 90 cm, côté douche) divise ce risque par 3. Budget : 40-80 €.

## 2. Détecteur de chute avec bouton SOS

Portable, étanche, relié à une centrale 24/7. En cas de chute, un opérateur appelle un proche ou les secours. Abonnement mensuel 25-40 €.

## 3. Éclairage automatique de nuit

Détecteurs de mouvement dans les couloirs et la chambre. Plus besoin de chercher l'interrupteur la nuit. Budget : 30-60 € le kit.

## 4. Pilulier électronique connecté

Sonne aux heures de prise, envoie une alerte smartphone au proche aidant si un médicament est oublié. Indispensable à partir de 4 médicaments/jour.

## 5. Téléphone senior simplifié

Grosses touches, volume élevé, 4 numéros favoris en touche directe. Pour rester connecté sans galérer.

---

**Notre conseil** : équipez progressivement, pièce par pièce. Commencez par la salle de bain (sécurité) et la chambre (alarme), puis étendez selon les besoins.`
  },
  {
    slug: "nuits-reparatrices-seniors",
    category: "Sommeil",
    title: "Retrouver des nuits réparatrices après 70 ans",
    excerpt: "Un matelas adapté change tout. On vous explique pourquoi et comment le choisir.",
    image: "https://images.unsplash.com/photo-1540518614846-7eded433c457?w=1400&auto=format&fit=crop",
    read_minutes: 5,
    published_at: "2026-02-10",
    author: "L'équipe Sereniva",
    body: `Le sommeil des seniors est plus fragile : temps d'endormissement plus long, réveils nocturnes, maux de dos au petit matin. La literie joue un rôle majeur — souvent sous-estimé.

## Pourquoi le matelas compte plus après 65 ans

Les tissus musculaires et la peau deviennent plus sensibles à la pression. Un matelas trop ferme crée des points de douleur ; un matelas trop mou ne soutient plus le dos.

## Les 3 bons choix

**Mémoire de forme**. Épouse la morphologie, répartit la pression. Idéal en cas d'arthrose ou douleurs articulaires.

**Matelas médical anti-escarres**. À étages ou dynamique, pour les personnes alitées de longue durée.

**Lit électrique relevable**. Permet de surélever tête/pieds sans effort. Très utile pour la digestion, le reflux, ou la circulation.

## Les indices qui ne trompent pas

- Vous vous réveillez plus fatigué qu'en vous couchant
- Votre matelas a plus de 8 ans
- Vous avez changé de morphologie depuis l'achat
- Vous sentez des "creux" ou affaissements

Si 2 critères sont cochés, il est temps de changer.`
  },
];

function useSiteDesign() {
  const siteId = useShopSiteId();
  const [site, setSite] = useState(null);
  const [design, setDesign] = useState(null);
  const [collectionPosts, setCollectionPosts] = useState(null);   // Phase 3.3 — collection db.blog_posts
  const storageKey = `cf_lang_${siteId}`;
  const [lang, setLangState] = useState(() => localStorage.getItem(storageKey) || "fr");
  const setLang = (l) => { localStorage.setItem(storageKey, l); setLangState(l); };
  useEffect(() => {
    fetchPublicSite(siteId).then(setSite).catch(() => setSite({ error: true }));
    axios.get(`${BACKEND_URL}/api/public/sites/${siteId}/design`)
      .then(({ data }) => setDesign(data?.published ? data.design : null))
      .catch(() => setDesign(null));
  }, [siteId]);
  // Phase 3.3 — charge les articles de la collection blog_posts (source of truth)
  useEffect(() => {
    if (!siteId || !lang) return;
    axios.get(`${BACKEND_URL}/api/public/sites/${siteId}/blog-posts?lang=${lang}&limit=60`)
      .then(({ data }) => setCollectionPosts(Array.isArray(data) ? data : []))
      .catch(() => setCollectionPosts([]));
  }, [siteId, lang]);
  // Bloc 2 — fix bug `availableLangs is not defined` qui plantait /blog
  const availableLangs = (site?.selected_languages && site.selected_languages.length)
    ? site.selected_languages
    : ["fr"];
  return { siteId, site, design: design || {}, lang, setLang, availableLangs, collectionPosts };
}

function getPosts(design, collectionPosts) {
  // Phase 3.3 — priorité à la collection db.blog_posts (Magic Content 3.3)
  if (Array.isArray(collectionPosts) && collectionPosts.length > 0) {
    return collectionPosts.map((p) => ({
      slug: p.slug,
      title: (p.title && (p.title[p.lang] || p.title.fr || Object.values(p.title)[0])) || "",
      excerpt: (p.excerpt && (p.excerpt[p.lang] || p.excerpt.fr || Object.values(p.excerpt)[0])) || "",
      category: p.category || "Journal",
      date: p.published_at || p.created_at,
      read_minutes: p.read_minutes || 6,
      hero_image_url: p.hero_image_url,
      inline_image_url: p.inline_image_url,
      role: p.role,
      tags: p.tags || [],
      body_md: "",  // chargé à la demande dans BlogPost
      _source: "collection",
    }));
  }
  const custom = design?.blog_posts;
  return (Array.isArray(custom) && custom.length > 0) ? custom : FALLBACK_POSTS;
}

function mdLite(md) {
  if (!md) return "";
  return md.split("\n\n").map((block) => {
    const b = block.trim();
    if (b.startsWith("## ")) return `<h2 class="text-2xl md:text-3xl font-semibold mt-10 mb-4 text-neutral-900">${b.slice(3)}</h2>`;
    if (b.startsWith("### ")) return `<h3 class="text-xl font-semibold mt-6 mb-3 text-neutral-900">${b.slice(4)}</h3>`;
    if (b === "---") return `<hr class="my-8 border-neutral-200" />`;
    if (b.startsWith("- ")) {
      const items = b.split("\n").map((l) => `<li>${l.replace(/^- /, "")}</li>`).join("");
      return `<ul class="list-disc pl-6 space-y-1.5 my-4 text-neutral-700">${items}</ul>`;
    }
    // Bold **text**
    const inline = b.replace(/\*\*(.+?)\*\*/g, '<strong class="text-neutral-900">$1</strong>');
    return `<p class="leading-[1.75] my-4 text-[17px] text-neutral-700">${inline.replace(/\n/g, "<br/>")}</p>`;
  }).join("");
}

/* =========================================================
 * BLOG INDEX — /shop/:siteId/blog
 * ========================================================= */
export function StorefrontBlog() {
  const { siteId, site, design, lang, setLang, availableLangs, collectionPosts } = useSiteDesign();
  const posts = getPosts(design, collectionPosts);
  const { primary, fontHeading } = designAccents(design);
  const canonical = typeof window !== "undefined" ? `${window.location.origin}/shop/${siteId}/blog` : undefined;

  return (
    <StorefrontLayout lang={lang} setLang={setLang} availableLangs={availableLangs} site={site} design={design}>
      <SEOHead
        title={`Journal · ${site?.name || ""}`}
        description={`Guides, conseils et actualités autour ${site?.niche || "des produits senior"}.`}
        canonical={canonical}
        siteName={site?.name}
        langs={buildHreflangs(site, "/blog")}
        schema={{
          "@context": "https://schema.org",
          "@type": "Blog",
          name: `Journal · ${site?.name || ""}`,
          url: canonical,
          blogPost: posts.slice(0, 20).map((p) => ({
            "@type": "BlogPosting",
            headline: pickLang(p.title, lang) || p.title,
            url: `${canonical}/${p.slug}`,
            datePublished: p.published_at,
            image: p.image,
          })),
        }}
      />

      {/* Lot G Fix 13 — header transparent (hérite body), aligné sur PageHero des
          autres pages secondaires. Pas de fond ivoire / accent_color. */}
      <section className="border-b border-stone-200/60">
        <div className="max-w-6xl mx-auto px-6 md:px-10 py-14 md:py-20">
          <div className="text-[11px] uppercase tracking-[0.2em] mb-3 font-medium" style={{ color: primary }}>Le Journal</div>
          <h1 className="text-4xl md:text-5xl lg:text-6xl leading-[1.05] tracking-tight text-neutral-900" style={{ fontFamily: `"${fontHeading}", serif` }}>
            Guides, conseils et inspirations
          </h1>
          <p className="text-[17px] text-neutral-600 mt-5 leading-relaxed max-w-2xl">
            Chaque article est rédigé par notre équipe en collaboration avec des ergothérapeutes et des aidants. Pas de jargon, pas de baratin.
          </p>
        </div>
      </section>

      <section className="max-w-6xl mx-auto px-6 md:px-10 py-16 md:py-20" data-testid="blog-index">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 md:gap-8">
          {posts.map((p, i) => (
            <Link
              key={p.slug || i}
              to={`/shop/${siteId}/blog/${p.slug}`}
              data-testid={`blog-card-${p.slug}`}
              className="group block bg-white rounded-3xl overflow-hidden border border-neutral-100 hover:shadow-lg transition-shadow duration-500"
            >
              <div className="aspect-[5/3] bg-neutral-100 overflow-hidden">
                {p.image && (
                  <img src={p.image} alt={pickLang(p.title, lang) || p.title} loading="lazy" className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-105" />
                )}
              </div>
              <div className="p-6 md:p-7">
                <div className="flex items-center gap-3 text-[11px] uppercase tracking-widest mb-3" style={{ color: primary }}>
                  <span>{pickLang(p.category, lang) || p.category}</span>
                  {p.read_minutes && (
                    <span className="flex items-center gap-1 text-neutral-500">
                      <Clock size={12} weight="bold" /> {p.read_minutes} min
                    </span>
                  )}
                </div>
                <h2 className="text-xl md:text-[22px] leading-snug mb-3 text-neutral-900 group-hover:opacity-80 transition" style={{ fontFamily: `"${fontHeading}", serif` }}>
                  {pickLang(p.title, lang) || p.title}
                </h2>
                <p className="text-[14px] text-neutral-600 leading-relaxed line-clamp-2">
                  {pickLang(p.excerpt, lang) || p.excerpt}
                </p>
                <div className="mt-5 inline-flex items-center gap-1.5 text-sm font-medium group-hover:gap-2.5 transition-all" style={{ color: primary }}>
                  Lire l'article <ArrowRight size={14} weight="bold" />
                </div>
              </div>
            </Link>
          ))}
        </div>
      </section>
    </StorefrontLayout>
  );
}

/* =========================================================
 * BLOG POST — /shop/:siteId/blog/:slug
 * ========================================================= */
export function StorefrontBlogPost() {
  const siteId = useShopSiteId(); const { slug } = useParams();
  const { site, design, lang, setLang, availableLangs, collectionPosts } = useSiteDesign();
  const posts = getPosts(design, collectionPosts);
  const post = posts.find((p) => p.slug === slug);
  const { primary, fontHeading } = designAccents(design);

  if (!post) {
    return (
      <StorefrontLayout lang={lang} setLang={setLang} availableLangs={availableLangs} site={site} design={design}>
        <div className="max-w-2xl mx-auto px-6 py-32 text-center">
          <h1 className="text-3xl font-semibold mb-3" style={{ fontFamily: `"${fontHeading}", serif` }}>Article introuvable</h1>
          <Link to={`/shop/${siteId}/blog`} className="text-sm hover:underline" style={{ color: primary }}>← Retour au journal</Link>
        </div>
      </StorefrontLayout>
    );
  }

  const title = pickLang(post.title, lang) || post.title;
  // Phase 3.3 — la collection stocke body_html (pré-rendu côté pipeline) sous
  // forme de dict {lang: html}. Fallback sur body_md rendu via mdLite.
  const bodyHtmlCollection = (post.body_html && (post.body_html[lang] || post.body_html.fr)) || "";
  const bodyMdCollection = (post.body_md && (post.body_md[lang] || post.body_md.fr)) || "";
  const body = bodyMdCollection || pickLang(post.body, lang) || post.body || "";
  const category = pickLang(post.category, lang) || post.category;
  const canonical = typeof window !== "undefined" ? `${window.location.origin}/shop/${siteId}/blog/${slug}` : undefined;
  const html = bodyHtmlCollection || mdLite(body);

  const wordCount = body.split(/\s+/).filter(Boolean).length;
  const articleSchema = {
    "@context": "https://schema.org",
    "@type": "BlogPosting",
    headline: title,
    alternativeHeadline: pickLang(post.excerpt, lang) || undefined,
    description: pickLang(post.excerpt, lang) || title,
    image: post.image,
    datePublished: post.published_at,
    dateModified: post.updated_at || post.published_at,
    wordCount,
    timeRequired: post.read_minutes ? `PT${post.read_minutes}M` : undefined,
    inLanguage: lang === "fr" ? "fr-FR" : lang,
    author: {
      "@type": "Organization",
      name: post.author || site?.name,
      url: `${window.location.origin}/shop/${siteId}/about`,
    },
    publisher: {
      "@type": "Organization",
      name: site?.name,
      logo: design?.brand?.logo_url
        ? { "@type": "ImageObject", url: design.brand.logo_url }
        : undefined,
    },
    mainEntityOfPage: canonical,
    articleSection: category,
    keywords: [post.pillar_keyword, post.satellite_keyword, ...(post.satellite_keywords || [])]
      .filter(Boolean).join(", ") || undefined,
    about: post.pillar_keyword || post.satellite_keyword || category,
    speakable: {
      "@type": "SpeakableSpecification",
      cssSelector: ["h1", "h2", "[data-speakable='true']"],
    },
  };
  const breadcrumb = {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: [
      { "@type": "ListItem", position: 1, name: "Accueil", item: `${window.location.origin}/shop/${siteId}` },
      { "@type": "ListItem", position: 2, name: "Journal", item: `${window.location.origin}/shop/${siteId}/blog` },
      { "@type": "ListItem", position: 3, name: title, item: canonical },
    ],
  };
  // Phase 3.3 fix hreflang — priorité au `hreflang` dict stocké en DB (6
  // slugs différents par langue, URLs absolues pré-calculées par le pipeline).
  // Fallback `buildHreflangs` si pas de hreflang DB (ancien format).
  const hreflangEntries = (post.hreflang && typeof post.hreflang === "object")
    ? Object.entries(post.hreflang)
        .filter(([code, href]) => code && href)
        .map(([code, href]) => ({ code: code === "fr" ? "fr-FR" : code, href }))
    : buildHreflangs(site, `/blog/${slug}`);

  return (
    <StorefrontLayout lang={lang} setLang={setLang} availableLangs={availableLangs} site={site} design={design}>
      <SEOHead
        title={`${title} · ${site?.name || ""}`}
        description={pickLang(post.excerpt, lang) || post.excerpt || title}
        canonical={canonical}
        image={post.image}
        type="article"
        siteName={site?.name}
        langs={hreflangEntries}
        schema={[articleSchema, breadcrumb]}
      />

      <article className="pb-20" data-testid="blog-post">
        {/* Lot G Fix 13 — hero article transparent (hérite body), aligné PageHero */}
        <div className="border-b border-stone-200/60">
          <div className="max-w-3xl mx-auto px-6 md:px-10 py-12 md:py-16">
            <Link to={`/shop/${siteId}/blog`} className="inline-flex items-center gap-1.5 text-[13px] text-neutral-600 hover:text-neutral-900 mb-6">
              <CaretLeft size={14} weight="bold" /> Retour au journal
            </Link>
            <div className="flex items-center gap-3 text-[11px] uppercase tracking-widest mb-4" style={{ color: primary }}>
              <span>{category}</span>
              {post.read_minutes && (
                <span className="flex items-center gap-1 text-neutral-500">
                  <Clock size={12} weight="bold" /> {post.read_minutes} min de lecture
                </span>
              )}
            </div>
            <h1 className="text-3xl md:text-5xl leading-[1.08] text-neutral-900" style={{ fontFamily: `"${fontHeading}", serif` }}>
              {title}
            </h1>
            {post.excerpt && (
              <p className="text-lg md:text-xl text-neutral-600 mt-5 leading-relaxed">
                {pickLang(post.excerpt, lang) || post.excerpt}
              </p>
            )}
            <div className="mt-8 text-sm text-neutral-500 flex items-center gap-3">
              <span>Par {post.author || site?.name}</span>
              {post.published_at && (
                <>
                  <span>·</span>
                  <time>{new Date(post.published_at).toLocaleDateString("fr-FR", { day: "numeric", month: "long", year: "numeric" })}</time>
                </>
              )}
            </div>
          </div>
        </div>

        {post.image && (
          <div className="max-w-4xl mx-auto px-6 md:px-10 -mt-8 md:-mt-12">
            <div className="aspect-[16/9] rounded-3xl overflow-hidden shadow-xl">
              <img src={post.image} alt={title} loading="lazy" decoding="async" className="w-full h-full object-cover" />
            </div>
          </div>
        )}

        <div className="max-w-3xl mx-auto px-6 md:px-10 mt-10 md:mt-14 prose-custom" data-testid="blog-post-body">
          <div dangerouslySetInnerHTML={{ __html: html }} />
        </div>

        {/* Related posts */}
        <div className="max-w-6xl mx-auto px-6 md:px-10 mt-20 pt-16 border-t" style={{ borderColor: "#E7E5E4" }}>
          <div className="text-[11px] uppercase tracking-[0.2em] text-neutral-500 mb-3">Continuer la lecture</div>
          <h2 className="text-2xl md:text-3xl mb-8" style={{ fontFamily: `"${fontHeading}", serif` }}>
            D'autres articles
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {posts.filter((p) => p.slug !== slug).slice(0, 3).map((rel, i) => (
              <Link key={i} to={`/shop/${siteId}/blog/${rel.slug}`} className="group block">
                <div className="aspect-[5/3] bg-neutral-100 rounded-2xl overflow-hidden mb-3">
                  {rel.image && <img src={rel.image} alt={pickLang(rel.title, lang) || rel.title} loading="lazy" className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-700" />}
                </div>
                <div className="text-[11px] uppercase tracking-widest mb-2" style={{ color: primary }}>
                  {pickLang(rel.category, lang) || rel.category}
                </div>
                <h3 className="text-lg leading-snug group-hover:opacity-70 transition" style={{ fontFamily: `"${fontHeading}", serif` }}>
                  {pickLang(rel.title, lang) || rel.title}
                </h3>
              </Link>
            ))}
          </div>
        </div>
      </article>
    </StorefrontLayout>
  );
}
