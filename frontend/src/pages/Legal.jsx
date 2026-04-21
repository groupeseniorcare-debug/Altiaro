import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { AltioraLogo } from "../components/AltioraLogo";

function MarkdownLegal({ md }) {
  if (!md) return null;
  // Lightweight markdown: ##, ###, **, tables, lists, paragraphs.
  // Tables use simple pipe-syntax.
  const renderBlock = (block) => {
    const b = block.trim();
    if (!b) return "";
    if (b.startsWith("### ")) return `<h3 class="text-lg font-semibold mt-8 mb-3 text-neutral-900">${b.slice(4)}</h3>`;
    if (b.startsWith("## ")) return `<h2 class="text-2xl font-semibold mt-12 mb-4 text-neutral-900">${b.slice(3)}</h2>`;
    if (b.startsWith("# ")) return `<h1 class="text-3xl font-semibold mt-2 mb-5 text-neutral-900">${b.slice(2)}</h1>`;
    // Table (| a | b |\n| - | - |\n| x | y |)
    if (b.includes("|") && b.split("\n")[1]?.includes("---")) {
      const lines = b.split("\n").filter((l) => l.trim());
      const cells = lines.map((l) => l.split("|").map((c) => c.trim()).filter((c, i, arr) => !(c === "" && (i === 0 || i === arr.length - 1))));
      const header = cells[0];
      const rows = cells.slice(2);
      const th = header.map((c) => `<th class="text-left font-semibold py-2 px-3 border-b border-neutral-200 text-sm">${c}</th>`).join("");
      const tr = rows.map((r) => `<tr>${r.map((c) => `<td class="py-2 px-3 border-b border-neutral-100 text-sm text-neutral-700">${c}</td>`).join("")}</tr>`).join("");
      return `<div class="overflow-x-auto my-6"><table class="w-full"><thead><tr>${th}</tr></thead><tbody>${tr}</tbody></table></div>`;
    }
    if (b.startsWith("- ")) {
      const items = b.split("\n").map((l) => `<li class="leading-relaxed">${l.replace(/^- /, "")}</li>`).join("");
      return `<ul class="list-disc pl-6 space-y-2 my-4 text-neutral-700">${items}</ul>`;
    }
    return `<p class="leading-relaxed my-4 text-neutral-700">${b.replace(/\n/g, "<br/>")}</p>`;
  };
  const html = md
    .split("\n\n")
    .map(renderBlock)
    .join("")
    .replace(/\*\*(.+?)\*\*/g, '<strong class="text-neutral-900 font-semibold">$1</strong>');
  return (
    <div
      className="markdown-body max-w-none text-[15px]"
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}

/**
 * Public legal page (Mentions légales / CGU / Confidentialité / Cookies).
 * No auth required — discoverable by Google, Mollie reviewers, etc.
 */
export default function Legal({ slug }) {
  const [page, setPage] = useState(null);
  const [err, setErr] = useState(null);

  useEffect(() => {
    api
      .get(`/platform/legal/${slug}`)
      .then((r) => setPage(r.data))
      .catch(() => setErr("Page introuvable"));
    document.title = `Altiora · ${slug}`;
  }, [slug]);

  return (
    <div className="min-h-screen bg-white text-neutral-900">
      {/* Nav */}
      <nav className="border-b border-neutral-200 bg-white/80 backdrop-blur sticky top-0 z-20">
        <div className="max-w-5xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2" data-testid="legal-home-link">
            <AltioraLogo variant="horizontal" size={22} color="#0A0A0A" />
          </Link>
          <Link
            to="/login"
            className="text-sm font-medium text-neutral-700 hover:text-neutral-900"
            data-testid="legal-login-link"
          >
            Accès Concepteur →
          </Link>
        </div>
      </nav>

      <main className="max-w-3xl mx-auto px-6 py-16" data-testid={`legal-page-${slug}`}>
        {err ? (
          <div className="text-neutral-500">{err}</div>
        ) : page ? (
          <>
            <div className="text-[11px] uppercase tracking-widest text-neutral-500 mb-3">
              Mis à jour le {page.updated}
            </div>
            <h1 className="text-4xl sm:text-5xl font-semibold tracking-tight mb-10">
              {page.title}
            </h1>
            <MarkdownLegal md={page.content} />
          </>
        ) : (
          <div className="text-neutral-500">Chargement…</div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-neutral-200 mt-24">
        <div className="max-w-5xl mx-auto px-6 py-10 flex flex-wrap gap-x-8 gap-y-3 items-center justify-between text-sm text-neutral-500">
          <div>© {new Date().getFullYear()} Altiora — Tous droits réservés</div>
          <div className="flex flex-wrap gap-x-6 gap-y-2">
            <Link to="/mentions-legales" className="hover:text-neutral-900">
              Mentions légales
            </Link>
            <Link to="/cgu" className="hover:text-neutral-900">
              CGU
            </Link>
            <Link to="/confidentialite" className="hover:text-neutral-900">
              Confidentialité
            </Link>
            <Link to="/cookies" className="hover:text-neutral-900">
              Cookies
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
