import React from "react";

/**
 * Altiora wordmark + icon logo.
 * Defaults to horizontal layout (icon + text).
 * Pure CSS/SVG — no image fetch, guaranteed crisp at any size.
 */
export function AltioraLogo({
  size = 24,
  variant = "horizontal", // "horizontal" | "icon-only" | "wordmark-only"
  color = "currentColor",
  className = "",
}) {
  const iconSize = size;
  const fontSize = size * 0.72;

  const Icon = (
    <svg
      width={iconSize}
      height={iconSize}
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      {/* Left stroke of the A */}
      <path d="M4 28 L14 4 L18 4 L28 28 L24 28 L21.2 21 L10.8 21 L8 28 Z" fill={color} />
      {/* Up-arrow in the negative space */}
      <path d="M16 8 L20 14 L17 14 L17 19 L15 19 L15 14 L12 14 Z" fill={color} />
    </svg>
  );

  if (variant === "icon-only") {
    return <span className={className}>{Icon}</span>;
  }

  const Word = (
    <span
      style={{
        fontSize: `${fontSize}px`,
        fontWeight: 600,
        letterSpacing: "0.09em",
        color,
        fontFamily: "'Inter', system-ui, sans-serif",
        lineHeight: 1,
      }}
    >
      ALTIORA
    </span>
  );

  if (variant === "wordmark-only") {
    return <span className={className}>{Word}</span>;
  }

  return (
    <span className={`inline-flex items-center gap-2 ${className}`}>
      {Icon}
      {Word}
    </span>
  );
}
