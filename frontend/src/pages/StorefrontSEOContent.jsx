// Sprint 2 — Pages storefront consommant les endpoints publics SEO :
// - BuyerGuidesList / BuyerGuideDetail
// - GlossaryList / GlossaryTerm
// - ComparisonsList / ComparisonDetail
// - TopListsList / TopListDetail
// - TeamList / TeamMember
// - AboutRich (enrichi via /about-rich)
//
// Rendering minimal mais premium, re-use StorefrontLayout + SEOHead.
import React, { useEffect, useState, useMemo } from "react";
import { Link, useParams } from "react-router-dom";
import axios from "axios";
import StorefrontLayout from "../components/StorefrontLayout";
import SEOHead from "../components/SEOHead";
import { useShopSiteId } from "../lib/shopSiteId";

const API = process.env.REACT_APP_BACKEND_URL || "";

function useFetch(url) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    let cancel = false;
    setLoading(true);
    axios.get(url)
      .then((r) => { if (!cancel) setData(r.data); })
      .catch((e) => { if (!cancel) setError(e); })
      .finally(() => { if (!cancel) setLoading(false); });
    return () => { cancel = true; };
  }, [url]);
  return { data, error, loading };
}

function Shell({ title, description, children }) {
  return (
    <StorefrontLayout>
      <SEOHead title={title} description={description} />
      <div className="max-w-4xl mx-auto px-4 py-12">
        {children}
      </div>
    </StorefrontLayout>
  );
}

// ── Buyer Guides ──
export function StorefrontBuyerGuides() {
  const { siteId } = useShopSiteId();
  const { data, loading } = useFetch(`${API}/api/public/sites/${siteId}/buyer-guides`);
  const items = (data && data.items) || [];
  return (
    <Shell title="Guides d'achat" description="Guides d'achat éditoriaux pour bien choisir votre produit.">
      <h1 className="text-3xl font-serif mb-6">Guides d'achat</h1>
      {loading && <p className="text-neutral-500">Chargement…</p>}
      <ul className="space-y-4">
        {items.map((g) => (
          <li key={g.id} className="border-b pb-4">
            <Link to={`/buyer-guides/${g.slug}`} className="text-lg font-medium hover:underline">
              {g.title || g.h1 || g.slug}
            </Link>
            {g.meta_description && <p className="text-sm text-neutral-600 mt-1">{g.meta_description}</p>}
          </li>
        ))}
        {!loading && items.length === 0 && <li className="text-neutral-500">Aucun guide disponible pour le moment.</li>}
      </ul>
    </Shell>
  );
}

export function StorefrontBuyerGuide() {
  const { siteId } = useShopSiteId();
  const { slug } = useParams();
  const { data: g, loading, error } = useFetch(`${API}/api/public/sites/${siteId}/buyer-guides/${slug}`);
  const jsonLd = useMemo(() => (g ? {
    "@context": "https://schema.org",
    "@type": "Article",
    headline: g.h1 || g.title,
    description: g.meta_description,
    author: { "@type": "Organization", name: "Équipe éditoriale" },
    datePublished: g.created_at,
    dateModified: g.updated_at,
  } : null), [g]);
  if (loading) return <Shell title="">Chargement…</Shell>;
  if (error || !g) return <Shell title="Guide introuvable">Guide introuvable.</Shell>;
  return (
    <Shell title={g.title || g.h1} description={g.meta_description}>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />
      <h1 className="text-4xl font-serif mb-4">{g.h1 || g.title}</h1>
      {g.intro && <p className="lead text-lg text-neutral-700 mb-8">{g.intro}</p>}
      <article className="prose prose-neutral max-w-none">
        {(g.sections || []).map((s, i) => (
          <section key={i} className="mb-8">
            <h2 className="text-2xl font-serif mt-8 mb-3">{s.h2}</h2>
            <div style={{ whiteSpace: "pre-wrap" }}>{s.body_md}</div>
          </section>
        ))}
        {g.comparison_table && (g.comparison_table.headers || []).length > 0 && (
          <div className="my-8 overflow-x-auto">
            <table className="min-w-full border">
              <thead>
                <tr>{(g.comparison_table.headers || []).map((h, i) => <th key={i} className="border px-3 py-2 bg-neutral-50">{h}</th>)}</tr>
              </thead>
              <tbody>
                {(g.comparison_table.rows || []).map((r, i) => (
                  <tr key={i}>{(r || []).map((c, j) => <td key={j} className="border px-3 py-2">{c}</td>)}</tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {(g.faq || []).length > 0 && (
          <section className="mt-10">
            <h2 className="text-2xl font-serif mb-4">FAQ</h2>
            {(g.faq || []).map((f, i) => (
              <details key={i} className="mb-3 border-b pb-3"><summary className="cursor-pointer font-medium">{f.q}</summary><p className="mt-2 text-neutral-700">{f.a}</p></details>
            ))}
          </section>
        )}
        {(g.internal_links || []).length > 0 && (
          <section className="mt-10 border-t pt-6">
            <h3 className="text-lg font-medium mb-3">À lire aussi</h3>
            <ul className="list-disc pl-5 space-y-1">
              {(g.internal_links || []).slice(0, 10).map((l, i) => (
                <li key={i}><Link to={`/products/${l.target_slug}`} className="underline">{l.anchor}</Link></li>
              ))}
            </ul>
          </section>
        )}
      </article>
    </Shell>
  );
}

// ── Glossary ──
export function StorefrontGlossary() {
  const { siteId } = useShopSiteId();
  const { data, loading } = useFetch(`${API}/api/public/sites/${siteId}/glossary`);
  const items = (data && data.items) || [];
  const byLetter = useMemo(() => {
    const m = {};
    items.forEach((t) => { const l = (t.term || "?")[0].toUpperCase(); (m[l] = m[l] || []).push(t); });
    return m;
  }, [items]);
  return (
    <Shell title="Glossaire" description="Définitions claires des termes techniques utilisés dans nos produits.">
      <h1 className="text-3xl font-serif mb-6">Glossaire</h1>
      {loading && <p>Chargement…</p>}
      {Object.keys(byLetter).sort().map((l) => (
        <section key={l} className="mb-6">
          <h2 className="text-xl font-semibold mb-2">{l}</h2>
          <ul className="space-y-1">
            {byLetter[l].map((t) => (
              <li key={t.id}><Link to={`/glossary/${t.slug}`} className="underline">{t.term}</Link></li>
            ))}
          </ul>
        </section>
      ))}
      {!loading && items.length === 0 && <p className="text-neutral-500">Glossaire en cours de constitution.</p>}
    </Shell>
  );
}

export function StorefrontGlossaryTerm() {
  const { siteId } = useShopSiteId();
  const { slug } = useParams();
  const { data: t, loading, error } = useFetch(`${API}/api/public/sites/${siteId}/glossary/${slug}`);
  if (loading) return <Shell title="">Chargement…</Shell>;
  if (error || !t) return <Shell title="Terme introuvable">Terme introuvable.</Shell>;
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "DefinedTerm",
    name: t.term,
    description: t.definition,
  };
  return (
    <Shell title={t.term} description={(t.definition || "").slice(0, 150)}>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />
      <h1 className="text-3xl font-serif mb-4">{t.term}</h1>
      <p className="text-neutral-700 text-lg">{t.definition}</p>
      {(t.related || []).length > 0 && (
        <section className="mt-8">
          <h3 className="text-lg font-medium mb-2">Termes liés</h3>
          <ul className="list-disc pl-5">
            {t.related.map((r) => (
              <li key={r.slug}><Link to={`/glossary/${r.slug}`} className="underline">{r.term}</Link></li>
            ))}
          </ul>
        </section>
      )}
      <div className="mt-8">
        <Link to="/glossary" className="text-sm text-neutral-500 underline">← Retour au glossaire</Link>
      </div>
    </Shell>
  );
}

// ── Comparisons ──
export function StorefrontComparisons() {
  const { siteId } = useShopSiteId();
  const { data, loading } = useFetch(`${API}/api/public/sites/${siteId}/comparisons`);
  const items = (data && data.items) || [];
  return (
    <Shell title="Comparaisons" description="Comparez nos produits côte à côte pour choisir le plus adapté.">
      <h1 className="text-3xl font-serif mb-6">Comparaisons</h1>
      {loading && <p>Chargement…</p>}
      <ul className="space-y-4">
        {items.map((c) => (
          <li key={c.id} className="border-b pb-4">
            <Link to={`/compare/${c.slug}`} className="text-lg font-medium hover:underline">{c.title || c.h1 || c.slug}</Link>
            {c.meta_description && <p className="text-sm text-neutral-600 mt-1">{c.meta_description}</p>}
          </li>
        ))}
        {!loading && items.length === 0 && <li className="text-neutral-500">Aucune comparaison disponible.</li>}
      </ul>
    </Shell>
  );
}

export function StorefrontCompare() {
  const { siteId } = useShopSiteId();
  const { slug } = useParams();
  const { data: c, loading, error } = useFetch(`${API}/api/public/sites/${siteId}/compare/${slug}`);
  if (loading) return <Shell title="">Chargement…</Shell>;
  if (error || !c) return <Shell title="Comparaison introuvable">Comparaison introuvable.</Shell>;
  return (
    <Shell title={c.title || c.h1} description={c.meta_description}>
      <h1 className="text-4xl font-serif mb-4">{c.h1 || c.title}</h1>
      {c.intro && <p className="lead text-lg text-neutral-700 mb-8">{c.intro}</p>}
      {c.comparison_table && (c.comparison_table.headers || []).length > 0 && (
        <div className="my-8 overflow-x-auto">
          <table className="min-w-full border">
            <thead><tr>{(c.comparison_table.headers || []).map((h, i) => <th key={i} className="border px-3 py-2 bg-neutral-50">{h}</th>)}</tr></thead>
            <tbody>{(c.comparison_table.rows || []).map((r, i) => <tr key={i}>{(r || []).map((v, j) => <td key={j} className="border px-3 py-2">{v}</td>)}</tr>)}</tbody>
          </table>
        </div>
      )}
      {c.section_a_strengths && (<><h2 className="text-2xl font-serif mt-6 mb-3">Forces de {c.product_a_slug}</h2><p>{c.section_a_strengths}</p></>)}
      {c.section_b_strengths && (<><h2 className="text-2xl font-serif mt-6 mb-3">Forces de {c.product_b_slug}</h2><p>{c.section_b_strengths}</p></>)}
      {c.verdict && (<><h2 className="text-2xl font-serif mt-6 mb-3">Verdict</h2><p>{c.verdict}</p></>)}
      {(c.faq || []).length > 0 && (
        <section className="mt-10"><h2 className="text-2xl font-serif mb-4">FAQ</h2>{(c.faq || []).map((f, i) => (
          <details key={i} className="mb-3 border-b pb-3"><summary className="cursor-pointer font-medium">{f.q}</summary><p className="mt-2 text-neutral-700">{f.a}</p></details>
        ))}</section>
      )}
    </Shell>
  );
}

// ── Top lists ──
export function StorefrontTopLists() {
  const { siteId } = useShopSiteId();
  const { data, loading } = useFetch(`${API}/api/public/sites/${siteId}/top-lists`);
  const items = (data && data.items) || [];
  return (
    <Shell title="Meilleurs produits" description="Nos sélections des meilleurs produits du catalogue.">
      <h1 className="text-3xl font-serif mb-6">Nos sélections</h1>
      {loading && <p>Chargement…</p>}
      <ul className="space-y-4">
        {items.map((t) => (
          <li key={t.id} className="border-b pb-4">
            <Link to={`/top/${t.slug}`} className="text-lg font-medium hover:underline">{t.title || t.h1 || t.slug}</Link>
            {t.meta_description && <p className="text-sm text-neutral-600 mt-1">{t.meta_description}</p>}
          </li>
        ))}
        {!loading && items.length === 0 && <li className="text-neutral-500">Aucune sélection pour le moment.</li>}
      </ul>
    </Shell>
  );
}

export function StorefrontTopList() {
  const { siteId } = useShopSiteId();
  const { slug } = useParams();
  const { data: t, loading, error } = useFetch(`${API}/api/public/sites/${siteId}/top-lists/${slug}`);
  if (loading) return <Shell title="">Chargement…</Shell>;
  if (error || !t) return <Shell title="Sélection introuvable">Sélection introuvable.</Shell>;
  return (
    <Shell title={t.title || t.h1} description={t.meta_description}>
      <h1 className="text-4xl font-serif mb-4">{t.h1 || t.title}</h1>
      {t.intro && <p className="lead text-lg text-neutral-700 mb-8">{t.intro}</p>}
      <ol className="space-y-6">
        {(t.items || []).map((it, i) => (
          <li key={i} className="border-l-4 pl-4 border-neutral-200">
            <div className="text-sm text-neutral-500">#{it.rank || i + 1}</div>
            <h3 className="text-xl font-medium mb-2">{it.headline}</h3>
            {it.product_slug && <Link to={`/products/${it.product_slug}`} className="text-sm underline">Voir le produit</Link>}
            <p className="mt-2">{it.why}</p>
            {(it.pros || []).length > 0 && <p className="mt-2 text-green-700">✓ {(it.pros || []).join(" • ")}</p>}
            {(it.cons || []).length > 0 && <p className="mt-1 text-amber-700">⚠︎ {(it.cons || []).join(" • ")}</p>}
            {it.verdict && <p className="mt-2 italic text-neutral-700">{it.verdict}</p>}
          </li>
        ))}
      </ol>
      {t.conclusion && <p className="mt-10">{t.conclusion}</p>}
      {(t.faq || []).length > 0 && (
        <section className="mt-10"><h2 className="text-2xl font-serif mb-4">FAQ</h2>{(t.faq || []).map((f, i) => (
          <details key={i} className="mb-3 border-b pb-3"><summary className="cursor-pointer font-medium">{f.q}</summary><p className="mt-2 text-neutral-700">{f.a}</p></details>
        ))}</section>
      )}
    </Shell>
  );
}

// ── Team ──
export function StorefrontTeam() {
  const { siteId } = useShopSiteId();
  const { data, loading } = useFetch(`${API}/api/public/sites/${siteId}/team`);
  const items = (data && data.items) || [];
  return (
    <Shell title="Notre équipe" description="Les experts derrière nos produits.">
      <h1 className="text-3xl font-serif mb-6">Notre équipe</h1>
      {loading && <p>Chargement…</p>}
      <div className="grid md:grid-cols-3 gap-6">
        {items.map((a) => (
          <Link key={a.slug} to={`/team/${a.slug}`} className="block border rounded-lg p-5 hover:shadow">
            {a.photo_url && <img src={a.photo_url} alt={a.name} className="w-24 h-24 rounded-full object-cover mb-3" loading="lazy" />}
            <div className="font-medium">{a.name}</div>
            <div className="text-sm text-neutral-600">{a.role}</div>
            <div className="text-xs text-neutral-500 mt-1">{a.specialty}</div>
          </Link>
        ))}
      </div>
    </Shell>
  );
}

export function StorefrontTeamMember() {
  const { siteId } = useShopSiteId();
  const { slug } = useParams();
  const { data: a, loading, error } = useFetch(`${API}/api/public/sites/${siteId}/team/${slug}`);
  if (loading) return <Shell title="">Chargement…</Shell>;
  if (error || !a) return <Shell title="Membre introuvable">Membre introuvable.</Shell>;
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "Person",
    name: a.name,
    jobTitle: a.role,
    knowsAbout: a.specialty,
    image: a.photo_url,
    sameAs: a.sameAs || [],
  };
  return (
    <Shell title={`${a.name} — ${a.role}`} description={(a.bio || "").slice(0, 150)}>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />
      {a.photo_url && <img src={a.photo_url} alt={a.name} className="w-40 h-40 rounded-full object-cover mb-6" loading="lazy" />}
      <h1 className="text-3xl font-serif mb-1">{a.name}</h1>
      <p className="text-neutral-600 mb-4">{a.role} — {a.specialty}</p>
      <p className="text-neutral-800 whitespace-pre-wrap">{a.bio}</p>
    </Shell>
  );
}

export default StorefrontBuyerGuides;
