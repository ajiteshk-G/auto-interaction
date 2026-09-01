"use client";

import React, { useState } from "react";
import { LiveMessage } from "@/hooks/useLiveVoice";
import { Send, Globe, MessageSquare, Bot, User, ArrowRight } from "lucide-react";

interface LiveAudioControlsProps {
  messages: LiveMessage[];
  activeLanguage: string;
  onSwitchLanguage: (lang: string) => void;
  onSendMessage: (text: string) => void;
}

export function LiveAudioControls({
  messages,
  activeLanguage,
  onSwitchLanguage,
  onSendMessage
}: LiveAudioControlsProps) {
  const [inputText, setInputText] = useState("");

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim()) return;
    onSendMessage(inputText);
    setInputText("");
  };

  const samplePrompts = [
    "Book a doorstep test drive",
    "Thar ROXX vs BE 6e electric",
    "गाड़ी की कीमत क्या है?",
    "गाडीची किंमत आणि मायलेज सांगा",
    "காரின் விலை மற்றும் மைலேஜ் என்ன?",
    "కారు మైలేజ్ ఎంత?"
  ];

  const indianLanguages = [
    { id: "Hinglish", label: "🇮🇳 Hinglish (Natural)" },
    { id: "Hindi", label: "🇮🇳 हिन्दी (Hindi)" },
    { id: "Marathi", label: "🇮🇳 मराठी (Marathi)" },
    { id: "Tamil", label: "🇮🇳 தமிழ் (Tamil)" },
    { id: "Telugu", label: "🇮🇳 తెలుగు (Telugu)" },
    { id: "Kannada", label: "🇮🇳 ಕನ್ನಡ (Kannada)" },
    { id: "Malayalam", label: "🇮🇳 മലയാളം (Malayalam)" },
    { id: "Bengali", label: "🇮🇳 বাংলা (Bengali)" },
    { id: "Gujarati", label: "🇮🇳 ગુજરાતી (Gujarati)" },
    { id: "Punjabi", label: "🇮🇳 ਪੰਜਾਬੀ (Punjabi)" },
    { id: "Odia", label: "🇮🇳 ଓଡ଼ିଆ (Odia)" },
    { id: "Urdu", label: "🇮🇳 اردو (Urdu)" },
    { id: "Assamese", label: "🇮🇳 অসমীয়া (Assamese)" },
    { id: "English", label: "🌐 English (IN)" }
  ];

  return (
    <div className="bg-white rounded-2xl border border-slate-200 flex flex-col h-[340px] sm:h-[380px] shadow-xs overflow-hidden">
      {/* Header with Kabir Avatar Status */}
      <div className="px-4 py-2.5 border-b border-slate-200 flex items-center justify-between bg-slate-50/80">
        <div className="flex items-center gap-2">
          <MessageSquare className="w-4 h-4 text-red-600" />
          <span className="text-xs font-black text-slate-800 uppercase tracking-wider">Live Chat with Kabir</span>
        </div>
        <div className="flex items-center gap-1.5 text-[11px] font-bold text-emerald-600">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
          <span>Online</span>
        </div>
      </div>

      {/* Transcript Feed */}
      <div className="flex-1 p-4 overflow-y-auto space-y-3 font-sans text-xs bg-slate-50/40">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex gap-2.5 ${msg.speaker === "customer" ? "justify-end" : "justify-start"}`}
          >
            {msg.speaker !== "customer" && (
              <div className="w-6 h-6 rounded-full bg-red-50 border border-red-200 flex items-center justify-center shrink-0 text-red-600 font-black text-[10px]">
                K
              </div>
            )}

            <div
              className={`max-w-[82%] rounded-2xl p-3 shadow-xs ${
                msg.speaker === "customer"
                  ? "bg-red-600 text-white rounded-br-none"
                  : "bg-white text-slate-800 border border-slate-200 rounded-bl-none"
              }`}
            >
              <div className={`flex items-center justify-between gap-2 mb-1 text-[10px] ${
                msg.speaker === "customer" ? "text-red-100" : "text-slate-400"
              }`}>
                <span className="font-bold">{msg.speaker === "customer" ? "You" : "Kabir (Mahindra Showroom Specialist)"}</span>
                <span>{msg.timestamp}</span>
              </div>
              <p className="leading-relaxed whitespace-pre-wrap font-medium">{msg.text}</p>
              {msg.toolCall && (
                <div className="mt-2 pt-1.5 border-t border-slate-100 flex items-center gap-1.5 text-[10px] text-amber-600 font-mono font-bold">
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-ping"></span>
                  Action: {msg.toolCall.replace(/_/g, " ")}
                </div>
              )}
            </div>

            {msg.speaker === "customer" && (
              <div className="w-6 h-6 rounded-full bg-slate-800 flex items-center justify-center shrink-0 text-white font-bold text-[10px]">
                <User className="w-3.5 h-3.5" />
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Suggested Quick Action Chips */}
      <div className="px-3 py-2 border-t border-slate-200 bg-white flex items-center gap-1.5 overflow-x-auto no-scrollbar">
        {samplePrompts.map((p, i) => (
          <button
            key={i}
            onClick={() => onSendMessage(p)}
            className="text-[11px] font-semibold whitespace-nowrap bg-slate-50 hover:bg-red-50 text-slate-700 hover:text-red-700 px-3 py-1 rounded-full border border-slate-200 hover:border-red-200 transition-colors flex items-center gap-1 shrink-0"
          >
            {p}
            <ArrowRight className="w-2.5 h-2.5 opacity-50" />
          </button>
        ))}
      </div>

      {/* Text Input Footer */}
      <form onSubmit={handleSend} className="p-3 border-t border-slate-200 bg-white flex gap-2">
        <input
          type="text"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          placeholder="Speak or type in Hindi, Tamil, Telugu, Marathi, Bengali, Hinglish, English..."
          className="flex-1 bg-slate-50 border border-slate-200 rounded-xl px-3.5 py-2 text-xs text-slate-900 placeholder-slate-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-red-500"
        />
        <button
          type="submit"
          disabled={!inputText.trim()}
          className="bg-red-600 hover:bg-red-700 disabled:opacity-40 text-white px-4 py-2 rounded-xl transition-all flex items-center justify-center shadow-xs"
        >
          <Send className="w-4 h-4" />
        </button>
      </form>
    </div>
  );
}
