import React, { useState, useEffect, useRef } from "react";
import { api, apiCall } from "../lib/api";
import {
  ChatCircleDots,
  X as XIcon,
  PaperPlaneTilt,
  Sparkle,
  Robot,
  User,
  Wrench,
  Trash,
  Plus,
  ArrowClockwise,
  CaretDown,
} from "@phosphor-icons/react";

const STORAGE_KEY = "cf_copilot_session_id";

const SUGGESTIONS = [
  "Liste mes sites",
  "Combien de commandes ce mois ?",
  "Cherche mes sites qui contiennent 'confort'",
  "Ma meilleure famille scalée",
];

export default function CopilotFab({ user }) {
  const [open, setOpen] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [sessions, setSessions] = useState([]);
  const [showSessions, setShowSessions] = useState(false);
  const scrollRef = useRef(null);

  // Load last session id from localStorage
  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) setSessionId(saved);
  }, []);

  // Fetch messages when session changes
  useEffect(() => {
    if (!sessionId || !open) return;
    (async () => {
      const { data } = await apiCall(() => api.get(`/copilot/sessions/${sessionId}`));
      if (data?.messages) setMessages(data.messages);
    })();
  }, [sessionId, open]);

  // Fetch session list when opened
  useEffect(() => {
    if (!open) return;
    (async () => {
      const { data } = await apiCall(() => api.get("/copilot/sessions"));
      if (data) setSessions(data);
    })();
  }, [open, sessionId, busy]);

  // Auto-scroll on new message
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, busy]);

  const send = async (text) => {
    const msg = (text ?? input).trim();
    if (!msg || busy) return;
    setInput("");
    // Optimistic UI
    setMessages((prev) => [
      ...prev,
      { role: "user", content: msg, ts: new Date().toISOString() },
    ]);
    setBusy(true);
    const { data, error } = await apiCall(() =>
      api.post("/copilot/chat", { session_id: sessionId, message: msg })
    );
    setBusy(false);
    if (error) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant_final", content: `⚠️ ${error}`, ts: new Date().toISOString() },
      ]);
      return;
    }
    if (!sessionId) {
      setSessionId(data.session_id);
      localStorage.setItem(STORAGE_KEY, data.session_id);
    }
    setMessages((prev) => [
      ...prev,
      {
        role: "assistant_final",
        content: data.final_answer,
        tool_trace: data.tool_trace,
        ts: new Date().toISOString(),
      },
    ]);
  };

  const newSession = () => {
    setSessionId(null);
    setMessages([]);
    setShowSessions(false);
    localStorage.removeItem(STORAGE_KEY);
  };

  const loadSession = async (sid) => {
    setSessionId(sid);
    localStorage.setItem(STORAGE_KEY, sid);
    setShowSessions(false);
  };

  const deleteSession = async (sid, e) => {
    e?.stopPropagation();
    if (!window.confirm("Supprimer cette conversation ?")) return;
    await apiCall(() => api.delete(`/copilot/sessions/${sid}`));
    setSessions((prev) => prev.filter((s) => s.session_id !== sid));
    if (sid === sessionId) newSession();
  };

  const onKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  return (
    <>
      {/* Floating button */}
      {!open && (
        <button
          onClick={() => setOpen(true)}
          data-testid="copilot-fab"
          className="fixed bottom-20 right-6 z-[60] h-14 px-5 rounded-full bg-gradient-to-br from-[#1C1917] to-[#44403C] text-white shadow-xl hover:shadow-2xl hover:scale-105 transition-all flex items-center gap-2.5 active:scale-95"
          aria-label="Ouvrir le Copilot IA"
        >
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-[#B84B31] to-[#D97706] flex items-center justify-center">
            <Sparkle size={16} weight="fill" />
          </div>
          <span className="font-medium text-sm">Copilot IA</span>
        </button>
      )}

      {/* Slide-over panel */}
      {open && (
        <div className="fixed inset-0 z-[55] pointer-events-none">
          <div className="absolute inset-0 bg-black/30 pointer-events-auto" onClick={() => setOpen(false)} />
          <div
            className="absolute top-0 right-0 bottom-0 w-full max-w-md bg-zinc-950 shadow-2xl pointer-events-auto flex flex-col"
            style={{ animation: "cfSlideInRight 0.25s cubic-bezier(0.16, 1, 0.3, 1)" }}
            data-testid="copilot-panel"
          >
            {/* Header */}
            <div className="flex items-center gap-3 px-5 py-4 border-b border-zinc-800">
              <div className="w-9 h-9 rounded-full bg-gradient-to-br from-[#B84B31] to-[#D97706] flex items-center justify-center">
                <Sparkle size={16} weight="fill" className="text-white" />
              </div>
              <div className="flex-1 min-w-0">
                <h2 className="font-heading text-base font-semibold text-zinc-100">
                  Concept Copilot
                </h2>
                <p className="text-[11px] text-zinc-500">
                  Claude 4.5 · {messages.length > 0 ? `${messages.length} msgs` : "Prêt à aider"}
                </p>
              </div>
              <button
                onClick={() => setShowSessions((s) => !s)}
                data-testid="copilot-sessions-toggle"
                title="Historique"
                className="w-8 h-8 rounded-lg hover:bg-zinc-800 flex items-center justify-center"
              >
                <CaretDown size={14} className={showSessions ? "rotate-180" : ""} />
              </button>
              <button
                onClick={newSession}
                data-testid="copilot-new"
                title="Nouvelle conversation"
                className="w-8 h-8 rounded-lg hover:bg-zinc-800 flex items-center justify-center"
              >
                <Plus size={14} />
              </button>
              <button
                onClick={() => setOpen(false)}
                data-testid="copilot-close"
                className="w-8 h-8 rounded-lg hover:bg-zinc-800 flex items-center justify-center"
              >
                <XIcon size={14} />
              </button>
            </div>

            {/* Sessions dropdown */}
            {showSessions && (
              <div className="border-b border-zinc-800 bg-zinc-900/40 p-3 max-h-56 overflow-y-auto">
                {sessions.length === 0 ? (
                  <div className="text-xs text-zinc-500 text-center py-4">
                    Aucune conversation précédente.
                  </div>
                ) : (
                  sessions.map((s) => (
                    <div
                      key={s.session_id}
                      className={`w-full p-2 rounded-lg mb-1 flex items-start gap-2 transition ${
                        s.session_id === sessionId ? "bg-zinc-950 border border-[#B84B31]/30" : "hover:bg-zinc-950"
                      }`}
                    >
                      <button
                        type="button"
                        onClick={() => loadSession(s.session_id)}
                        data-testid={`copilot-session-${s.session_id}`}
                        className="flex-1 min-w-0 text-left"
                      >
                        <div className="text-xs font-medium text-zinc-100 truncate">
                          {s.last_message_preview || "(vide)"}
                        </div>
                        <div className="text-[10px] text-zinc-500">
                          {s.message_count} msgs · {s.last_at ? new Date(s.last_at).toLocaleString("fr-FR") : ""}
                        </div>
                      </button>
                      <button
                        type="button"
                        onClick={(e) => deleteSession(s.session_id, e)}
                        data-testid={`copilot-session-delete-${s.session_id}`}
                        className="w-6 h-6 rounded hover:bg-red-500/10 text-red-400 flex items-center justify-center shrink-0"
                        aria-label="Supprimer la conversation"
                      >
                        <Trash size={12} />
                      </button>
                    </div>
                  ))
                )}
              </div>
            )}

            {/* Messages */}
            <div ref={scrollRef} className="flex-1 overflow-y-auto px-5 py-4 space-y-3">
              {messages.length === 0 && !busy && (
                <div className="flex flex-col items-center text-center py-6">
                  <div className="w-14 h-14 rounded-full bg-gradient-to-br from-[#B84B31] to-[#D97706] flex items-center justify-center mb-3">
                    <Robot size={28} weight="duotone" className="text-white" />
                  </div>
                  <h3 className="font-heading text-lg font-semibold mb-1">
                    Salut {user?.name || "!"}
                  </h3>
                  <p className="text-sm text-zinc-500 max-w-xs mb-4">
                    Demande-moi n'importe quoi sur tes sites : stats, produits, commandes,
                    mises à jour en lot…
                  </p>
                  <div className="flex flex-col gap-1.5 w-full">
                    {SUGGESTIONS.map((s, i) => (
                      <button
                        key={i}
                        onClick={() => send(s)}
                        data-testid={`copilot-suggestion-${i}`}
                        className="text-left text-sm p-2.5 rounded-lg border border-zinc-800 hover:border-[#B84B31] hover:bg-zinc-900/40 transition"
                      >
                        {s}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {messages.map((m, i) => (
                <MessageBubble key={i} msg={m} />
              ))}

              {busy && (
                <div className="flex items-center gap-2 text-sm text-zinc-500" data-testid="copilot-thinking">
                  <div className="w-7 h-7 rounded-full bg-zinc-800 flex items-center justify-center">
                    <Sparkle size={12} weight="fill" className="text-zinc-100 animate-pulse" />
                  </div>
                  <span className="italic">Copilot réfléchit…</span>
                </div>
              )}
            </div>

            {/* Input */}
            <div className="border-t border-zinc-800 p-3">
              <div className="flex items-end gap-2 bg-zinc-900/40 rounded-xl p-2 focus-within:ring-2 focus-within:ring-[#B84B31]/30 transition">
                <textarea
                  rows={1}
                  value={input}
                  onChange={(e) => {
                    setInput(e.target.value);
                    e.target.style.height = "auto";
                    e.target.style.height = `${Math.min(e.target.scrollHeight, 120)}px`;
                  }}
                  onKeyDown={onKeyDown}
                  placeholder="Demande quelque chose au Copilot…"
                  disabled={busy}
                  data-testid="copilot-input"
                  className="flex-1 bg-transparent resize-none outline-none text-sm placeholder-[#A8A29E] py-1 px-1 min-h-[28px] max-h-[120px]"
                />
                <button
                  onClick={() => send()}
                  disabled={busy || !input.trim()}
                  data-testid="copilot-send"
                  className="w-9 h-9 rounded-lg bg-white hover:bg-[#44403C] disabled:opacity-40 text-black flex items-center justify-center transition active:scale-95"
                >
                  {busy ? <ArrowClockwise size={14} className="animate-spin" /> : <PaperPlaneTilt size={14} weight="fill" />}
                </button>
              </div>
              <div className="text-[10px] text-zinc-500 mt-1 px-1">
                Entrée pour envoyer · Maj+Entrée pour nouvelle ligne
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

function MessageBubble({ msg }) {
  const role = msg.role;
  if (role === "user") {
    return (
      <div className="flex justify-end" data-testid="copilot-msg-user">
        <div className="max-w-[85%] bg-white text-black rounded-md rounded-tr-sm px-3.5 py-2.5 text-sm">
          {msg.content}
        </div>
      </div>
    );
  }
  if (role === "assistant_final") {
    return (
      <div className="flex gap-2" data-testid="copilot-msg-assistant">
        <div className="shrink-0 w-7 h-7 rounded-full bg-gradient-to-br from-[#B84B31] to-[#D97706] flex items-center justify-center mt-1">
          <Sparkle size={12} weight="fill" className="text-white" />
        </div>
        <div className="flex-1 min-w-0">
          {msg.tool_trace && msg.tool_trace.length > 0 && (
            <details className="mb-2 text-xs">
              <summary className="cursor-pointer text-zinc-500 hover:text-zinc-100 flex items-center gap-1">
                <Wrench size={11} />
                {msg.tool_trace.length} outil{msg.tool_trace.length > 1 ? "s" : ""} utilisé{msg.tool_trace.length > 1 ? "s" : ""}
              </summary>
              <div className="mt-1.5 space-y-1">
                {msg.tool_trace.map((t, i) => (
                  <div key={i} className="bg-zinc-900/40 rounded p-2 font-mono text-[10px]">
                    <div className="font-semibold text-zinc-100">
                      {t.name}({Object.keys(t.arguments || {}).join(", ")})
                    </div>
                    {t.thought && <div className="text-zinc-500 italic mt-0.5">{t.thought}</div>}
                  </div>
                ))}
              </div>
            </details>
          )}
          <div className="bg-zinc-900/40 rounded-md rounded-tl-sm px-3.5 py-2.5 text-sm text-zinc-100 whitespace-pre-wrap">
            {msg.content}
          </div>
        </div>
      </div>
    );
  }
  return null;
}
