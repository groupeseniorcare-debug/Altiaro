import React, { useState } from "react";
import { ArrowClockwise, Sparkle } from "@phosphor-icons/react";

export function AiField({ label, field, aiField, tweak, setTweak, onGenerate, children }) {
  const busy = aiField === field;
  const [showTweak, setShowTweak] = useState(false);
  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <div className="text-[11px] uppercase tracking-widest text-neutral-500">{label}</div>
        <div className="flex items-center gap-1">
          {showTweak && (
            <input
              type="text"
              value={tweak || ""}
              onChange={(e) => setTweak(e.target.value)}
              placeholder="Brief IA (optionnel)"
              className="h-7 px-2 rounded border border-violet-200 bg-white text-[11px] w-48"
              data-testid={`ai-tweak-${field}`}
            />
          )}
          <button
            onClick={() => setShowTweak((v) => !v)}
            className="h-7 w-7 rounded-lg hover:bg-neutral-100 text-neutral-500 flex items-center justify-center text-xs"
            title="Ajouter un brief"
            data-testid={`ai-tweak-toggle-${field}`}
          >+</button>
          <button
            onClick={onGenerate}
            disabled={busy}
            data-testid={`ai-${field}`}
            className="h-7 px-2 rounded-lg bg-violet-600 hover:bg-violet-700 text-white text-[11px] font-medium flex items-center gap-1 disabled:opacity-60"
          >
            {busy ? <ArrowClockwise size={10} className="animate-spin" /> : <Sparkle size={10} weight="fill" />}
            IA
          </button>
        </div>
      </div>
      {children}
    </div>
  );
}

export function Field({ label, children }) {
  return (
    <div>
      <div className="text-[11px] uppercase tracking-widest text-neutral-500 mb-1">{label}</div>
      {children}
    </div>
  );
}

export function ColorPicker({ label, value, onChange }) {
  return (
    <div>
      <div className="text-[11px] uppercase tracking-widest text-neutral-500 mb-1">{label}</div>
      <div className="flex items-center gap-2 h-10 px-2 rounded-lg border border-neutral-200 bg-white">
        <input type="color" value={value} onChange={(e) => onChange(e.target.value)}
          data-testid={`color-${label.toLowerCase()}`}
          className="w-8 h-8 rounded cursor-pointer border-0" />
        <input type="text" value={value} onChange={(e) => onChange(e.target.value)}
          className="flex-1 bg-transparent outline-none text-xs font-mono" />
      </div>
    </div>
  );
}
