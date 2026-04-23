import React, { useEffect, useState } from "react";
import {
  DndContext, closestCenter, KeyboardSensor, PointerSensor,
  useSensor, useSensors,
} from "@dnd-kit/core";
import {
  arrayMove, SortableContext, sortableKeyboardCoordinates,
  useSortable, verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import {
  DotsSixVertical, Eye, EyeSlash, Sparkle, CheckCircle, ArrowClockwise,
  Lightning, BookOpen, Target, Stack,
} from "@phosphor-icons/react";
import { api, apiCall } from "../lib/api";

/**
 * Drag-and-drop page builder for homepage sections.
 * - Réordonner les sections par drag
 * - Activer / masquer chaque section (checkbox)
 * - Presets : minimaliste / éditorial / conversion-first / full
 * - Persisté sur PUT /api/sites/{id}/design/homepage-sections
 */

const PRESET_META = {
  minimal:    { label: "Minimaliste",      icon: Target,    desc: "5 sections. Droit au but." },
  editorial:  { label: "Éditorial",        icon: BookOpen,  desc: "Storytelling premium." },
  conversion: { label: "Conversion-first", icon: Lightning, desc: "Social proof + trust." },
  full:       { label: "Complète",         icon: Stack,     desc: "Toutes les sections." },
};

export default function HomepageSectionsEditor({ siteId, onChange }) {
  const [sections, setSections] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [dirty, setDirty] = useState(false);

  const load = async () => {
    const { data } = await apiCall(() => api.get(`/sites/${siteId}/design/homepage-sections`));
    if (data?.sections) setSections(data.sections);
    setLoading(false);
    setDirty(false);
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [siteId]);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  const handleDragEnd = (evt) => {
    const { active, over } = evt;
    if (!over || active.id === over.id) return;
    const oldIdx = sections.findIndex((s) => s.key === active.id);
    const newIdx = sections.findIndex((s) => s.key === over.id);
    setSections((prev) => arrayMove(prev, oldIdx, newIdx));
    setDirty(true);
  };

  const toggleVisible = (key) => {
    setSections((prev) => prev.map((s) => (s.key === key ? { ...s, visible: !s.visible } : s)));
    setDirty(true);
  };

  const save = async () => {
    setSaving(true);
    const { error } = await apiCall(() =>
      api.put(`/sites/${siteId}/design/homepage-sections`,
              { sections: sections.map(({ key, visible }) => ({ key, visible })) })
    );
    setSaving(false);
    if (error) { window.alert(error); return; }
    setDirty(false);
    onChange?.();
  };

  const applyPreset = async (preset) => {
    if (!window.confirm(`Appliquer le preset « ${PRESET_META[preset].label} » ? Tes choix actuels seront écrasés.`)) return;
    setSaving(true);
    const { data, error } = await apiCall(() =>
      api.post(`/sites/${siteId}/design/homepage-sections/preset/${preset}`, {})
    );
    setSaving(false);
    if (error) { window.alert(error); return; }
    if (data?.sections) {
      // Refresh full from backend (with labels)
      await load();
    }
    onChange?.();
  };

  const visibleCount = sections.filter((s) => s.visible).length;

  if (loading) {
    return (
      <div className="bg-white border border-neutral-200 rounded-2xl p-6 text-sm text-neutral-400">
        Chargement des sections…
      </div>
    );
  }

  return (
    <div className="space-y-4" data-testid="homepage-sections-editor">
      {/* Intro */}
      <div className="bg-gradient-to-br from-violet-50 to-indigo-50 border border-violet-200 rounded-2xl p-5">
        <div className="flex items-start gap-3 flex-wrap">
          <div className="w-10 h-10 rounded-xl bg-violet-600 flex items-center justify-center shrink-0">
            <Stack size={18} weight="fill" className="text-white" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-sm font-semibold text-violet-900">Page Builder — sections homepage</div>
            <div className="text-xs text-violet-800/80 mt-0.5">
              Active / masque / réorganise les sections. Glisse ↕ pour déplacer.
              Une section masquée ne s'affichera jamais — même si tu lui mets du contenu.
            </div>
          </div>
          <div className="text-xs font-medium text-violet-900 bg-white/60 rounded-lg px-3 py-1.5 whitespace-nowrap">
            {visibleCount} / {sections.length} visibles
          </div>
        </div>
      </div>

      {/* Presets */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
        {Object.entries(PRESET_META).map(([key, meta]) => {
          const Icon = meta.icon;
          return (
            <button
              key={key}
              onClick={() => applyPreset(key)}
              disabled={saving}
              data-testid={`preset-${key}`}
              className="group text-left bg-white border border-neutral-200 hover:border-neutral-900 rounded-xl p-3 transition disabled:opacity-60"
            >
              <div className="w-8 h-8 rounded-lg bg-neutral-100 group-hover:bg-neutral-900 group-hover:text-white flex items-center justify-center mb-2 transition">
                <Icon size={14} weight="fill" />
              </div>
              <div className="text-xs font-semibold text-neutral-900">{meta.label}</div>
              <div className="text-[11px] text-neutral-500 mt-0.5 leading-snug">{meta.desc}</div>
            </button>
          );
        })}
      </div>

      {/* Sortable list */}
      <div className="bg-white border border-neutral-200 rounded-2xl p-2">
        <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
          <SortableContext items={sections.map((s) => s.key)} strategy={verticalListSortingStrategy}>
            {sections.map((s, i) => (
              <SortableRow key={s.key} section={s} index={i} onToggle={() => toggleVisible(s.key)} />
            ))}
          </SortableContext>
        </DndContext>
      </div>

      {/* Save bar */}
      <div className={`sticky bottom-4 rounded-2xl p-4 flex items-center justify-between gap-3 shadow-xl z-30 transition ${
        dirty ? "bg-neutral-900 text-white" : "bg-white border border-neutral-200 text-neutral-500"
      }`}>
        <div className="text-sm flex items-center gap-2">
          {dirty ? (
            <>
              <Sparkle size={14} weight="fill" />
              Modifications non enregistrées.
            </>
          ) : (
            <>
              <CheckCircle size={14} weight="fill" className="text-emerald-500" />
              Tout est à jour.
            </>
          )}
        </div>
        <button
          onClick={save}
          disabled={saving || !dirty}
          data-testid="save-homepage-sections"
          className="h-10 px-5 rounded-lg bg-white text-neutral-900 hover:bg-neutral-100 disabled:opacity-50 text-sm font-semibold flex items-center gap-2 border border-neutral-200"
        >
          {saving ? <ArrowClockwise size={14} className="animate-spin" /> : <CheckCircle size={14} weight="fill" />}
          {saving ? "Enregistrement…" : "Enregistrer l'ordre"}
        </button>
      </div>
    </div>
  );
}

// ---- sortable row ----
function SortableRow({ section, index, onToggle }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: section.key });
  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };
  return (
    <div
      ref={setNodeRef}
      style={style}
      data-testid={`section-row-${section.key}`}
      className={`flex items-center gap-2 p-3 rounded-xl ${
        section.visible ? "bg-white" : "bg-neutral-50"
      } ${isDragging ? "ring-2 ring-violet-400" : ""}`}
    >
      <button
        {...attributes}
        {...listeners}
        data-testid={`drag-${section.key}`}
        className="w-8 h-8 rounded hover:bg-neutral-100 text-neutral-400 flex items-center justify-center cursor-grab active:cursor-grabbing"
        aria-label="Déplacer la section"
      >
        <DotsSixVertical size={16} />
      </button>
      <div className="w-7 h-7 rounded-full bg-neutral-100 flex items-center justify-center text-[11px] font-semibold text-neutral-600 shrink-0">
        {index + 1}
      </div>
      <div className="flex-1 min-w-0">
        <div className={`text-sm font-medium truncate ${section.visible ? "text-neutral-900" : "text-neutral-400"}`}>
          {section.label}
        </div>
        <div className="text-[11px] text-neutral-400 font-mono">{section.key}</div>
      </div>
      <button
        onClick={onToggle}
        data-testid={`toggle-${section.key}`}
        className={`w-9 h-9 rounded-lg flex items-center justify-center transition ${
          section.visible
            ? "bg-emerald-50 text-emerald-600 hover:bg-emerald-100"
            : "bg-neutral-100 text-neutral-400 hover:bg-neutral-200"
        }`}
        aria-label={section.visible ? "Masquer la section" : "Afficher la section"}
        title={section.visible ? "Masquer" : "Afficher"}
      >
        {section.visible ? <Eye size={14} weight="bold" /> : <EyeSlash size={14} weight="bold" />}
      </button>
    </div>
  );
}
