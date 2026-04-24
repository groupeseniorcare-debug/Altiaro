import React from "react";
import {
  Globe, Link as LinkIcon, ArrowClockwise, CheckCircle, Warning, X as XIcon,
} from "@phosphor-icons/react";

/**
 * Chantier 6 — DomainModal extrait du cockpit pour alléger SiteDetail.jsx.
 * Logique inchangée vs version précédente — uniquement déplacée.
 */
export default function DomainModal({
  status, input, setInput, busy, msg, onSave, onVerify, onClear, onClose,
}) {
  const verified = status?.custom_domain_verified;
  const hasDomain = !!status?.custom_domain;
  const target = status?.cname_target || "";
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-neutral-900/40 p-4" onClick={onClose}>
      <div
        className="bg-white rounded-md w-full max-w-xl p-6 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
        data-testid="domain-modal"
      >
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-neutral-200 flex items-center justify-center">
              <Globe size={20} weight="duotone" className="text-neutral-900" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-neutral-900">Domaine custom</h2>
              <p className="text-xs text-neutral-500">Connecte ta boutique à ton propre nom de domaine.</p>
            </div>
          </div>
          <button onClick={onClose} className="w-8 h-8 rounded-lg hover:bg-neutral-200" data-testid="domain-modal-close">
            <XIcon size={16} className="mx-auto" />
          </button>
        </div>
        <label className="block text-xs font-medium text-neutral-600 mb-1.5">Nom de domaine</label>
        <input
          type="text" value={input} onChange={(e) => setInput(e.target.value)}
          placeholder="maboutique.fr" data-testid="domain-input"
          className="w-full h-11 px-3 rounded-lg border border-neutral-200 bg-white text-sm mb-3 focus:outline-none focus:border-neutral-400"
        />
        <div className="bg-neutral-100/40 rounded-lg border border-neutral-200 p-4 mb-4 text-sm">
          <div className="font-medium text-neutral-900 mb-2 flex items-center gap-2">
            <LinkIcon size={14} /> Configuration DNS requise
          </div>
          <div className="grid grid-cols-[80px_1fr] gap-y-1.5 gap-x-3 text-xs font-mono text-neutral-600">
            <span>Type</span><span className="text-neutral-900">CNAME</span>
            <span>Nom</span><span className="text-neutral-900">@ (ou www)</span>
            <span>Valeur</span><span className="text-neutral-900 break-all">{target}</span>
            <span>TTL</span><span className="text-neutral-900">3600</span>
          </div>
          <p className="text-[11px] text-neutral-500 mt-2">
            Ajoute ce CNAME chez ton registrar (OVH, Gandi, Cloudflare…) puis clique "Vérifier".
            Propagation&nbsp;: 5&nbsp;min à 24h.
          </p>
        </div>
        {msg && (
          <div className={`mb-3 p-2.5 rounded-lg text-xs flex gap-2 ${
            msg.kind === "ok" ? "bg-emerald-500/10 text-emerald-700"
              : msg.kind === "warn" ? "bg-amber-500/10 text-amber-700"
              : "bg-red-500/10 text-red-500"
          }`} data-testid="domain-msg">
            {msg.kind === "ok"
              ? <CheckCircle size={14} weight="fill" className="shrink-0 mt-0.5" />
              : <Warning size={14} weight="fill" className="shrink-0 mt-0.5" />}
            {msg.text}
          </div>
        )}
        <div className="flex items-center justify-between gap-2">
          <div>
            {hasDomain && (
              <button type="button" onClick={onClear} disabled={busy} data-testid="domain-clear"
                className="h-10 px-3 rounded-lg text-sm text-red-500 hover:bg-red-500/10 disabled:opacity-50">
                Retirer
              </button>
            )}
          </div>
          <div className="flex gap-2">
            <button type="button" onClick={onSave} disabled={busy || !input.trim()} data-testid="domain-save"
              className="h-10 px-4 rounded-lg bg-white border border-neutral-200 hover:border-[#B84B31] text-sm font-medium disabled:opacity-50">
              Enregistrer
            </button>
            {hasDomain && (
              <button type="button" onClick={onVerify} disabled={busy} data-testid="domain-verify"
                className="h-10 px-4 rounded-lg bg-neutral-900 hover:bg-neutral-800 text-white text-sm font-medium disabled:opacity-50 flex items-center gap-2">
                {busy ? <ArrowClockwise size={14} className="animate-spin" />
                  : verified ? <CheckCircle size={14} weight="fill" />
                  : <Globe size={14} weight="duotone" />}
                {verified ? "Re-vérifier" : "Vérifier DNS"}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
