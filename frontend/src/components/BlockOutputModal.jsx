import React, { useState } from "react";
import { X as XIcon, Copy, CheckCircle } from "@phosphor-icons/react";

function renderLeaf(v) {
  if (v === null || v === undefined) return <span className="text-[#78716C] italic">—</span>;
  if (typeof v === "string") return <span className="whitespace-pre-wrap">{v}</span>;
  if (typeof v === "number" || typeof v === "boolean") return <span className="font-mono text-[#B84B31]">{String(v)}</span>;
  return <pre className="text-xs bg-[#FAF7F2] rounded p-2 overflow-auto">{JSON.stringify(v, null, 2)}</pre>;
}

function renderArray(arr) {
  return (
    <ul className="space-y-1 list-disc list-inside">
      {arr.map((item, i) => (
        <li key={i} className="text-sm text-[#1C1917]">
          {typeof item === "object" && item !== null ? (
            <pre className="inline text-xs bg-[#FAF7F2] rounded p-1.5 ml-2">{JSON.stringify(item, null, 2)}</pre>
          ) : (
            renderLeaf(item)
          )}
        </li>
      ))}
    </ul>
  );
}

function renderValue(v) {
  if (Array.isArray(v)) return renderArray(v);
  if (typeof v === "object" && v !== null) {
    return (
      <div className="space-y-2 pl-3 border-l-2 border-[#F5F2EB]">
        {Object.entries(v).map(([k, val]) => (
          <div key={k}>
            <div className="text-[10px] font-semibold uppercase tracking-wider text-[#57534E] mb-1">
              {k.replace(/_/g, " ")}
            </div>
            <div className="text-sm text-[#1C1917]">
              {Array.isArray(val) ? renderArray(val) : renderLeaf(val)}
            </div>
          </div>
        ))}
      </div>
    );
  }
  return renderLeaf(v);
}

export default function BlockOutputModal({ output, onClose }) {
  const [copied, setCopied] = useState(false);
  const rawJson = JSON.stringify(output.output, null, 2);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(rawJson);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {}
  };

  const entries = Object.entries(output.output || {});

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-neutral-900/40 p-4" onClick={onClose}>
      <div
        className="bg-white rounded-2xl w-full max-w-4xl shadow-2xl max-h-[90vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
        data-testid="block-output-modal"
      >
        <div className="flex items-start justify-between p-6 pb-4 border-b border-[#E7E5E4]">
          <div className="flex items-center gap-3">
            <div className="text-3xl">{output.block_emoji}</div>
            <div>
              <div className="text-[11px] uppercase tracking-widest text-[#78716C]">
                Livrable Mega-Bloc IA · Claude 4.5
              </div>
              <h2 className="font-heading text-xl font-semibold text-[#1C1917]">
                {output.block_name}
              </h2>
              <div className="text-xs text-[#78716C]">
                Généré le {new Date(output.created_at).toLocaleString("fr-FR")}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={copy}
              data-testid="copy-block-output"
              className="h-9 px-3 rounded-lg bg-[#1C1917] hover:bg-[#44403C] text-neutral-900 text-xs font-medium flex items-center gap-1.5"
            >
              {copied ? (
                <>
                  <CheckCircle size={12} weight="fill" /> Copié
                </>
              ) : (
                <>
                  <Copy size={12} /> Copier le JSON
                </>
              )}
            </button>
            <button
              onClick={onClose}
              data-testid="block-output-close"
              className="w-9 h-9 rounded-lg hover:bg-[#F5F2EB] flex items-center justify-center"
            >
              <XIcon size={16} />
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-6 space-y-5">
          {entries.length === 0 ? (
            <div className="text-sm text-[#78716C]">Livrable vide.</div>
          ) : (
            entries.map(([key, val]) => (
              <section key={key}>
                <h3 className="font-heading text-sm font-semibold text-[#B84B31] mb-2 uppercase tracking-wider">
                  {key.replace(/_/g, " ")}
                </h3>
                {renderValue(val)}
              </section>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
