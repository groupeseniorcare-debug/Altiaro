import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowLeft, CheckCircle, Warning, Clock, XCircle, Eye, Flag, Rocket,
} from "@phosphor-icons/react";
import { api, apiCall } from "../lib/api";

export default function AdminReview() {
  const [sites, setSites] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeModal, setActiveModal] = useState(null); // site object being reviewed
  const [decision, setDecision] = useState("approve");
  const [note, setNote] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const load = async () => {
    setLoading(true);
    const { data } = await apiCall(() => api.get("/admin/review-queue"));
    setSites(data || []);
    setLoading(false);
  };
  useEffect(() => { load(); }, []);

  const submit = async () => {
    if (!activeModal) return;
    setSubmitting(true);
    await apiCall(() => api.post(`/sites/${activeModal.id}/review`, { decision, note }));
    setSubmitting(false);
    setActiveModal(null);
    setNote("");
    load();
  };

  const launch = async (siteId) => {
    if (!window.confirm("Lancer ce site (Google Ads) ?")) return;
    await apiCall(() => api.post(`/sites/${siteId}/launch`));
    load();
  };

  return (
    <div className="min-h-screen bg-[#FAF7F2]">
      <div className="max-w-6xl mx-auto px-6 md:px-10 py-8">
        <Link to="/" className="inline-flex items-center gap-2 text-sm text-neutral-600 hover:text-neutral-900 mb-6" data-testid="admin-review-back">
          <ArrowLeft size={14} /> Retour au dashboard
        </Link>

        <div className="mb-8">
          <div className="text-[11px] uppercase tracking-[0.2em] text-neutral-500 mb-2 flex items-center gap-2">
            <Flag size={12} weight="bold" /> Admin · File de validation
          </div>
          <h1 className="text-3xl md:text-4xl font-semibold text-neutral-900" style={{ fontFamily: "'Fraunces', serif" }}>
            Sites en attente de validation
          </h1>
          <p className="text-sm text-neutral-500 mt-2">
            {sites.length} site{sites.length !== 1 ? "s" : ""} soumis{sites.length > 1 ? "" : ""} par des Concepteurs. Validez ou demandez des corrections.
          </p>
        </div>

        {loading ? (
          <div className="py-20 text-center text-neutral-500">Chargement…</div>
        ) : sites.length === 0 ? (
          <div className="bg-white border border-neutral-200 rounded-2xl p-12 text-center" data-testid="admin-review-empty">
            <CheckCircle size={40} weight="duotone" className="mx-auto text-emerald-500 mb-3" />
            <div className="font-semibold text-neutral-900 mb-1">Aucun site en attente</div>
            <div className="text-sm text-neutral-500">Tous les sites soumis ont été traités.</div>
          </div>
        ) : (
          <div className="space-y-4" data-testid="admin-review-list">
            {sites.map((s) => <ReviewCard key={s.id} site={s} onReview={() => { setActiveModal(s); setDecision("approve"); setNote(""); }} onLaunch={() => launch(s.id)} />)}
          </div>
        )}
      </div>

      {activeModal && (
        <ReviewModal
          site={activeModal}
          decision={decision}
          setDecision={setDecision}
          note={note}
          setNote={setNote}
          onClose={() => setActiveModal(null)}
          onSubmit={submit}
          submitting={submitting}
        />
      )}
    </div>
  );
}

function ReviewCard({ site, onReview, onLaunch }) {
  const qa = site.submission?.qa_snapshot || {};
  const submittedAt = site.submission?.submitted_at;
  const blockers = qa.blockers || [];
  const checks = qa.checks || [];
  const passed = qa.passed || 0;
  const total = qa.total || 0;

  return (
    <div className="bg-white border border-neutral-200 rounded-2xl p-5" data-testid={`review-card-${site.id}`}>
      <div className="flex items-start justify-between gap-4 flex-wrap mb-4">
        <div className="min-w-0">
          <div className="text-[11px] uppercase tracking-widest text-neutral-500">{site.niche}</div>
          <h3 className="text-xl font-semibold text-neutral-900 mt-0.5" style={{ fontFamily: "'Fraunces', serif" }}>
            {site.name}
          </h3>
          <div className="text-xs text-neutral-500 mt-1">
            Par <span className="font-medium text-neutral-700">{site.operator?.email || "inconnu"}</span> ·
            Soumis le {submittedAt ? new Date(submittedAt).toLocaleDateString("fr-FR", { day: "2-digit", month: "long", year: "numeric" }) : "—"} ·
            {(site.selected_countries || []).join(", ") || "—"}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Link to={`/shop/${site.id}`} target="_blank" rel="noreferrer" className="h-9 px-3 rounded-lg bg-white border border-neutral-200 text-xs font-medium text-neutral-700 hover:border-neutral-400 flex items-center gap-1.5">
            <Eye size={12} /> Voir la boutique
          </Link>
        </div>
      </div>

      {/* QA snapshot */}
      <div className="bg-[#FDFBF7] rounded-xl p-4 mb-4">
        <div className="flex items-center justify-between gap-4 mb-3 flex-wrap">
          <div className="flex items-center gap-3">
            <div className={`w-12 h-12 rounded-full flex items-center justify-center text-lg font-bold ${qa.score >= 80 ? "bg-emerald-100 text-emerald-700" : qa.score >= 60 ? "bg-amber-100 text-amber-700" : "bg-rose-100 text-rose-700"}`}>
              {qa.score || 0}
            </div>
            <div>
              <div className="text-sm font-semibold text-neutral-900">Score QA · {passed}/{total} contrôles passés</div>
              <div className="text-xs text-neutral-500">
                {blockers.length > 0 ? `${blockers.length} bloquant(s) non résolu(s)` : "Aucun bloquant"}
              </div>
            </div>
          </div>
        </div>
        {blockers.length > 0 && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mb-3">
            {blockers.slice(0, 6).map((b, i) => (
              <div key={i} className="flex items-start gap-2 text-xs bg-rose-50 border border-rose-200 p-2 rounded-lg">
                <XCircle size={14} weight="fill" className="text-rose-600 mt-0.5 flex-shrink-0" />
                <div>
                  <div className="font-medium text-rose-900">{b.label}</div>
                  {b.detail && <div className="text-rose-700 text-[11px]">{b.detail}</div>}
                </div>
              </div>
            ))}
          </div>
        )}
        <div className="grid grid-cols-2 md:grid-cols-3 gap-x-4 gap-y-1 text-[11px]">
          {checks.slice(0, 12).map((c, i) => (
            <div key={i} className="flex items-center gap-1.5">
              {c.pass ? (
                <CheckCircle size={11} weight="fill" className="text-emerald-600" />
              ) : c.critical ? (
                <XCircle size={11} weight="fill" className="text-rose-500" />
              ) : (
                <Warning size={11} weight="fill" className="text-amber-500" />
              )}
              <span className={c.pass ? "text-neutral-700" : "text-neutral-500"}>{c.label}</span>
            </div>
          ))}
        </div>
      </div>

      {site.submission?.concepteur_note && (
        <div className="rounded-xl bg-sky-50 border border-sky-200 p-3 text-sm text-sky-900 mb-4">
          <strong>Note du Concepteur :</strong> {site.submission.concepteur_note}
        </div>
      )}

      <div className="flex gap-2 flex-wrap">
        <button
          onClick={onReview}
          data-testid={`review-btn-${site.id}`}
          className="h-10 px-4 rounded-xl bg-neutral-900 hover:bg-neutral-800 text-white text-sm font-medium flex items-center gap-2"
        >
          <Flag size={14} weight="bold" /> Valider / Demander correction
        </button>
        {site.status === "approved" && (
          <button
            onClick={onLaunch}
            className="h-10 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-medium flex items-center gap-2"
          >
            <Rocket size={14} weight="bold" /> Marquer comme lancé
          </button>
        )}
      </div>
    </div>
  );
}

function ReviewModal({ site, decision, setDecision, note, setNote, onClose, onSubmit, submitting }) {
  return (
    <div className="fixed inset-0 z-50 bg-neutral-900/60 flex items-center justify-center p-4" onClick={onClose}>
      <div
        className="bg-white rounded-2xl w-full max-w-lg p-6 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
        data-testid="review-modal"
      >
        <h2 className="text-xl font-semibold text-neutral-900 mb-1" style={{ fontFamily: "'Fraunces', serif" }}>
          Valider « {site.name} »
        </h2>
        <p className="text-sm text-neutral-500 mb-5">Votre décision sera envoyée au Concepteur.</p>

        <div className="grid grid-cols-2 gap-2 mb-5">
          <button
            onClick={() => setDecision("approve")}
            data-testid="review-approve"
            className={`p-4 rounded-xl border text-left transition ${decision === "approve" ? "border-emerald-500 bg-emerald-50" : "border-neutral-200 hover:border-neutral-300"}`}
          >
            <CheckCircle size={20} weight="fill" className="text-emerald-600 mb-1" />
            <div className="font-semibold text-sm">Approuver</div>
            <div className="text-[11px] text-neutral-500">Prêt à lancer les Ads</div>
          </button>
          <button
            onClick={() => setDecision("changes_req")}
            data-testid="review-changes-req"
            className={`p-4 rounded-xl border text-left transition ${decision === "changes_req" ? "border-amber-500 bg-amber-50" : "border-neutral-200 hover:border-neutral-300"}`}
          >
            <Warning size={20} weight="fill" className="text-amber-600 mb-1" />
            <div className="font-semibold text-sm">Demander correction</div>
            <div className="text-[11px] text-neutral-500">Concepteur repasse dessus</div>
          </button>
        </div>

        <label className="block text-xs font-medium text-neutral-700 mb-1.5">
          Message pour le Concepteur {decision === "changes_req" && <span className="text-rose-500">*</span>}
        </label>
        <textarea
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder={decision === "approve" ? "Bravo ! Tu peux lancer les Ads demain." : "Ex: Manque la page 'À propos', SEO à enrichir sur le produit X…"}
          data-testid="review-note"
          rows={4}
          className="w-full rounded-xl border border-neutral-200 p-3 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-300 mb-5"
        />

        <div className="flex justify-end gap-2">
          <button onClick={onClose} disabled={submitting} className="h-10 px-4 rounded-xl text-sm text-neutral-600 hover:bg-neutral-100">
            Annuler
          </button>
          <button
            onClick={onSubmit}
            disabled={submitting || (decision === "changes_req" && !note.trim())}
            data-testid="review-submit"
            className="h-10 px-5 rounded-xl bg-neutral-900 hover:bg-neutral-800 text-white text-sm font-medium disabled:opacity-50"
          >
            {submitting ? "Envoi…" : "Confirmer"}
          </button>
        </div>
      </div>
    </div>
  );
}
