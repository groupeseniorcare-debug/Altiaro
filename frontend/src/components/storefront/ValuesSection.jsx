import React from "react";
import { Heart, UsersThree, Lightbulb, HandHeart, Leaf, ShieldCheck } from "@phosphor-icons/react";
import { pickLang } from "../../lib/i18n";

const ICON_POOL = { Heart, UsersThree, Lightbulb, HandHeart, Leaf, ShieldCheck };

/**
 * Values / engagements premium section.
 * Renders 4 pillars with icon + title + description + (optional) metric.
 *
 * Fed by design.values = [{icon, title, description, metric, metric_label}]
 * Falls back to default Altiaro pillars if undefined.
 */
export default function ValuesSection({ values, lang = "fr", design }) {
  const pillars = values?.length
    ? values
    : [
        { icon: "Heart", title: "Conçu avec tendresse", description: "Chaque produit est pensé pour préserver la dignité, l'autonomie et le confort des seniors.", metric: "10+", metric_label: "ans d'expérience" },
        { icon: "UsersThree", title: "L'équipe à votre écoute", description: "Une conseillère répond à chaque appel. Pas de répondeur, pas d'attente — juste un humain qui comprend.", metric: "2h", metric_label: "délai de réponse moyen" },
        { icon: "HandHeart", title: "Installation inclusée", description: "Sur demande, un technicien se déplace pour installer, expliquer et s'assurer que tout fonctionne.", metric: "100%", metric_label: "avec accompagnement" },
        { icon: "Leaf", title: "Production responsable", description: "Nous sélectionnons nos fabricants avec soin. Matériaux durables, circuits courts quand possible.", metric: "15", metric_label: "partenaires audités" },
      ];

  const primary = design?.brand?.primary_color || "#1C1917";
  const accent = design?.brand?.accent_color || "#F5F2EB";
  const fontHeading = design?.brand?.font_heading || "Fraunces";

  return (
    <section className="py-20 md:py-28 px-6" data-testid="storefront-values" style={{ background: accent }}>
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-16">
          <div className="text-[11px] uppercase tracking-[0.2em] text-neutral-500 mb-3">Nos engagements</div>
          <h2 className="text-4xl md:text-5xl mb-4" style={{ fontFamily: `${fontHeading}, serif`, color: "#1C1917" }}>
            Ce qui nous anime
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {pillars.map((p, i) => {
            const Icon = ICON_POOL[p.icon] || Heart;
            const title = pickLang(p.title, lang) || p.title;
            const desc = pickLang(p.description, lang) || p.description;
            return (
              <div key={i} className="bg-white rounded-3xl p-8 md:p-10 hover:shadow-lg transition-shadow duration-500 group"
                   data-testid={`value-${i}`}>
                <div className="flex items-start gap-5">
                  <div className="w-14 h-14 rounded-2xl flex items-center justify-center shrink-0 transition-colors"
                    style={{ background: primary + "15" }}>
                    <Icon size={28} weight="duotone" style={{ color: primary }} />
                  </div>
                  <div className="flex-1">
                    <div className="flex items-start justify-between mb-2">
                      <h3 className="text-xl font-semibold text-neutral-900">{title}</h3>
                      {p.metric && (
                        <div className="text-right shrink-0 ml-4">
                          <div className="text-2xl font-semibold tabular-nums" style={{ color: primary, fontFamily: `${fontHeading}, serif` }}>
                            {p.metric}
                          </div>
                          {p.metric_label && <div className="text-[10px] uppercase tracking-wider text-neutral-500">{p.metric_label}</div>}
                        </div>
                      )}
                    </div>
                    <p className="text-neutral-600 text-[15px] leading-relaxed">{desc}</p>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
