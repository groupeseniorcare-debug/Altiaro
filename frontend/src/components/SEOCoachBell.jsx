import React, { useEffect, useState, useRef } from "react";
import { Bell, Warning, ArrowRight, Sparkle, X } from "@phosphor-icons/react";
import { api, apiCall } from "../lib/api";
import { Link } from "react-router-dom";

/**
 * SEO Coach bell — topbar badge in the site cockpit.
 * Polls /seo/alerts/unread, opens a dropdown of actionable alerts,
 * and marks them as read when opened.
 */
export default function SEOCoachBell({ siteId }) {
  const [summary, setSummary] = useState({ unread_count: 0, max_severity: "none" });
  const [alerts, setAlerts] = useState([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const ref = useRef(null);

  const refreshSummary = async () => {
    const { data } = await apiCall(() => api.get(`/sites/${siteId}/seo/alerts/unread`));
    if (data) setSummary(data);
  };

  useEffect(() => {
    refreshSummary();
    const t = setInterval(refreshSummary, 60_000); // refresh every minute
    return () => clearInterval(t);
  }, [siteId]);

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    const h = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, [open]);

  const handleOpen = async () => {
    const willOpen = !open;
    setOpen(willOpen);
    if (willOpen) {
      setLoading(true);
      const { data } = await apiCall(() => api.get(`/sites/${siteId}/seo/alerts`));
      setLoading(false);
      if (data) setAlerts(data.alerts || []);
      // Mark as read in background (don't block UI)
      apiCall(() => api.post(`/sites/${siteId}/seo/alerts/mark-read`))
        .then(() => setSummary({ unread_count: 0, max_severity: "none" }));
    }
  };

  const count = summary.unread_count || 0;
  const dotColor = summary.max_severity === "critical" ? "#991B1B" : "#0A0A0A";

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={handleOpen}
        data-testid="seo-coach-bell"
        aria-label="Alertes SEO Coach"
        className="relative h-10 w-10 flex items-center justify-center bg-white hover:bg-neutral-100 transition"
        style={{ border: "1px solid #E5E5E5", borderRadius: "2px" }}
      >
        <Bell size={17} weight={count > 0 ? "fill" : "regular"} className="text-neutral-900" />
        {count > 0 && (
          <span
            className="absolute -top-1 -right-1 min-w-[18px] h-[18px] px-1 flex items-center justify-center text-white text-[10px] font-semibold tabular-nums"
            style={{ background: dotColor, borderRadius: "9px" }}
            data-testid="seo-coach-bell-count"
          >
            {count}
          </span>
        )}
      </button>

      {open && (
        <div
          className="absolute right-0 top-12 w-[400px] max-h-[540px] overflow-y-auto bg-white shadow-xl z-50"
          style={{ border: "1px solid #E5E5E5", borderRadius: "2px" }}
          data-testid="seo-coach-dropdown"
        >
          <div className="p-5 flex items-start justify-between gap-3" style={{ borderBottom: "1px solid #E5E5E5" }}>
            <div>
              <div className="flex items-center gap-2 mb-1.5">
                <span className="h-px w-6 bg-neutral-900" />
                <span className="text-[9px] uppercase tracking-[0.35em] font-medium text-neutral-900">
                  Coach SEO
                </span>
              </div>
              <h3 className="text-[18px] leading-[1.2] text-neutral-900" style={{ fontFamily: "'Fraunces', Georgia, serif" }}>
                {alerts.length > 0
                  ? `${alerts.length} recommandation${alerts.length > 1 ? "s" : ""}`
                  : "Tout est en ordre."}
              </h3>
            </div>
            <button onClick={() => setOpen(false)} className="p-1 text-neutral-400 hover:text-neutral-900">
              <X size={16} />
            </button>
          </div>

          {loading ? (
            <div className="p-6 text-center text-[13px] text-neutral-400">Chargement…</div>
          ) : alerts.length === 0 ? (
            <div className="p-8 text-center">
              <Sparkle size={28} weight="duotone" className="mx-auto mb-2 text-neutral-300" />
              <div className="text-[13px] text-neutral-500 leading-snug">
                Pas d'alerte pour cette semaine.<br />
                Vos signaux E-E-A-T sont solides.
              </div>
            </div>
          ) : (
            <ul className="divide-y" style={{ borderColor: "#E5E5E5" }}>
              {alerts.map((a) => {
                const tone =
                  a.severity === "critical" ? { bg: "#FEE2E2", fg: "#991B1B", Icon: Warning }
                  : a.severity === "warn" ? { bg: "#FEF3C7", fg: "#92400E", Icon: Warning }
                  : { bg: "#D1FAE5", fg: "#065F46", Icon: Sparkle };
                return (
                  <li key={a.id} className="p-5" data-testid={`seo-coach-alert-${a.id}`}>
                    <div className="flex items-start gap-3">
                      <span
                        className="shrink-0 w-8 h-8 flex items-center justify-center"
                        style={{ background: tone.bg, color: tone.fg, borderRadius: "2px" }}
                      >
                        <tone.Icon size={14} weight="fill" />
                      </span>
                      <div className="flex-1 min-w-0">
                        <div className="text-[13.5px] font-semibold text-neutral-900 leading-snug">
                          {a.title}
                        </div>
                        <p className="text-[12.5px] text-neutral-600 mt-1 leading-[1.55]">
                          {a.message}
                        </p>
                        <Link
                          to={a.cta_href}
                          className="mt-2.5 inline-flex items-center gap-1.5 text-[11.5px] font-semibold text-neutral-900 hover:underline"
                          onClick={() => setOpen(false)}
                        >
                          {a.cta_label} <ArrowRight size={11} weight="bold" />
                        </Link>
                      </div>
                    </div>
                  </li>
                );
              })}
            </ul>
          )}

          <div className="p-3 text-center bg-[#FAFAFA]" style={{ borderTop: "1px solid #E5E5E5" }}>
            <div className="text-[10px] uppercase tracking-[0.3em] text-neutral-500">
              Digest email · chaque lundi 09h
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
