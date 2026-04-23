import React from "react";
import { ArrowClockwise, Storefront as StoreIcon } from "@phosphor-icons/react";

export default function LivePreview({ siteId, previewKey, onClose, onRefresh }) {
  const src = `/shop/${siteId}?preview=1&v=${previewKey}`;
  return (
    <div className="hidden xl:block" data-testid="live-preview">
      <div className="sticky top-6">
        <div className="bg-white border border-neutral-200 rounded-2xl overflow-hidden shadow-sm">
          <div className="flex items-center justify-between px-3 py-2 border-b border-neutral-100 bg-neutral-50">
            <div className="flex items-center gap-2 text-xs text-neutral-600">
              <div className="flex gap-1">
                <span className="w-2.5 h-2.5 rounded-full bg-red-400" />
                <span className="w-2.5 h-2.5 rounded-full bg-amber-400" />
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-400" />
              </div>
              <span className="font-mono truncate max-w-[180px]">/shop/{siteId.slice(0, 8)}…</span>
            </div>
            <div className="flex items-center gap-1">
              <button onClick={onRefresh} title="Rafraîchir"
                data-testid="preview-refresh"
                className="w-7 h-7 rounded hover:bg-neutral-200 text-neutral-600 flex items-center justify-center">
                <ArrowClockwise size={12} />
              </button>
              <a href={src} target="_blank" rel="noreferrer" title="Ouvrir en nouvel onglet"
                data-testid="preview-external"
                className="w-7 h-7 rounded hover:bg-neutral-200 text-neutral-600 flex items-center justify-center">
                <StoreIcon size={12} />
              </a>
              <button onClick={onClose} title="Fermer l'aperçu"
                data-testid="preview-close"
                className="w-7 h-7 rounded hover:bg-neutral-200 text-neutral-600 flex items-center justify-center text-xs">
                ✕
              </button>
            </div>
          </div>
          <iframe
            key={previewKey}
            src={src}
            title="Aperçu storefront"
            data-testid="preview-iframe"
            className="w-full h-[720px] bg-white"
            loading="lazy"
          />
        </div>
        <div className="text-[11px] text-neutral-400 mt-2 text-center">
          L'aperçu se rafraîchit à chaque modification enregistrée.
        </div>
      </div>
    </div>
  );
}
