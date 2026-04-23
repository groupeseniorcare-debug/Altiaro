/**
 * Sanitize brand text fields that may contain Markdown or full Claude explanations
 * (legacy data from before the backend sanitizer was added). Takes the first bolded
 * token (** x **) or the first clean line, strips markdown chars, guillemets and
 * common French preambles ("Voici…", "# Proposition de…").
 *
 * Used defensively in the storefront so a broken DB row doesn't render as
 * "# Proposition de nom de marque\n\n**Soléa**\n\n…" inside an <h1>.
 */
const PREAMBLE_RE = /^\s*(?:voici|proposition(?:s)?\s+de\s+\w+|suggestion(?:s)?(?:\s+de)?|mon\s+choix|je\s+propose|nom\s+(?:de\s+)?(?:marque|choisi)\s*:?|baseline\s*:?|tagline\s*:?|ton\s+de\s+voix\s*:?|histoire\s*:?|le\s+nom\s+(?:est|serait)?\s*:?)\s*[:\-–—]?\s*/i;

export function sanitizeBrandText(raw, maxLen = 80) {
  if (!raw) return "";
  let text = String(raw).trim();
  const bold = text.match(/\*\*([^*\n]{1,80})\*\*/);
  if (bold) {
    text = bold[1].trim();
  } else {
    // Drop markdown headings, blockquotes, code fences
    text = text
      .replace(/^\s*#{1,6}\s+.*$/gm, "")
      .replace(/^\s*>\s*/gm, "")
      .replace(/```[^`]*```/gs, "");
    // First non-empty line
    for (const line of text.split(/\r?\n/)) {
      const l = line.trim();
      if (l) { text = l; break; }
    }
  }
  text = text
    .replace(/[*_`#>]+/g, "")
    .trim()
    .replace(/^["'«»“”‘’]+|["'«»“”‘’]+$/g, "")
    .trim()
    .replace(PREAMBLE_RE, "")
    .trim()
    .replace(/[.,:; ]+$/, "");
  if (text.length > maxLen) {
    text = text.slice(0, maxLen).replace(/\s+\S*$/, "").trim();
  }
  return text;
}
