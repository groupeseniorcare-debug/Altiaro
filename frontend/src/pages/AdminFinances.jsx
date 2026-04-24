import React, { useEffect, useState, useCallback } from "react";
import { api, apiCall } from "../lib/api";
import Layout from "../components/Layout";
import { CurrencyEur, TrendUp, Plus, Spinner } from "@phosphor-icons/react";

const fmt = (n) => new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 }).format(n || 0) + " €";
const nowMonth = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
};

export default function AdminFinances() {
  const [sites, setSites] = useState([]);
  const [selectedSite, setSelectedSite] = useState("");
  const [items, setItems] = useState([]);
  const [form, setForm] = useState({
    month: nowMonth(),
    revenue: 0,
    ad_spend: 0,
    cogs: 0,
    other_costs: 0,
    orders_count: 0,
    notes: "",
  });
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState("");

  // Chargement initial : liste des sites (le `selectedSite` est volontairement
  // exclu des dépendances — on ne veut charger qu'au mount).
  useEffect(() => {
    apiCall(() => api.get("/sites")).then(({ data }) => {
      setSites(data || []);
      if (data?.length && !selectedSite) setSelectedSite(data[0].id);
    });
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const loadItems = useCallback(async (siteId) => {
    if (!siteId) return;
    const { data } = await apiCall(() => api.get(`/sites/${siteId}/financials`));
    setItems(data || []);
  }, []);

  useEffect(() => {
    if (selectedSite) loadItems(selectedSite);
  }, [selectedSite, loadItems]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setMsg("");
    const { data, error } = await apiCall(() =>
      api.post(`/sites/${selectedSite}/financials`, {
        ...form,
        revenue: parseFloat(form.revenue) || 0,
        ad_spend: parseFloat(form.ad_spend) || 0,
        cogs: parseFloat(form.cogs) || 0,
        other_costs: parseFloat(form.other_costs) || 0,
        orders_count: parseInt(form.orders_count) || 0,
      })
    );
    setSaving(false);
    if (error) setMsg(error);
    else {
      setMsg("✓ Enregistré");
      await loadItems(selectedSite);
      setTimeout(() => setMsg(""), 2500);
    }
  };

  const selectedSiteObj = sites.find((s) => s.id === selectedSite);

  return (
    <Layout>
      <div className="p-8 md:p-12 max-w-[1400px]">
        <div className="mb-10 animate-fade-up">
          <div className="text-[11px] uppercase tracking-widest text-neutral-500 mb-2">Performance</div>
          <h1 className="text-3xl font-semibold text-neutral-900">Finances</h1>
          <p className="text-neutral-600 mt-2">
            Saisissez le CA, le spend publicitaire et les coûts produits mensuels par site. Ces données alimentent le tableau de bord global.
          </p>
        </div>

        <div className="mb-6">
          <label className="block text-[13px] font-medium text-neutral-900 mb-1.5">Site</label>
          <select
            value={selectedSite}
            onChange={(e) => setSelectedSite(e.target.value)}
            data-testid="finance-site-select"
            className="h-11 px-4 rounded-xl border border-neutral-200 bg-white min-w-[300px] focus:outline-none focus:ring-2 focus:ring-zinc-500/30"
          >
            {sites.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </div>

        {selectedSite && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-1">
              <div className="bg-white rounded-xl border border-neutral-200 p-6 sticky top-6">
                <h2 className="text-base font-semibold text-neutral-900 mb-1">Nouveau relevé mensuel</h2>
                <p className="text-sm text-neutral-500 mb-5">Réécrit si le mois existe déjà.</p>
                <form onSubmit={handleSubmit} className="space-y-4" data-testid="finance-form">
                  <div>
                    <label className="block text-[12px] font-medium text-neutral-600 mb-1">Mois (YYYY-MM)</label>
                    <input
                      type="month"
                      required
                      value={form.month}
                      onChange={(e) => setForm({ ...form, month: e.target.value })}
                      data-testid="finance-month"
                      className="w-full h-10 px-3 rounded-lg border border-neutral-200 focus:outline-none focus:ring-2 focus:ring-zinc-500/30"
                    />
                  </div>
                  {[
                    ["revenue", "Chiffre d'affaires (€)"],
                    ["ad_spend", "Dépense publicitaire (€)"],
                    ["cogs", "Coût des produits (€)"],
                    ["other_costs", "Autres coûts (€)"],
                    ["orders_count", "Nombre de commandes"],
                  ].map(([key, label]) => (
                    <div key={key}>
                      <label className="block text-[12px] font-medium text-neutral-600 mb-1">{label}</label>
                      <input
                        type="number"
                        step="0.01"
                        value={form[key]}
                        onChange={(e) => setForm({ ...form, [key]: e.target.value })}
                        data-testid={`finance-${key}`}
                        className="w-full h-10 px-3 rounded-lg border border-neutral-200 focus:outline-none focus:ring-2 focus:ring-zinc-500/30"
                      />
                    </div>
                  ))}
                  <button
                    type="submit"
                    disabled={saving}
                    data-testid="finance-submit"
                    className="w-full h-11 rounded-xl bg-neutral-900 hover:bg-neutral-800 text-white font-medium flex items-center justify-center gap-2 disabled:opacity-60 active:scale-[0.98]"
                  >
                    {saving ? <Spinner size={16} className="animate-spin" /> : <Plus size={16} weight="bold" />}
                    Enregistrer
                  </button>
                  {msg && <div className="text-sm text-center" style={{ color: msg.startsWith("✓") ? "#047857" : "#BE123C" }}>{msg}</div>}
                </form>
              </div>
            </div>

            <div className="lg:col-span-2 bg-white rounded-xl border border-neutral-200 overflow-hidden">
              <div className="px-6 py-5 border-b border-neutral-200">
                <h2 className="text-base font-semibold text-neutral-900">
                  Historique — {selectedSiteObj?.name}
                </h2>
              </div>
              {items.length === 0 ? (
                <div className="p-10 text-center text-neutral-500">Aucun relevé saisi pour ce site.</div>
              ) : (
                <table className="w-full">
                  <thead className="bg-white">
                    <tr>
                      <th className="text-left px-6 py-3 text-[11px] uppercase tracking-widest text-neutral-500">Mois</th>
                      <th className="text-right px-6 py-3 text-[11px] uppercase tracking-widest text-neutral-500">CA</th>
                      <th className="text-right px-6 py-3 text-[11px] uppercase tracking-widest text-neutral-500">Pub</th>
                      <th className="text-right px-6 py-3 text-[11px] uppercase tracking-widest text-neutral-500">Coûts</th>
                      <th className="text-right px-6 py-3 text-[11px] uppercase tracking-widest text-neutral-500">Marge</th>
                      <th className="text-right px-6 py-3 text-[11px] uppercase tracking-widest text-neutral-500">ROAS</th>
                    </tr>
                  </thead>
                  <tbody>
                    {items.map((f) => (
                      <tr key={f.month} className="border-t border-neutral-200 hover:bg-white">
                        <td className="px-6 py-3.5 font-mono text-sm text-neutral-900">{f.month}</td>
                        <td className="px-6 py-3.5 text-right">{fmt(f.revenue)}</td>
                        <td className="px-6 py-3.5 text-right">{fmt(f.ad_spend)}</td>
                        <td className="px-6 py-3.5 text-right">{fmt((f.cogs || 0) + (f.other_costs || 0))}</td>
                        <td className="px-6 py-3.5 text-right font-medium text-emerald-400">{fmt(f.margin)}</td>
                        <td className="px-6 py-3.5 text-right font-medium">{f.roas ? `${f.roas}×` : "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        )}
      </div>
    </Layout>
  );
}
