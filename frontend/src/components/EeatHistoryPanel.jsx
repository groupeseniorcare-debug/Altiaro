import React, { useEffect, useState } from "react";
import { api, apiCall } from "../lib/api";
import { TrendUp, TrendDown } from "@phosphor-icons/react";

/**
 * Sparkline hebdomadaire du score E-E-A-T + grille de badges d'achievement.
 * Storytelling dopamine-driven : le Concepteur voit la courbe monter semaine
 * après semaine et débloque des badges à des paliers clés.
 */
export default function EeatHistoryPanel({ siteId }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const { data: res } = await apiCall(() => api.get(`/sites/${siteId}/seo/history`));
      if (!cancelled) {
        setData(res || null);
        setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [siteId]);

  if (loading || !data) return null;
  const { snapshots = [], badges = [], current_score = 0, delta_vs_last_week = 0, weeks_tracked = 0 } = data;

  return (
    <div
      className="p-6 md:p-7"
      style={{ borderTop: "1px solid #E5E5E5" }}
      data-testid="eeat-history-panel"
    >
      <div className="grid grid-cols-1 lg:grid-cols-[1.4fr_1fr] gap-10">
        {/* Left — Sparkline */}
        <div>
          <div className="flex items-start justify-between mb-5 gap-3 flex-wrap">
            <div>
              <div className="text-[10px] uppercase tracking-[0.35em] text-neutral-500 mb-1">
                Historique E-E-A-T · {weeks_tracked} sem.
              </div>
              <div className="flex items-baseline gap-3">
                <div
                  className="text-[36px] md:text-[40px] leading-none text-neutral-900 tabular-nums"
                  style={{ fontFamily: "'Fraunces', Georgia, serif" }}
                >
                  {current_score}
                </div>
                {delta_vs_last_week !== 0 && (
                  <div
                    className="flex items-center gap-1 text-[12px] font-semibold"
                    style={{ color: delta_vs_last_week > 0 ? "#047857" : "#B91C1C" }}
                  >
                    {delta_vs_last_week > 0 ? <TrendUp size={13} weight="bold" /> : <TrendDown size={13} weight="bold" />}
                    {delta_vs_last_week > 0 ? "+" : ""}{delta_vs_last_week} pt
                  </div>
                )}
              </div>
            </div>
          </div>
          <Sparkline snapshots={snapshots} />
          {snapshots.length >= 2 && (
            <div className="flex items-center justify-between mt-3 text-[10px] uppercase tracking-[0.25em] text-neutral-400">
              <span>{snapshots[0]?.week}</span>
              <span>{snapshots[snapshots.length - 1]?.week}</span>
            </div>
          )}
        </div>

        {/* Right — Badges */}
        <div data-testid="eeat-badges">
          <div className="text-[10px] uppercase tracking-[0.35em] text-neutral-500 mb-4">
            Badges débloqués · {badges.length}
          </div>
          {badges.length === 0 ? (
            <div className="text-[12.5px] text-neutral-500 leading-relaxed">
              Vos premiers badges arrivent quand vous publierez votre premier
              cluster ou quand votre score dépassera 75.
            </div>
          ) : (
            <ul className="space-y-2.5">
              {badges.slice(0, 6).map((b) => (
                <li
                  key={b.id}
                  className="flex items-start gap-3 p-3"
                  style={{ background: "#F5F5F5", borderRadius: "2px" }}
                  data-testid={`eeat-badge-${b.id}`}
                >
                  <span className="text-xl shrink-0">{b.icon || "🏅"}</span>
                  <div className="flex-1 min-w-0">
                    <div className="text-[12.5px] font-semibold text-neutral-900 leading-snug">
                      {b.title}
                    </div>
                    <div className="text-[11px] text-neutral-600 mt-0.5 leading-[1.5]">
                      {b.description}
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}

/**
 * Tiny zero-dep SVG sparkline — editorial style (line + area fill + end dot).
 */
function Sparkline({ snapshots }) {
  const values = (snapshots || []).map((s) => Number(s.avg_eeat_score) || 0);
  if (values.length === 0) {
    return <div className="h-[88px] flex items-center text-[12px] text-neutral-400">Aucune donnée.</div>;
  }
  // If only 1 datapoint, duplicate it so the line is visible
  const points = values.length === 1 ? [values[0], values[0]] : values;

  const width = 520;
  const height = 88;
  const padX = 4;
  const padY = 6;
  const maxVal = 100;
  const minVal = 0;
  const stepX = (width - 2 * padX) / Math.max(1, points.length - 1);
  const mapY = (v) => height - padY - ((v - minVal) / (maxVal - minVal)) * (height - 2 * padY);

  const coords = points.map((v, i) => [padX + i * stepX, mapY(v)]);
  const path = coords.map(([x, y], i) => `${i === 0 ? "M" : "L"} ${x.toFixed(1)} ${y.toFixed(1)}`).join(" ");
  const areaPath = `${path} L ${coords[coords.length - 1][0]} ${height - padY} L ${coords[0][0]} ${height - padY} Z`;
  const lastX = coords[coords.length - 1][0];
  const lastY = coords[coords.length - 1][1];

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-[96px]" preserveAspectRatio="none">
      {/* Dashed baseline at 75 (target "professional" threshold) */}
      <line
        x1={padX}
        x2={width - padX}
        y1={mapY(75)}
        y2={mapY(75)}
        stroke="#D4D4D4"
        strokeDasharray="3 3"
        strokeWidth="1"
      />
      <path d={areaPath} fill="#0A0A0A" opacity="0.06" />
      <path d={path} fill="none" stroke="#0A0A0A" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
      {/* End dot */}
      <circle cx={lastX} cy={lastY} r="4" fill="#0A0A0A" />
      <circle cx={lastX} cy={lastY} r="8" fill="#0A0A0A" opacity="0.12" />
    </svg>
  );
}
