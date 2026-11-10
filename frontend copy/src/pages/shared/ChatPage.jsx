import React, { useState, useRef } from "react";
import { Send, Bot, User, Languages, Info } from "lucide-react";
import PageHeader from "@/components/common/PageHeader";
import SectionCard from "@/components/common/SectionCard";
import { sendChat } from "@/services/api/chatbot";

const LANGS = [{ code: "en", label: "English" }, { code: "hi", label: "हिन्दी" }, { code: "or", label: "ଓଡ଼ିଆ" }];

export default function ChatPage({ context = "CITIZEN", eyebrow = "Guidance", title = "Civic assistant" }) {
  const [language, setLanguage] = useState("en");
  const [messages, setMessages] = useState([{ role: "assistant", text: "Hello! Ask me about municipal services, complaints, or applications." }]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const endRef = useRef(null);

  const send = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;
    const text = input;
    setMessages(m => [...m, { role: "user", text }]);
    setInput(""); setLoading(true);
    try {
      const res = await sendChat(text, language, context);
      setMessages(m => [...m, { role: "assistant", text: res.message, sources: res.sources }]);
    } catch {
      setMessages(m => [...m, { role: "assistant", text: "Sorry, I could not process that right now." }]);
    } finally { setLoading(false); setTimeout(() => endRef.current?.scrollIntoView({ behavior: "smooth" }), 50); }
  };

  return <div className="mx-auto max-w-7xl px-5 py-8 sm:px-8 lg:px-10">
    <PageHeader eyebrow={eyebrow} title={title} description="Multilingual guidance. Official information is clearly distinguished from general advice." action={
      <div className="flex items-center gap-2"><Languages className="h-4 w-4 text-slate-400" />
        <select value={language} onChange={e => setLanguage(e.target.value)} className="rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-cyan-500 focus:outline-none">
          {LANGS.map(l => <option key={l.code} value={l.code}>{l.label}</option>)}
        </select>
      </div>} />
    <div className="mx-auto max-w-3xl">
      <SectionCard>
        <div className="flex h-[52vh] flex-col">
          <div className="flex-1 space-y-4 overflow-y-auto pr-1">
            {messages.map((m, i) => <div key={i} className={`flex gap-3 ${m.role === "user" ? "justify-end" : ""}`}>
              {m.role === "assistant" && <span className="mt-1 rounded-lg bg-indigo-100 p-2"><Bot className="h-4 w-4 text-indigo-600" /></span>}
              <div className={`max-w-[78%] rounded-2xl px-4 py-2.5 text-sm leading-6 ${m.role === "user" ? "bg-cyan-700 text-white" : "bg-slate-100 text-slate-800"}`}>
                {m.text}
                {m.sources?.length > 0 && <div className="mt-2 flex items-center gap-1.5 border-t border-slate-200 pt-2 text-xs text-slate-500"><Info className="h-3 w-3" /> Official source: {m.sources.map(s => s.title).join(", ")}</div>}
              </div>
              {m.role === "user" && <span className="mt-1 rounded-lg bg-cyan-100 p-2"><User className="h-4 w-4 text-cyan-700" /></span>}
            </div>)}
            <div ref={endRef} />
          </div>
          <form onSubmit={send} className="mt-4 flex gap-2 border-t border-slate-200 pt-4">
            <input value={input} onChange={e => setInput(e.target.value)} placeholder="Type your question…" className="flex-1 rounded-xl border border-slate-300 px-4 py-2.5 text-sm focus:border-cyan-500 focus:outline-none" />
            <button type="submit" disabled={loading} className="flex items-center gap-2 rounded-xl bg-cyan-700 px-4 py-2.5 text-sm font-semibold text-white hover:bg-cyan-800 disabled:opacity-60"><Send className="h-4 w-4" />{loading ? "…" : "Send"}</button>
          </form>
        </div>
      </SectionCard>
    </div>
  </div>;
}