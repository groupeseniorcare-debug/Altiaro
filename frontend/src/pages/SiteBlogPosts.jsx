import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  Plus, PencilSimple, Trash, Sparkle, ArrowLeft, X, Eye,
  FloppyDisk, Warning, CheckCircle, Clock,
} from "@phosphor-icons/react";
import { api, apiCall } from "../lib/api";

export default function SiteBlogPosts() {
  const { id: siteId } = useParams();
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(null);
  const [toast, setToast] = useState(null);
  const [aiOpen, setAiOpen] = useState(false);
  const [aiForm, setAiForm] = useState({ keyword: "", angle: "", length: "long" });
  const [aiLoading, setAiLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    const { data } = await apiCall(() => api.get(`/sites/${siteId}/blog-posts`));
    setPosts(data || []);
    setLoading(false);
  };

  useEffect(() => { load(); }, [siteId]);

  const showToast = (type, msg) => {
    setToast({ type, msg });
    setTimeout(() => setToast(null), 5000);
  };

  const save = async () => {
    if (!editing?.title) return;
    const payload = { ...editing };
    if (editing._isNew) {
      const { data, error } = await apiCall(() => api.post(`/sites/${siteId}/blog-posts`, payload));
      if (error) return showToast("error", error);
      showToast("ok", "Article créé");
    } else {
      const { data, error } = await apiCall(() => api.patch(`/sites/${siteId}/blog-posts/${editing.slug}`, payload));
      if (error) return showToast("error", error);
      showToast("ok", "Article mis à jour");
    }
    setEditing(null);
    load();
  };

  const remove = async (post) => {
    if (!window.confirm(`Supprimer définitivement « ${post.title} » ?`)) return;
    const { error } = await apiCall(() => api.delete(`/sites/${siteId}/blog-posts/${post.slug}`));
    if (error) return showToast("error", error);
    showToast("ok", "Article supprimé");
    load();
  };

  const aiGenerate = async () => {
    if (!aiForm.keyword) return;
    setAiLoading(true);
    const { data, error } = await apiCall(() => api.post(`/sites/${siteId}/blog-posts/ai-draft`, aiForm));
    setAiLoading(false);
    if (error) return showToast("error", error);
    showToast("ok", `Article "${data.title}" généré par l'IA`);
    setAiOpen(false);
    setAiForm({ keyword: "", angle: "", length: "long" });
    load();
  };

  return (
    <div className="min-h-screen bg-[#FAF7F2]">
      <div className="max-w-6xl mx-auto px-6 md:px-10 py-8">
        <Link to={`/sites/${siteId}`} className="inline-flex items-center gap-2 text-sm text-neutral-600 hover:text-neutral-900 mb-6" data-testid="back-to-site">
          <ArrowLeft size={14} /> Retour au cockpit
        </Link>

        <div className="flex items-end justify-between gap-4 mb-8 flex-wrap">
          <div>
            <div className="text-[11px] uppercase tracking-[0.2em] text-neutral-500 mb-2">Contenu éditorial</div>
            <h1 className="text-3xl md:text-4xl font-semibold text-neutral-900" style={{ fontFamily: "'Fraunces', serif" }}>
              Le Journal
            </h1>
            <p className="text-sm text-neutral-500 mt-2">
              Les articles alimentent la page `/blog` de votre boutique et participent au SEO.
            </p>
          </div>
          <div className="flex gap-2">
            <a href={`/shop/${siteId}/blog`} target="_blank" rel="noreferrer"
               className="h-11 px-4 rounded-xl bg-white border border-neutral-200 hover:border-[#B84B31] text-neutral-900 text-sm font-medium flex items-center gap-2 transition" data-testid="preview-blog">
              <Eye size={16} /> Voir le blog
            </a>
            <button onClick={() => setAiOpen(true)} data-testid="ai-draft-btn"
                    className="h-11 px-4 rounded-xl bg-white border border-neutral-200 hover:border-[#B84B31] text-neutral-900 text-sm font-medium flex items-center gap-2 transition">
              <Sparkle size={16} weight="duotone" /> Rédiger avec l'IA
            </button>
            <button onClick={() => setEditing({ _isNew: true, title: "", category: "Guide d'achat", read_minutes: 4, body: "" })} data-testid="new-post-btn"
                    className="h-11 px-4 rounded-xl bg-neutral-900 hover:bg-neutral-800 text-white text-sm font-medium flex items-center gap-2 transition">
              <Plus size={16} weight="bold" /> Nouvel article
            </button>
          </div>
        </div>

        {toast && (
          <div data-testid="blog-toast"
               className={`mb-5 px-4 py-3 rounded-xl text-sm font-medium flex items-center gap-2 ${
                 toast.type === "ok" ? "bg-emerald-50 text-emerald-900 border border-emerald-200" : "bg-rose-50 text-rose-900 border border-rose-200"
               }`}>
            {toast.type === "ok" ? <CheckCircle size={16} weight="fill" /> : <Warning size={16} weight="fill" />}
            {toast.msg}
          </div>
        )}

        {loading ? (
          <div className="text-center py-16 text-neutral-500">Chargement…</div>
        ) : posts.length === 0 ? (
          <div className="bg-white rounded-2xl border border-dashed border-neutral-200 p-12 text-center">
            <Sparkle size={40} weight="duotone" className="mx-auto mb-3 text-neutral-300" />
            <div className="font-semibold text-neutral-900 mb-2">Aucun article publié</div>
            <div className="text-sm text-neutral-500 mb-5">Démarrez votre SEO avec un premier guide. L'IA peut rédiger un article complet en 30 secondes.</div>
            <button onClick={() => setAiOpen(true)} className="inline-flex items-center gap-2 h-11 px-5 rounded-xl bg-neutral-900 text-white text-sm font-medium">
              <Sparkle size={16} weight="duotone" /> Commencer avec l'IA
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4" data-testid="blog-posts-list">
            {posts.map((p) => (
              <div key={p.slug} className="bg-white rounded-2xl border border-neutral-200 p-5" data-testid={`post-card-${p.slug}`}>
                <div className="flex items-start justify-between gap-3 mb-2">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 text-[11px] uppercase tracking-widest text-neutral-500 mb-2">
                      <span>{p.category}</span>
                      {p.read_minutes && <><span>·</span><Clock size={11} weight="bold" /> {p.read_minutes} min</>}
                      {p.ai_generated && <><span>·</span><Sparkle size={11} weight="fill" className="text-violet-600" /> IA</>}
                    </div>
                    <h3 className="font-semibold text-neutral-900 leading-tight mb-1">{p.title}</h3>
                    <p className="text-xs text-neutral-500 line-clamp-2">{p.excerpt}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2 mt-4 pt-3 border-t border-neutral-100">
                  <a href={`/shop/${siteId}/blog/${p.slug}`} target="_blank" rel="noreferrer"
                     className="flex-1 h-9 rounded-lg bg-white border border-neutral-200 hover:border-[#B84B31] text-[13px] text-neutral-700 flex items-center justify-center gap-1.5">
                    <Eye size={13} /> Voir
                  </a>
                  <button onClick={() => setEditing({ ...p })} data-testid={`edit-${p.slug}`}
                          className="flex-1 h-9 rounded-lg bg-white border border-neutral-200 hover:border-[#B84B31] text-[13px] text-neutral-900 flex items-center justify-center gap-1.5">
                    <PencilSimple size={13} /> Éditer
                  </button>
                  <button onClick={() => remove(p)} data-testid={`delete-${p.slug}`}
                          className="h-9 w-9 rounded-lg border border-neutral-200 hover:border-rose-300 hover:text-rose-600 text-neutral-500 flex items-center justify-center">
                    <Trash size={13} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Edit drawer */}
      {editing && (
        <div className="fixed inset-0 z-50 flex" data-testid="edit-drawer">
          <div className="flex-1 bg-black/40" onClick={() => setEditing(null)} />
          <div className="w-full max-w-2xl bg-white h-full overflow-y-auto shadow-2xl flex flex-col">
            <div className="flex items-center justify-between p-5 border-b border-neutral-100">
              <div className="font-semibold">{editing._isNew ? "Nouvel article" : "Modifier l'article"}</div>
              <button onClick={() => setEditing(null)} className="w-9 h-9 rounded-full hover:bg-neutral-100 flex items-center justify-center">
                <X size={18} />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-6 space-y-4">
              <Field label="Titre *" value={editing.title} onChange={(v) => setEditing({ ...editing, title: v })} testId="input-title" />
              <Field label="Catégorie" value={editing.category || ""} onChange={(v) => setEditing({ ...editing, category: v })} testId="input-category" />
              <Field label="Image (URL)" value={editing.image || ""} onChange={(v) => setEditing({ ...editing, image: v })} testId="input-image" />
              <Field label="Extrait (affiché sur les cards)" value={editing.excerpt || ""} onChange={(v) => setEditing({ ...editing, excerpt: v })} textarea rows={2} testId="input-excerpt" />
              <Field label="Contenu (Markdown — ## titres, **gras**, - puces)" value={editing.body || ""} onChange={(v) => setEditing({ ...editing, body: v })} textarea rows={15} testId="input-body" />
              <div className="grid grid-cols-2 gap-4">
                <Field label="Temps de lecture (min)" type="number" value={editing.read_minutes || 4} onChange={(v) => setEditing({ ...editing, read_minutes: Number(v) || 4 })} testId="input-read" />
                <Field label="Auteur" value={editing.author || ""} onChange={(v) => setEditing({ ...editing, author: v })} testId="input-author" />
              </div>
            </div>
            <div className="p-5 border-t border-neutral-100 flex gap-2">
              <button onClick={() => setEditing(null)} className="flex-1 h-11 rounded-xl border border-neutral-200 text-sm font-medium">Annuler</button>
              <button onClick={save} data-testid="save-post"
                      className="flex-1 h-11 rounded-xl bg-neutral-900 text-white text-sm font-medium flex items-center justify-center gap-1.5 hover:bg-neutral-800">
                <FloppyDisk size={15} /> Enregistrer
              </button>
            </div>
          </div>
        </div>
      )}

      {/* AI draft modal */}
      {aiOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-6 bg-black/50" data-testid="ai-modal">
          <div className="bg-white rounded-2xl w-full max-w-lg p-6 shadow-2xl">
            <div className="flex items-center gap-2 mb-4">
              <Sparkle size={20} weight="duotone" className="text-violet-600" />
              <h3 className="font-semibold text-lg">Rédiger avec l'IA</h3>
            </div>
            <p className="text-sm text-neutral-500 mb-5">L'IA rédige un article SEO optimisé (structure H2/H3, mini-FAQ, meta title/description) en ~30 secondes.</p>
            <div className="space-y-4">
              <Field label="Mot-clé cible *" placeholder="ex: fauteuil releveur remboursement" value={aiForm.keyword} onChange={(v) => setAiForm({ ...aiForm, keyword: v })} testId="ai-keyword" />
              <Field label="Angle (optionnel)" placeholder="ex: guide d'achat, FAQ, comparatif" value={aiForm.angle} onChange={(v) => setAiForm({ ...aiForm, angle: v })} testId="ai-angle" />
              <div>
                <label className="block text-[13px] font-medium text-neutral-900 mb-1.5">Longueur</label>
                <div className="flex gap-2">
                  {[{v:"short",l:"Court (600-800 mots)"},{v:"medium",l:"Moyen (1000-1400 mots)"},{v:"long",l:"Long (1800-2400 mots)"}].map((opt) => (
                    <button key={opt.v} onClick={() => setAiForm({ ...aiForm, length: opt.v })}
                            className={`flex-1 h-10 px-3 rounded-lg border text-[12px] font-medium transition ${aiForm.length === opt.v ? "bg-neutral-900 text-white border-neutral-900" : "bg-white border-neutral-200 text-neutral-600"}`}>
                      {opt.l}
                    </button>
                  ))}
                </div>
              </div>
            </div>
            <div className="flex gap-2 mt-6">
              <button onClick={() => setAiOpen(false)} className="flex-1 h-11 rounded-xl border border-neutral-200 text-sm font-medium">Annuler</button>
              <button onClick={aiGenerate} disabled={!aiForm.keyword || aiLoading} data-testid="ai-generate"
                      className="flex-1 h-11 rounded-xl bg-neutral-900 text-white text-sm font-medium disabled:opacity-50 flex items-center justify-center gap-1.5">
                <Sparkle size={14} weight={aiLoading ? "regular" : "fill"} className={aiLoading ? "animate-pulse" : ""} />
                {aiLoading ? "Rédaction…" : "Générer l'article"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function Field({ label, value, onChange, textarea, rows = 3, type = "text", placeholder, testId }) {
  return (
    <div>
      <label className="block text-[13px] font-medium text-neutral-900 mb-1.5">{label}</label>
      {textarea ? (
        <textarea
          value={value || ""}
          onChange={(e) => onChange(e.target.value)}
          rows={rows}
          placeholder={placeholder}
          data-testid={testId}
          className="w-full px-3 py-2 rounded-lg border border-neutral-200 focus:outline-none focus:ring-2 focus:ring-neutral-300 text-sm font-mono resize-y"
        />
      ) : (
        <input
          type={type}
          value={value ?? ""}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          data-testid={testId}
          className="w-full h-11 px-3 rounded-lg border border-neutral-200 focus:outline-none focus:ring-2 focus:ring-neutral-300 text-sm"
        />
      )}
    </div>
  );
}
