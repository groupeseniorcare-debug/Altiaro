import React, { useEffect, useState } from "react";
import { api, apiCall } from "../lib/api";
import { useAuth } from "../lib/auth";
import Layout from "../components/Layout";
import { Plus, Trash, UserCircle, Spinner } from "@phosphor-icons/react";

export default function Users() {
  const { user: me } = useAuth();
  const [users, setUsers] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ email: "", password: "", name: "", role: "operator" });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const load = async () => {
    const { data } = await apiCall(() => api.get("/users"));
    setUsers(data || []);
  };

  useEffect(() => {
    load();
  }, []);

  const handleCreate = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError("");
    const { error: err } = await apiCall(() => api.post("/users", form));
    setSaving(false);
    if (err) setError(err);
    else {
      setForm({ email: "", password: "", name: "", role: "operator" });
      setShowForm(false);
      load();
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm("Supprimer cet utilisateur ?")) return;
    await apiCall(() => api.delete(`/users/${id}`));
    load();
  };

  return (
    <Layout>
      <div className="p-8 md:p-12 max-w-[1000px]">
        <div className="flex items-start justify-between mb-10 animate-fade-up">
          <div>
            <div className="text-[11px] uppercase tracking-widest text-[#78716C] mb-2">Collaborateurs</div>
            <h1 className="font-heading text-4xl font-semibold text-[#1C1917]">Équipe</h1>
            <p className="text-[#57534E] mt-2">Ajoutez des opérateurs et administrateurs au cockpit.</p>
          </div>
          <button
            onClick={() => setShowForm(!showForm)}
            data-testid="toggle-new-user"
            className="h-11 px-5 rounded-xl bg-[#B84B31] hover:bg-[#993D26] text-white font-medium transition flex items-center gap-2 active:scale-[0.98]"
          >
            <Plus size={18} weight="bold" /> Nouvel utilisateur
          </button>
        </div>

        {showForm && (
          <form
            onSubmit={handleCreate}
            className="bg-white rounded-xl border border-[#E7E5E4] p-6 mb-8 grid grid-cols-1 md:grid-cols-2 gap-4"
            data-testid="new-user-form"
          >
            <div>
              <label className="block text-[13px] font-medium text-[#1C1917] mb-1.5">Nom</label>
              <input
                required
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                data-testid="new-user-name"
                className="w-full h-11 px-4 rounded-lg border border-[#E7E5E4] focus:outline-none focus:ring-2 focus:ring-[#B84B31]/30"
              />
            </div>
            <div>
              <label className="block text-[13px] font-medium text-[#1C1917] mb-1.5">Email</label>
              <input
                required
                type="email"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                data-testid="new-user-email"
                className="w-full h-11 px-4 rounded-lg border border-[#E7E5E4] focus:outline-none focus:ring-2 focus:ring-[#B84B31]/30"
              />
            </div>
            <div>
              <label className="block text-[13px] font-medium text-[#1C1917] mb-1.5">Mot de passe</label>
              <input
                required
                type="text"
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
                data-testid="new-user-password"
                className="w-full h-11 px-4 rounded-lg border border-[#E7E5E4] font-mono focus:outline-none focus:ring-2 focus:ring-[#B84B31]/30"
                placeholder="min 8 caractères"
              />
            </div>
            <div>
              <label className="block text-[13px] font-medium text-[#1C1917] mb-1.5">Rôle</label>
              <select
                value={form.role}
                onChange={(e) => setForm({ ...form, role: e.target.value })}
                data-testid="new-user-role"
                className="w-full h-11 px-4 rounded-lg border border-[#E7E5E4] focus:outline-none focus:ring-2 focus:ring-[#B84B31]/30"
              >
                <option value="operator">Opérateur</option>
                <option value="admin">Administrateur</option>
              </select>
            </div>
            {error && (
              <div className="md:col-span-2 p-3 rounded-lg bg-[#FFE4E6] text-[#BE123C] text-sm">{error}</div>
            )}
            <div className="md:col-span-2 flex justify-end gap-3">
              <button
                type="button"
                onClick={() => setShowForm(false)}
                className="h-11 px-5 rounded-xl border border-[#E7E5E4] text-[#57534E] hover:bg-[#FDFBF7]"
              >
                Annuler
              </button>
              <button
                type="submit"
                disabled={saving}
                data-testid="new-user-submit"
                className="h-11 px-5 rounded-xl bg-[#B84B31] hover:bg-[#993D26] text-white font-medium flex items-center gap-2 disabled:opacity-60"
              >
                {saving ? <Spinner size={16} className="animate-spin" /> : null}
                Créer
              </button>
            </div>
          </form>
        )}

        <div className="bg-white rounded-xl border border-[#E7E5E4] overflow-hidden">
          <table className="w-full">
            <thead className="bg-[#FDFBF7]">
              <tr>
                <th className="text-left px-6 py-3 text-[11px] uppercase tracking-widest text-[#78716C]">Nom</th>
                <th className="text-left px-6 py-3 text-[11px] uppercase tracking-widest text-[#78716C]">Email</th>
                <th className="text-left px-6 py-3 text-[11px] uppercase tracking-widest text-[#78716C]">Rôle</th>
                <th className="text-right px-6 py-3 text-[11px] uppercase tracking-widest text-[#78716C]">Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} className="border-t border-[#E7E5E4] hover:bg-[#FDFBF7]">
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div className="w-9 h-9 rounded-full bg-[#B84B31] text-white flex items-center justify-center font-heading font-semibold text-sm">
                        {u.name?.[0]?.toUpperCase() || "?"}
                      </div>
                      <span className="font-medium text-[#1C1917]">{u.name}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4 text-[#57534E]">{u.email}</td>
                  <td className="px-6 py-4">
                    <span
                      className={`text-[11px] uppercase tracking-widest px-2.5 py-1 rounded-full ${
                        u.role === "admin" ? "bg-[#B84B31]/10 text-[#B84B31]" : "bg-[#F5F2EB] text-[#78716C]"
                      }`}
                    >
                      {u.role}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-right">
                    {u.id !== me?.id && (
                      <button
                        onClick={() => handleDelete(u.id)}
                        data-testid={`delete-user-${u.id}`}
                        className="p-2 rounded-lg text-[#BE123C] hover:bg-[#FFE4E6] transition"
                      >
                        <Trash size={16} />
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </Layout>
  );
}
