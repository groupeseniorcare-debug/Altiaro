import React from "react";

/**
 * Tiny shared form helpers for the storefront Checkout / Confirmation pages.
 * Extracted from `pages/Storefront.jsx` in Phase 4 refactor (April 2026).
 */

export function Card({ title, children }) {
  return (
    <div className="bg-white rounded-2xl border border-[#E7E5E4] p-6 space-y-4">
      <div className="font-heading text-lg font-semibold text-[#1C1917]">{title}</div>
      {children}
    </div>
  );
}

export function Field({ label, name, type = "text", value, onChange, required }) {
  return (
    <div>
      <label className="block text-[13px] font-medium text-[#1C1917] mb-1.5">{label}</label>
      <input
        name={name}
        type={type}
        value={value}
        onChange={onChange}
        required={required}
        data-testid={`field-${name}`}
        className="w-full h-12 px-4 rounded-xl border border-[#E7E5E4] bg-white focus:ring-2 focus:ring-[#B84B31]/30 focus:border-[#B84B31] outline-none"
      />
    </div>
  );
}

export function Row({ label, value }) {
  return (
    <div className="flex items-center justify-between text-sm">
      <span className="text-[#57534E]">{label}</span>
      <span className="text-[#1C1917]">{value}</span>
    </div>
  );
}
