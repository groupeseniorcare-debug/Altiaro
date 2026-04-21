import React, { useState } from "react";
import { marked } from "marked";
import { api, apiCall } from "../lib/api";
import {
  X,
  Sparkle,
  FloppyDisk,
  PaperPlaneRight,
  CheckCircle,
  XCircle,
  UploadSimple,
  Spinner,
  ClipboardText,
  FileText,
  LinkSimple,
  Hourglass,
} from "@phosphor-icons/react";

marked.setOptions({ gfm: true, breaks: false });

const STATUS_META = {
  locked: { label: "Verrouillée", color: "#78716C", bg: "#F5F5F4" },
  in_progress: { label: "En cours", color: "#B45309", bg: "#FEF3C7" },
  awaiting_validation: { label: "En attente de validation", color: "#0369A1", bg: "#E0F2FE" },
  validated: { label: "Validée ✓", color: "#047857", bg: "#D1FAE5" },
  rejected: { label: "À refaire", color: "#BE123C", bg: "#FFE4E6" },
};

export default function StepPanel({ step: initialStep, site, isAdmin, onClose, onUpdate }) {
  const [step, setStep] = useState(initialStep);
  const [url, setUrl] = useState(step.deliverable_url || "");
  const [notes, setNotes] = useState(step.deliverable_notes || "");
  const [aiResponse, setAiResponse] = useState(step.ai_response || "");
  const [aiModel, setAiModel] = useState("anthropic/claude-sonnet-4-5-20250929");
  const [executing, setExecuting] = useState(Boolean(initialStep.ai_executing));
  const [saving, setSaving] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [rejectReason, setRejectReason] = useState("");
  const [showReject, setShowReject] = useState(false);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);

  const meta = STATUS_META[step.status] || STATUS_META.locked;
  const readOnly = step.status === "validated" || step.status === "awaiting_validation";

  const refreshStep = (newStep) => {
    setStep(newStep);
    setUrl(newStep.deliverable_url || "");
    setNotes(newStep.deliverable_notes || "");
    setAiResponse(newStep.ai_response || "");
    onUpdate(newStep);
  };

  const substitutePrompt = (text) => {
    const subs = {
      "[NICHE]": site?.niche || "",
      "[NOM_MARQUE]": site?.name || "",
      "[NOM]": site?.name || "",
      "[NOM_CHOISI]": site?.name || "",
      "[DOMAINE]": site?.domain || "",
      "[URL_ADMIN]": site?.shopify_url || "",
      "[MON_SHOPIFY]": site?.shopify_url || "",
    };
    let out = text;
    Object.entries(subs).forEach(([k, v]) => { if (v) out = out.replaceAll(k, v); });
    return out;
  };

  const copyPrompt = async () => {
    await navigator.clipboard.writeText(substitutePrompt(step.prompt));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleSave = async () => {
    setSaving(true);
    setError("");
    const { data, error: err } = await apiCall(() =>
      api.patch(`/steps/${step.id}`, {
        deliverable_url: url,
        deliverable_notes: notes,
      })
    );
    setSaving(false);
    if (err) setError(err);
    else if (data) refreshStep(data);
  };

  const handleExecute = async () => {
    setExecuting(true);
    setError("");
    const [provider, model] = aiModel.split("/");
    const { error: err } = await apiCall(() =>
      api.post(`/steps/${step.id}/execute`, {
        model_provider: provider,
        model_name: model,
      })
    );
    if (err) {
      setExecuting(false);
      setError(err);
      return;
    }
    // Fire-and-forget launched on backend — poll the step every 2.5s for up to 3 minutes
    const startTs = Date.now();
    const pollInterval = setInterval(async () => {
      const { data: refreshed } = await apiCall(() => api.get(`/steps/${step.id}`));
      if (!refreshed) return;
      if (refreshed.ai_executing === false && (refreshed.ai_response || refreshed.ai_error)) {
        clearInterval(pollInterval);
        setExecuting(false);
        if (refreshed.ai_error) {
          setError(refreshed.ai_error);
        } else if (refreshed.ai_response) {
          setAiResponse(refreshed.ai_response);
          refreshStep(refreshed);
        }
      } else if (Date.now() - startTs > 180000) {
        clearInterval(pollInterval);
        setExecuting(false);
        setError("Timeout : l'IA n'a pas répondu dans les 3 minutes. Réessayez.");
      }
    }, 2500);
  };

  const handleUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const fd = new FormData();
    fd.append("file", file);
    try {
      const { data } = await api.post(`/steps/${step.id}/upload`, fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      const { data: refreshed } = await apiCall(() => api.get(`/steps/${step.id}`));
      if (refreshed) refreshStep(refreshed);
    } catch (err) {
      setError(err.response?.data?.detail || "Upload échoué");
    }
  };

  const handleSubmit = async () => {
    setError("");
    // save first
    await handleSave();
    setSubmitting(true);
    const { data, error: err } = await apiCall(() => api.post(`/steps/${step.id}/submit`));
    setSubmitting(false);
    if (err) {
      setError(err);
    } else if (data) {
      refreshStep(data);
      onClose();
    }
  };

  const handleValidate = async () => {
    const { data, error: err } = await apiCall(() =>
      api.post(`/steps/${step.id}/validate`, { comment: "" })
    );
    if (err) setError(err);
    else if (data) {
      refreshStep(data);
      onClose();
    }
  };

  const handleReject = async () => {
    if (!rejectReason.trim()) {
      setError("Ajoutez un motif de refus");
      return;
    }
    const { data, error: err } = await apiCall(() =>
      api.post(`/steps/${step.id}/reject`, { reason: rejectReason })
    );
    if (err) setError(err);
    else if (data) {
      refreshStep(data);
      setShowReject(false);
      onClose();
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex justify-end" data-testid="step-panel">
      <div className="absolute inset-0 bg-[#1C1917]/40 backdrop-blur-sm animate-fade-up" onClick={onClose} />
      <div className="relative w-full max-w-[900px] bg-[#FDFBF7] shadow-2xl overflow-y-auto animate-fade-up">
        {/* Header */}
        <div className="sticky top-0 z-10 bg-white border-b border-[#E7E5E4] px-8 py-5 flex items-center justify-between">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2.5 mb-1">
              <span className="text-xs font-mono text-[#78716C]">#{step.number}</span>
              <span
                className="text-[10px] uppercase tracking-widest px-2 py-0.5 rounded-full"
                style={{ backgroundColor: meta.bg, color: meta.color }}
              >
                {meta.label}
              </span>
              <span className="text-xs text-[#78716C]">Phase {step.phase} · {step.phase_name}</span>
            </div>
            <h2 className="font-heading text-2xl font-semibold text-[#1C1917] truncate">{step.title}</h2>
          </div>
          <button
            onClick={onClose}
            data-testid="step-panel-close"
            className="w-10 h-10 rounded-lg hover:bg-[#F5F2EB] flex items-center justify-center transition"
          >
            <X size={18} />
          </button>
        </div>

        <div className="p-8 space-y-6">
          {/* Summary */}
          <div className="p-4 rounded-xl bg-[#F5F2EB] text-[#57534E] text-sm leading-relaxed">
            {step.summary}
          </div>

          {/* How it works help banner */}
          {!readOnly && (
            <div className="p-4 rounded-xl bg-white border border-[#E7E5E4]">
              <div className="text-[11px] uppercase tracking-widest text-[#B84B31] font-semibold mb-2">
                Comment ça marche
              </div>
              <ol className="space-y-1.5 text-sm text-[#57534E] leading-relaxed list-decimal pl-5">
                <li>
                  <strong className="text-[#1C1917]">Lis le prompt</strong> ci-dessous (l'expertise de Claude 4.5 pour cette étape).
                </li>
                <li>
                  Clique <strong className="text-[#1C1917]">« Exécuter le prompt »</strong> pour générer un premier livrable via l'IA.
                </li>
                <li>
                  Affine la réponse dans les <strong className="text-[#1C1917]">champs Livrables</strong> :
                  <ul className="list-disc pl-5 mt-1 text-xs text-[#78716C] space-y-0.5">
                    <li><strong>URL externe</strong> : lien vers un Google Doc / Figma / page Shopify si tu as travaillé en dehors</li>
                    <li><strong>Notes internes</strong> : décisions prises, points clés du livrable</li>
                    <li><strong>Fichiers joints</strong> : PDF, images, CSV (max 15 Mo)</li>
                  </ul>
                </li>
                <li>
                  Clique <strong className="text-[#1C1917]">« Valider & continuer »</strong> pour acter l'étape et débloquer la suivante. La validation peut déclencher des automatismes (injection légal / import produits / renommage du site selon l'étape).
                </li>
              </ol>
            </div>
          )}

          {/* Prompt */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <ClipboardText size={18} weight="duotone" color="#B84B31" />
                <h3 className="font-heading text-lg font-semibold text-[#1C1917]">Prompt à exécuter</h3>
              </div>
              <button
                onClick={copyPrompt}
                data-testid="copy-prompt-btn"
                className="text-xs text-[#B84B31] hover:text-[#993D26] font-medium px-3 py-1.5 rounded-lg hover:bg-[#F5F2EB] transition"
              >
                {copied ? "Copié ✓" : "Copier"}
              </button>
            </div>
            <div className="bg-white rounded-xl border border-[#E7E5E4] overflow-hidden">
              <pre className="p-5 text-[13.5px] whitespace-pre-wrap font-mono text-[#1C1917] leading-relaxed max-h-[400px] overflow-y-auto">
                {substitutePrompt(step.prompt)}
              </pre>
            </div>
          </div>

          {/* AI Execute */}
          {!readOnly && (
            <div className="bg-white rounded-xl border border-[#E7E5E4] p-6">
              <div className="flex items-center gap-2 mb-1">
                <Sparkle size={20} weight="fill" color="#B84B31" />
                <h3 className="font-heading text-lg font-semibold text-[#1C1917]">Exécuter avec l'IA</h3>
              </div>
              <p className="text-sm text-[#78716C] mb-4">
                Générez un livrable initial. Vous pourrez l'affiner puis le soumettre à validation.
              </p>
              <div className="flex items-center gap-3 mb-4">
                <div className="h-10 px-3 rounded-lg border border-[#E7E5E4] bg-neutral-50 text-xs text-neutral-700 font-mono flex items-center gap-2">
                  <Sparkle size={12} weight="fill" color="#B84B31" />
                  Claude Sonnet 4.5
                </div>
                <button
                  onClick={handleExecute}
                  disabled={executing}
                  data-testid="step-execute-ai"
                  className="h-10 px-4 rounded-lg bg-neutral-900 hover:bg-neutral-800 text-white text-sm font-medium flex items-center gap-2 disabled:opacity-60 transition active:scale-[0.98]"
                >
                  {executing ? (
                    <>
                      <Spinner size={16} className="animate-spin" /> Génération en cours...
                    </>
                  ) : (
                    <>
                      <Sparkle size={16} weight="fill" /> Exécuter le prompt
                    </>
                  )}
                </button>
              </div>
              {executing && (
                <div className="text-xs text-[#78716C]">
                  ⏳ L'IA peut mettre 20-60 secondes pour un prompt long. Ne fermez pas ce panneau.
                </div>
              )}
            </div>
          )}

          {/* AI Response */}
          {aiResponse && (
            <div>
              <h3 className="font-heading text-lg font-semibold text-[#1C1917] mb-3 flex items-center gap-2">
                <Sparkle size={18} weight="fill" color="#B84B31" />
                Réponse IA
                {step.ai_model_used && <span className="text-xs text-[#78716C] font-normal font-mono">· {step.ai_model_used}</span>}
              </h3>
              <div
                className="bg-white rounded-xl border border-[#E7E5E4] p-6 markdown-body max-h-[500px] overflow-y-auto"
                data-testid="step-ai-response"
                dangerouslySetInnerHTML={{ __html: marked.parse(aiResponse) }}
              />
            </div>
          )}

          {/* Deliverable inputs */}
          <div>
            <h3 className="font-heading text-lg font-semibold text-[#1C1917] mb-4 flex items-center gap-2">
              <FileText size={18} weight="duotone" color="#B84B31" />
              Livrables
            </h3>
            <div className="space-y-4">
              <div>
                <label className="block text-[13px] font-medium text-[#1C1917] mb-1.5 flex items-center gap-1.5">
                  <LinkSimple size={14} /> URL externe (Google Doc, Figma, Shopify page…)
                </label>
                <input
                  type="url"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  disabled={readOnly}
                  placeholder="https://..."
                  data-testid="step-url-input"
                  className="w-full h-11 px-4 rounded-lg border border-[#E7E5E4] bg-white focus:outline-none focus:ring-2 focus:ring-[#B84B31]/30 focus:border-[#B84B31] disabled:bg-[#FAF7F2] disabled:cursor-not-allowed"
                />
              </div>

              <div>
                <label className="block text-[13px] font-medium text-[#1C1917] mb-1.5">Notes internes</label>
                <textarea
                  rows={4}
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  disabled={readOnly}
                  placeholder="Commentaires, décisions prises, éléments de contexte..."
                  data-testid="step-notes-input"
                  className="w-full px-4 py-3 rounded-lg border border-[#E7E5E4] bg-white focus:outline-none focus:ring-2 focus:ring-[#B84B31]/30 focus:border-[#B84B31] resize-none disabled:bg-[#FAF7F2]"
                />
              </div>

              <div>
                <label className="block text-[13px] font-medium text-[#1C1917] mb-1.5">Fichiers joints</label>
                {step.deliverable_files?.length > 0 && (
                  <div className="mb-3 space-y-2">
                    {step.deliverable_files.map((f, i) => (
                      <a
                        key={i}
                        href={`${process.env.REACT_APP_BACKEND_URL}${f.url}`}
                        target="_blank"
                        rel="noreferrer"
                        className="flex items-center gap-2 p-2.5 rounded-lg bg-white border border-[#E7E5E4] hover:border-[#B84B31]/50 text-sm text-[#57534E] hover:text-[#1C1917] transition"
                        data-testid={`step-file-${i}`}
                      >
                        <FileText size={16} />
                        <span className="flex-1 truncate">{f.original_name}</span>
                        <span className="text-xs text-[#78716C]">{(f.size / 1024).toFixed(0)} Ko</span>
                      </a>
                    ))}
                  </div>
                )}
                {!readOnly && (
                  <label className="flex items-center justify-center gap-2 h-11 rounded-lg border border-dashed border-[#B84B31]/40 bg-[#FDFBF7] hover:bg-[#F5F2EB] text-sm text-[#B84B31] cursor-pointer transition">
                    <UploadSimple size={16} />
                    <span>Ajouter un fichier (max 15 Mo)</span>
                    <input type="file" className="hidden" onChange={handleUpload} data-testid="step-file-upload" />
                  </label>
                )}
              </div>
            </div>
          </div>

          {/* Rejection reason display */}
          {step.status === "rejected" && step.rejection_reason && (
            <div className="p-4 rounded-xl bg-[#FFE4E6] border border-[#FCA5A5]">
              <div className="text-[11px] uppercase tracking-widest text-[#BE123C] font-semibold mb-1">
                Motif de refus
              </div>
              <div className="text-sm text-[#991B1B]">{step.rejection_reason}</div>
            </div>
          )}

          {error && (
            <div className="p-3.5 rounded-lg bg-[#FFE4E6] text-[#BE123C] text-sm" data-testid="step-error">
              {error}
            </div>
          )}
        </div>

        {/* Sticky footer actions */}
        <div className="sticky bottom-0 bg-white border-t border-[#E7E5E4] px-8 py-5">
          {isAdmin && step.status === "awaiting_validation" && !showReject && (
            <div className="flex items-center gap-3 justify-end">
              <button
                onClick={() => setShowReject(true)}
                data-testid="step-reject-btn"
                className="h-11 px-5 rounded-xl border border-[#E7E5E4] text-[#BE123C] hover:bg-[#FFE4E6] font-medium transition flex items-center gap-2"
              >
                <XCircle size={18} /> Refuser
              </button>
              <button
                onClick={handleValidate}
                data-testid="step-validate-btn"
                className="h-11 px-5 rounded-xl bg-[#047857] hover:bg-[#065F46] text-neutral-900 font-medium transition flex items-center gap-2 active:scale-[0.98]"
              >
                <CheckCircle size={18} weight="fill" /> Valider et déverrouiller la suivante
              </button>
            </div>
          )}

          {isAdmin && showReject && (
            <div className="space-y-3">
              <textarea
                rows={2}
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                placeholder="Motif du refus, attendu pour la seconde tentative..."
                data-testid="step-reject-reason"
                className="w-full px-4 py-3 rounded-lg border border-[#E7E5E4] focus:outline-none focus:ring-2 focus:ring-[#BE123C]/30 resize-none"
              />
              <div className="flex justify-end gap-3">
                <button
                  onClick={() => setShowReject(false)}
                  className="h-10 px-4 rounded-lg border border-[#E7E5E4] text-[#57534E] hover:bg-[#FDFBF7] transition"
                >
                  Annuler
                </button>
                <button
                  onClick={handleReject}
                  data-testid="step-reject-confirm"
                  className="h-10 px-4 rounded-lg bg-[#BE123C] hover:bg-[#9F1239] text-neutral-900 font-medium flex items-center gap-2"
                >
                  <XCircle size={16} /> Confirmer le refus
                </button>
              </div>
            </div>
          )}

          {(step.status === "in_progress" || step.status === "rejected") && !readOnly && (() => {
            const hasDeliverable = !!(url?.trim() || notes?.trim() || aiResponse?.trim() || (step.deliverable_files?.length > 0));
            return (
              <div className="flex items-center justify-between gap-4">
                <div className="text-xs text-[#78716C] flex-1">
                  {hasDeliverable
                    ? "Renseignez vos livrables puis validez pour passer à l'étape suivante."
                    : "Exécutez le prompt IA ou renseignez un livrable (URL / notes / fichier) pour pouvoir valider."}
                </div>
                <div className="flex gap-3 shrink-0">
                  <button
                    onClick={handleSave}
                    disabled={saving}
                    data-testid="step-save-btn"
                    className="h-11 px-4 rounded-xl border border-[#E7E5E4] text-[#57534E] hover:bg-[#FDFBF7] font-medium transition flex items-center gap-2 disabled:opacity-60"
                  >
                    {saving ? <Spinner size={16} className="animate-spin" /> : <FloppyDisk size={16} />}
                    Enregistrer brouillon
                  </button>
                  <button
                    onClick={handleSubmit}
                    disabled={submitting || !hasDeliverable}
                    title={!hasDeliverable ? "Génère un livrable via l'IA ou remplis un champ avant de valider" : "Valide l'étape et passe à la suivante"}
                    data-testid="step-submit-btn"
                    className="h-11 px-5 rounded-xl bg-[#047857] hover:bg-[#065F46] text-white font-medium transition flex items-center gap-2 active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {submitting ? <Spinner size={16} className="animate-spin" /> : <CheckCircle size={16} weight="fill" />}
                    Valider & continuer
                  </button>
                </div>
              </div>
            );
          })()}

          {step.status === "awaiting_validation" && !isAdmin && (
            <div className="flex items-center gap-3 text-sm text-[#0369A1]">
              <Hourglass size={18} />
              En attente de validation par l'administrateur.
            </div>
          )}

          {step.status === "validated" && (
            <div className="flex items-center gap-3 text-sm text-[#047857]">
              <CheckCircle size={18} weight="fill" />
              Étape validée le {step.validated_at ? new Date(step.validated_at).toLocaleDateString("fr-FR") : ""}.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// End of StepPanel component
