import React from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft, Package } from "@phosphor-icons/react";
import SourcingPanel from "../components/SourcingPanel";
import { useStepGuard } from "../lib/useStepGuard";

export default function Sourcing() {
  const { id: siteId } = useParams();
  const { allowed, checking } = useStepGuard(siteId, "import");

  if (checking) {
    return (
      <div className="min-h-screen bg-[#FAF7F2] flex items-center justify-center">
        <div className="text-sm text-neutral-500">Vérification des prérequis…</div>
      </div>
    );
  }
  if (!allowed) return null;

  return (
    <div className="min-h-screen bg-[#FAF7F2]">
      <div className="max-w-[1600px] mx-auto px-6 md:px-10 py-8">
        <Link
          to={`/sites/${siteId}`}
          className="inline-flex items-center gap-2 text-sm text-neutral-600 hover:text-neutral-900 mb-6"
          data-testid="back-to-site"
        >
          <ArrowLeft size={14} /> Retour au cockpit
        </Link>

        <div className="mb-8">
          <div className="text-[11px] uppercase tracking-[0.2em] text-neutral-500 mb-2 flex items-center gap-2">
            <Package size={12} weight="bold" /> Étape 2 · Import du catalogue
          </div>
          <h1 className="text-3xl md:text-4xl font-semibold text-neutral-900" style={{ fontFamily: "'Fraunces', serif" }}>
            Sourcing fournisseurs
          </h1>
          <p className="text-sm text-neutral-500 mt-2 max-w-2xl">
            Recherche sur <strong>CJ Dropshipping</strong> et <strong>AliExpress</strong>, ou importe par URL.
          </p>
        </div>

        <SourcingPanel siteId={siteId} context="catalog" />
      </div>
    </div>
  );
}
