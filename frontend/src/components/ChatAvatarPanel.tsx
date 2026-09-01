"use client";

import React, { useState, useEffect, useRef } from "react";
import { LiveMessage } from "@/hooks/useLiveVoice";
import { TestDriveChatCalendar } from "./TestDriveChatCalendar";
import { identifyCustomer } from "@/lib/api";
import { BrandCatalog } from "@/types";
import {
  Power,
  PhoneOff,
  X,
  Mic,
  MicOff,
  Languages,
  Send,
  Sparkles,
  User,
  Phone,
  CheckCircle2,
  AlertCircle,
  Edit3,
  Calendar,
  Activity,
  Radio
} from "lucide-react";

interface ChatAvatarPanelProps {
  isRecording: boolean;
  rmsLevel: number;
  isAssistantSpeaking?: boolean;
  messages: LiveMessage[];
  activeLanguage: string;
  onToggleRecording: (customerName?: string, customerPhone?: string, vehicleId?: string) => void;
  onSendMessage: (text: string) => void;
  onSwitchLanguage?: (lang: string) => void;
  onSelectPrompt?: (text: string) => void;
  onClose?: () => void;
  initialCustomerName?: string;
  initialCustomerPhone?: string;
  activeVehicleId?: string;
  brand?: BrandCatalog | null;
}

export function ChatAvatarPanel({
  isRecording,
  rmsLevel,
  isAssistantSpeaking = false,
  messages,
  activeLanguage,
  onToggleRecording,
  onSendMessage,
  onSwitchLanguage,
  onClose,
  initialCustomerName = "",
  initialCustomerPhone = "",
  activeVehicleId = "thar_roxx",
  brand
}: ChatAvatarPanelProps) {
  const [name, setName] = useState<string>(initialCustomerName || "");
  const [phone, setPhone] = useState<string>(initialCustomerPhone || "");
  const [nameError, setNameError] = useState<string>("");
  const [phoneError, setPhoneError] = useState<string>("");
  const [touched, setTouched] = useState<{ name: boolean; phone: boolean }>({ name: false, phone: false });
  const [isVerified, setIsVerified] = useState<boolean>(Boolean(initialCustomerName && initialCustomerPhone));
  const [showCalendar, setShowCalendar] = useState<boolean>(false);
  const [inputText, setInputText] = useState("");
  const chatScrollRef = useRef<HTMLDivElement | null>(null);

  // Dynamic brand identities
  const brandName = brand?.name ? brand.name.replace(/\(.*\)/, "").trim() : "Mahindra";
  const primaryColor = brand?.primary_color || "#d71920";
  const agentName = brand?.agent_name || brand?.avatar_name || "Kavya";

  useEffect(() => {
    if (initialCustomerName && initialCustomerPhone) {
      setName(initialCustomerName);
      setPhone(initialCustomerPhone);
      setIsVerified(true);
    }
  }, [initialCustomerName, initialCustomerPhone]);

  // Open calendar widget when customer asks for a test ride/drive or agrees to book
  useEffect(() => {
    if (messages.length === 0) return;

    for (let i = messages.length - 1; i >= Math.max(0, messages.length - 3); i--) {
      const msg = messages[i];
      const text = (msg.text || "").trim();
      const lower = text.toLowerCase();

      // 1. Tool call triggered
      if (
        msg.toolCall === "book_test_drive" ||
        msg.toolCall === "open_test_drive_booking"
      ) {
        setShowCalendar(true);
        return;
      }

      // 2. Customer explicitly asks about / requests test drive or test ride
      if (msg.speaker === "customer") {
        const isTestDriveCustomerIntent =
          /(test\s*(drive|ride)|book\s*(a\s*)?(drive|ride|slot)|schedule\s*(a\s*)?(drive|ride|slot)|take\s*(a\s*)?(drive|ride)|drive\s*book|ride\s*book|drive\s*karna|ride\s*karna|drive\s*lena|ride\s*lena|chahiye|kara\s*do)/i.test(lower) ||
          /(book|schedule|reserve|slot).*(thar|scorpio|xuv|creta|verna|tucson|swift|brezza|grand\s*vitara|car|suv|vehicle)/i.test(lower);

        if (isTestDriveCustomerIntent) {
          setShowCalendar(true);
          return;
        }

        // 3. Customer agreed ("yes", "sure", "ok", "book it") to assistant offer
        if (i > 0) {
          const prev = messages[i - 1];
          if (prev.speaker === "mia") {
            const prevOffered = /(test\s*(drive|ride)|book|schedule|slot|preferred\s*date|calendar)/i.test(prev.text || "");
            const customerAgreed =
              /^(yes|yeah|yep|sure|ok|okay|please|definitely|let\x27?s\s+do\s+it|book\s+it|ha|haan|zaroor|bilkul|proceed|go\s*ahead|done)\b/i.test(lower) ||
              /\b(yes\s*please|book\s*it|schedule\s*it|let\x27?s\s*book|kar\s*do)\b/i.test(lower);

            if (prevOffered && customerAgreed) {
              setShowCalendar(true);
              return;
            }
          }
        }
      }

      // 4. Assistant mentions opening booking calendar / selecting slots
      if (msg.speaker === "mia") {
        if (
          /(opening|opened|shared|choose|select).*(test\s*(drive|ride)|calendar|slot|date\s*and\s*time)/i.test(lower) ||
          /(calendar|slot\s*card|below).*(test\s*(drive|ride)|booking)/i.test(lower)
        ) {
          setShowCalendar(true);
          return;
        }
      }
    }
  }, [messages]);

  // Auto-scroll transcript to bottom as new messages arrive
  useEffect(() => {
    if (chatScrollRef.current) {
      chatScrollRef.current.scrollTo({
        top: chatScrollRef.current.scrollHeight,
        behavior: "smooth"
      });
    }
  }, [messages]);

  // Validation
  const NAME_REGEX = /^[a-zA-Z\s.\x27]{2,50}$/;
  const PHONE_REGEX = /^(?:\+91|91)?[6-9]\d{9}$/;

  const validateName = (val: string): string => {
    if (!val.trim()) return "Full name is required";
    if (!NAME_REGEX.test(val.trim())) {
      return "Please enter a valid name (at least 2 letters, alphabets only)";
    }
    return "";
  };

  const validatePhone = (val: string): string => {
    const cleaned = val.replace(/[\s-]/g, "");
    if (!cleaned) return "Mobile number is required";
    if (!PHONE_REGEX.test(cleaned)) {
      return "Please enter a valid 10-digit mobile number (e.g. 9154920275)";
    }
    return "";
  };

  const isFormValid =
    name.trim().length >= 2 &&
    NAME_REGEX.test(name.trim()) &&
    PHONE_REGEX.test(phone.replace(/[\s-]/g, ""));

  const handleStartConsultation = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const nErr = validateName(name);
    const pErr = validatePhone(phone);

    if (nErr || pErr) {
      setTouched({ name: true, phone: true });
      setNameError(nErr);
      setPhoneError(pErr);
      return;
    }

    setIsVerified(true);
    identifyCustomer({
      name: name.trim(),
      phone: phone.trim(),
      session_type: "LIVE_CALL",
      vehicle_id: activeVehicleId
    }).catch((err) => console.debug("Identify customer notice:", err));

    onToggleRecording(name.trim(), phone.trim(), activeVehicleId);
  };

  const handleSend = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!inputText.trim()) return;
    onSendMessage(inputText);
    setInputText("");
  };

  const handleLanguageChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const val = e.target.value;
    if (onSwitchLanguage) {
      onSwitchLanguage(val);
    }
  };

  // Generate dynamic suggested questions based on active brand vehicles
  const suggestedQuestions = React.useMemo(() => {
    if (brand?.vehicles && brand.vehicles.length > 0) {
      const topVehicles = brand.vehicles.slice(0, 3);
      return [
        {
          text: `Tell me about the ${topVehicles[0]?.name}`,
          label: topVehicles[0]?.name
        },
        ...(topVehicles[1]
          ? [{ text: `Compare specs of ${topVehicles[1].name}`, label: topVehicles[1].name }]
          : []),
        ...(topVehicles[2]
          ? [{ text: `What is the mileage and features of ${topVehicles[2].name}?`, label: topVehicles[2].name }]
          : [])
      ];
    }
    return [
      { text: "Tell me about the new Thar ROXX 5-door SUV", label: "Thar ROXX" },
      { text: "Tell me about Scorpio-N features and price", label: "Scorpio-N" },
      { text: "Show me XUV700 Level 2 ADAS and features", label: "XUV700" }
    ];
  }, [brand]);

  // Waveform bars
  const visualizerBars = [0.35, 0.7, 1.2, 0.6, 1.0, 0.45, 0.9, 0.5, 1.1, 0.4];

  return (
    <aside className="chat-avatar-panel flex flex-col h-full bg-[#0B0F17]/95 border border-white/10 rounded-2xl shadow-2xl overflow-hidden backdrop-blur-xl">
      {/* Header Bar */}
      <div className="avatar-header flex items-center justify-between p-3.5 border-b border-white/10 bg-[#0F1420]/80">
        <div className="consultant-profile flex items-center gap-3">
          <div className="relative">
            <div
              className="w-10 h-10 rounded-full flex items-center justify-center text-white font-black text-sm shadow-md"
              style={{ backgroundColor: primaryColor }}
            >
              {agentName.charAt(0)}
            </div>
            <span
              className={`absolute bottom-0 right-0 w-3 h-3 rounded-full border-2 border-[#0B0F17] ${
                isRecording ? "bg-emerald-500 animate-pulse" : "bg-slate-500"
              }`}
            />
          </div>
          <div>
            <div className="consultant-name flex items-center gap-2">
              <span className="text-sm font-bold text-white">{agentName}</span>
              <span
                className="text-[9px] font-mono font-bold px-1.5 py-0.5 rounded-full border text-white"
                style={{
                  backgroundColor: `${primaryColor}25`,
                  borderColor: `${primaryColor}60`
                }}
              >
                {brandName} Voice AI
              </span>
              {isVerified && name && (
                <button
                  type="button"
                  onClick={() => setIsVerified(false)}
                  className="text-[9px] text-cyan-400 hover:text-white bg-cyan-950/60 hover:bg-cyan-900/80 border border-cyan-800/60 px-1.5 py-0.5 rounded-full font-mono flex items-center gap-1 cursor-pointer transition-all"
                  title="Click to edit name and phone number"
                >
                  <CheckCircle2 className="w-2.5 h-2.5 text-cyan-400" />
                  <span>{name.split(" ")[0]}</span>
                  <Edit3 className="w-2.5 h-2.5 text-slate-400 hover:text-cyan-300 ml-0.5" />
                </button>
              )}
            </div>
            <div className="consultant-title text-[11px] text-slate-400 flex items-center gap-1">
              <Radio className="w-2.5 h-2.5 text-emerald-400 animate-pulse" />
              <span>Gemini Live Audio • {brandName} Specialist</span>
            </div>
          </div>
        </div>

        <div className="avatar-header-actions flex items-center gap-2">
          {isVerified || messages.length > 0 ? (
            !isRecording ? (
              <button
                id="connectBtn"
                className="btn-primary-connect flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold text-white shadow-md transition-all hover:scale-105 cursor-pointer"
                style={{ backgroundColor: primaryColor }}
                onClick={() => onToggleRecording(name, phone, activeVehicleId)}
                title={`Start Live Voice Consultation with ${agentName}`}
              >
                <Power className="w-3.5 h-3.5" /> Start Live
              </button>
            ) : (
              <button
                id="disconnectBtn"
                className="btn-secondary-disconnect flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-red-600/20 hover:bg-red-600/30 text-red-300 border border-red-500/40 text-xs font-bold transition-all cursor-pointer"
                onClick={() => onToggleRecording()}
                title="End Live Voice Consultation"
              >
                <PhoneOff className="w-3.5 h-3.5" /> End Call
              </button>
            )
          ) : null}

          {onClose && (
            <button
              onClick={onClose}
              className="p-1.5 text-slate-400 hover:text-white bg-white/5 hover:bg-white/10 rounded-lg transition-colors cursor-pointer flex items-center justify-center"
              title="Close Audio Chat"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Pre-Chat Registration Form */}
      {!isVerified && messages.length === 0 && !isRecording ? (
        <div className="flex-1 px-4 py-3 flex flex-col justify-center overflow-y-auto animate-in fade-in duration-300">
          <div className="text-center mb-5">
            <div className="relative w-16 h-16 mx-auto mb-3">
              <div
                className="w-full h-full rounded-full p-0.5 flex items-center justify-center text-white text-2xl font-black shadow-lg"
                style={{
                  background: `linear-gradient(135deg, ${primaryColor}, #1e293b)`
                }}
              >
                {agentName.charAt(0)}
              </div>
              <span className="absolute bottom-0 right-0 w-3.5 h-3.5 rounded-full bg-emerald-500 border-2 border-[#0B0F17] flex items-center justify-center">
                <span className="w-1.5 h-1.5 rounded-full bg-white animate-ping" />
              </span>
            </div>

            <h3 className="text-sm font-black text-white uppercase tracking-wider flex items-center justify-center gap-1.5">
              <span>Connect with {agentName} AI</span>
            </h3>
            <p className="text-[11px] text-slate-300 mt-1 max-w-[280px] mx-auto leading-relaxed font-normal">
              Enter your details below to unlock your interactive live audio consultation with {brandName}&apos;s AI Showroom Specialist.
            </p>
          </div>

          <form onSubmit={handleStartConsultation} className="space-y-3.5 max-w-[340px] mx-auto w-full">
            <div className="flex items-center justify-between bg-white/[0.04] border border-white/10 rounded-xl p-2.5">
              <div className="text-[10px] text-slate-300">
                <span className="font-bold text-white">Demo Profile</span>: Ajitesh Kumar
              </div>
              <button
                type="button"
                onClick={() => {
                  setName("Ajitesh Kumar");
                  setPhone("9154920275");
                  setNameError("");
                  setPhoneError("");
                  setTouched({ name: true, phone: true });
                }}
                className="text-[10px] font-bold text-cyan-300 hover:text-white bg-cyan-950/80 hover:bg-cyan-900/90 border border-cyan-500/40 px-2.5 py-1 rounded-lg transition-all flex items-center gap-1 cursor-pointer shadow-xs active:scale-95"
                title="Fill dummy details: Ajitesh Kumar (+91 91549 20275)"
              >
                <Sparkles className="w-2.5 h-2.5 text-amber-300" />
                <span>Auto Fill</span>
              </button>
            </div>

            <div>
              <label className="block text-[10.5px] font-bold text-slate-300 uppercase tracking-wider mb-1 flex items-center justify-between">
                <span className="flex items-center gap-1.5">
                  <User className="w-3.5 h-3.5 text-cyan-400" /> Full Name
                </span>
                {touched.name && !nameError && name.trim().length >= 2 && (
                  <span className="text-emerald-400 text-[10px] flex items-center gap-1 font-mono font-bold">
                    <CheckCircle2 className="w-3 h-3" /> Valid Name
                  </span>
                )}
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => {
                  setName(e.target.value);
                  if (touched.name) {
                    setNameError(validateName(e.target.value));
                  }
                }}
                onBlur={() => {
                  setTouched((prev) => ({ ...prev, name: true }));
                  setNameError(validateName(name));
                }}
                placeholder="e.g. Ajitesh Kumar"
                className={`w-full bg-[#151D2C] border rounded-xl px-3.5 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none transition-all ${
                  touched.name && nameError
                    ? "border-red-500 ring-1 ring-red-500/40 bg-red-950/20"
                    : touched.name && !nameError && name.trim().length >= 2
                    ? "border-emerald-500/70 bg-emerald-950/20 focus:border-emerald-400 ring-1 ring-emerald-500/20"
                    : "border-white/10 focus:border-cyan-400 focus:ring-1 focus:ring-cyan-400/40"
                }`}
              />
              {touched.name && nameError && (
                <p className="text-[10px] text-red-400 mt-1 flex items-center gap-1 animate-in fade-in font-medium">
                  <AlertCircle className="w-3 h-3 shrink-0" /> {nameError}
                </p>
              )}
            </div>

            <div>
              <label className="block text-[10.5px] font-bold text-slate-300 uppercase tracking-wider mb-1 flex items-center justify-between">
                <span className="flex items-center gap-1.5">
                  <Phone className="w-3.5 h-3.5 text-cyan-400" /> Mobile Number
                </span>
                {touched.phone && !phoneError && phone.trim().length === 10 && (
                  <span className="text-emerald-400 text-[10px] flex items-center gap-1 font-mono font-bold">
                    <CheckCircle2 className="w-3 h-3" /> Valid Mobile
                  </span>
                )}
              </label>
              <div className="relative flex items-center">
                <span className="absolute left-3.5 text-xs text-slate-400 font-mono font-bold flex items-center gap-1.5 pointer-events-none border-r border-white/10 pr-2">
                  <span>🇮🇳</span> +91
                </span>
                <input
                  type="tel"
                  maxLength={10}
                  value={phone}
                  onChange={(e) => {
                    const cleaned = e.target.value.replace(/\D/g, "");
                    setPhone(cleaned);
                    if (touched.phone) {
                      setPhoneError(validatePhone(cleaned));
                    }
                  }}
                  onBlur={() => {
                    setTouched((prev) => ({ ...prev, phone: true }));
                    setPhoneError(validatePhone(phone));
                  }}
                  placeholder="91549 20275"
                  className={`w-full bg-[#151D2C] border rounded-xl pl-16 pr-3.5 py-2.5 text-xs text-white placeholder-slate-500 font-mono focus:outline-none transition-all ${
                    touched.phone && phoneError
                      ? "border-red-500 ring-1 ring-red-500/40 bg-red-950/20"
                      : touched.phone && !phoneError && phone.trim().length === 10
                      ? "border-emerald-500/70 bg-emerald-950/20 focus:border-emerald-400 ring-1 ring-emerald-500/20"
                      : "border-white/10 focus:border-cyan-400 focus:ring-1 focus:ring-cyan-400/40"
                  }`}
                />
              </div>
              {touched.phone && phoneError && (
                <p className="text-[10px] text-red-400 mt-1 flex items-center gap-1 animate-in fade-in font-medium">
                  <AlertCircle className="w-3 h-3 shrink-0" /> {phoneError}
                </p>
              )}
            </div>

            <button
              type="submit"
              disabled={!isFormValid}
              style={isFormValid ? { backgroundColor: primaryColor } : undefined}
              className={`w-full py-3 px-4 rounded-xl font-bold text-xs flex items-center justify-center gap-2 transition-all mt-2 cursor-pointer ${
                isFormValid
                  ? "text-white shadow-lg hover:scale-[1.02] active:scale-98"
                  : "bg-white/5 text-slate-500 border border-white/5 cursor-not-allowed opacity-60"
              }`}
            >
              <CheckCircle2 className="w-4 h-4 text-white" />
              <span>Connect to {brandName} AI</span>
            </button>
          </form>

          <div className="mt-3 pt-3 border-t border-white/10 max-w-[340px] mx-auto w-full text-[10.5px] text-slate-400 space-y-1.5">
            <div className="flex items-center gap-2 text-slate-300">
              <span className="text-emerald-400 font-bold">✓</span>
              <span>Real-time Live Audio in 13+ Indian Languages</span>
            </div>
            <div className="flex items-center gap-2 text-slate-300">
              <span className="text-emerald-400 font-bold">✓</span>
              <span>Instant Doorstep Test Drive Scheduling &amp; SMS Dispatch</span>
            </div>
          </div>
        </div>
      ) : (
        <div className="avatar-content-stage flex-1 p-3 flex flex-col gap-2.5 min-h-0 overflow-hidden">
          {/* Audio Chatbot Live Visualizer Card */}
          <div className="bg-[#121826] border border-white/10 rounded-2xl p-4 flex flex-col items-center justify-center relative overflow-hidden shadow-inner shrink-0">
            {/* Ambient Background Glow */}
            <div
              className="absolute w-40 h-40 rounded-full blur-2xl pointer-events-none transition-opacity duration-300"
              style={{
                backgroundColor: primaryColor,
                opacity: isRecording ? Math.min(0.4, 0.15 + rmsLevel * 0.5) : 0.08
              }}
            />

            {/* Central Audio Persona Orb */}
            <div className="relative z-10 flex items-center gap-4 w-full justify-between">
              <div className="flex items-center gap-3">
                <div
                  className="relative w-12 h-12 rounded-2xl flex items-center justify-center font-black text-white text-lg shadow-md border border-white/20 transition-transform duration-150"
                  style={{
                    backgroundColor: primaryColor,
                    transform: isAssistantSpeaking ? "scale(1.08)" : "scale(1)"
                  }}
                >
                  {agentName.charAt(0)}
                  {isRecording && (
                    <span className="absolute -top-1 -right-1 w-3.5 h-3.5 rounded-full bg-emerald-500 border-2 border-[#121826] flex items-center justify-center">
                      <span className="w-1.5 h-1.5 rounded-full bg-white animate-ping" />
                    </span>
                  )}
                </div>
                <div>
                  <div className="text-xs font-bold text-white flex items-center gap-1.5">
                    <span>{agentName}</span>
                    <span className="text-[10px] text-slate-400 font-normal">• {brandName} Specialist</span>
                  </div>
                  <div className="text-[10.5px] text-slate-400 flex items-center gap-1.5 mt-0.5">
                    {isAssistantSpeaking ? (
                      <span className="text-cyan-400 font-bold flex items-center gap-1 animate-pulse">
                        <Activity className="w-3 h-3 text-cyan-400" />
                        Speaking...
                      </span>
                    ) : isRecording ? (
                      <span className="text-emerald-400 flex items-center gap-1">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                        Listening...
                      </span>
                    ) : (
                      <span className="text-slate-400">Audio Standby</span>
                    )}
                  </div>
                </div>
              </div>

              {/* Dynamic Waveform Visualizer */}
              <div className="flex items-center gap-1 px-3 py-2 bg-black/40 rounded-xl border border-white/5">
                {visualizerBars.map((multiplier, idx) => {
                  const baseHeight = isRecording ? Math.max(4, Math.min(24, rmsLevel * 40 * multiplier)) : 4;
                  return (
                    <span
                      key={idx}
                      className="w-1 rounded-full transition-all duration-75"
                      style={{
                        height: `${baseHeight}px`,
                        backgroundColor: isRecording ? primaryColor : "#475569"
                      }}
                    />
                  );
                })}
              </div>

              {/* Audio Mic Action Button */}
              <button
                onClick={() => onToggleRecording(name, phone, activeVehicleId)}
                className={`p-2.5 rounded-xl border transition-all cursor-pointer shadow-md ${
                  isRecording
                    ? "bg-red-600 text-white border-red-500 shadow-red-600/30 hover:scale-105"
                    : "bg-white/5 text-slate-300 border-white/10 hover:text-white hover:bg-white/10"
                }`}
                title={isRecording ? "Mute Microphone" : "Unmute Microphone"}
              >
                {isRecording ? <Mic className="w-4 h-4" /> : <MicOff className="w-4 h-4" />}
              </button>
            </div>
          </div>

          {/* Conversation Chat Window */}
          <div id="chat-container" className="live-chat-box flex-1 flex flex-col min-h-0 bg-[#0E1420] border border-white/10 rounded-2xl overflow-hidden">
            <div className="chat-box-header flex items-center justify-between px-3 py-2 border-b border-white/10 bg-black/20 text-xs">
              <div className="flex items-center gap-1.5 text-slate-300 text-[11px]">
                <Languages className="w-3.5 h-3.5 text-cyan-400" />
                <span>Voice Language:</span>
              </div>
              <div className="chat-lang-toggle">
                <select
                  id="active-indian-lang-select"
                  className="lang-select-dropdown bg-[#161F30] border border-white/10 text-white text-[10px] rounded-lg px-2 py-1 focus:outline-none"
                  value={
                    activeLanguage === "Hinglish" || activeLanguage === "Hindi"
                      ? "hi-IN"
                      : activeLanguage === "English"
                      ? "en-IN"
                      : activeLanguage
                  }
                  onChange={handleLanguageChange}
                  title="Select Indian Language for Voice & Consultation"
                >
                  <option value="hi-IN">🇮🇳 Hindi (हिन्दी)</option>
                  <option value="en-IN">🇬🇧 English / Hinglish</option>
                  <option value="ta-IN">🇮🇳 Tamil (தமிழ்)</option>
                  <option value="te-IN">🇮🇳 Telugu (తెలుగు)</option>
                  <option value="kn-IN">🇮🇳 Kannada (ಕನ್ನಡ)</option>
                  <option value="mr-IN">🇮🇳 Marathi (मराठी)</option>
                  <option value="bn-IN">🇮🇳 Bengali (বাংলা)</option>
                  <option value="gu-IN">🇮🇳 Gujarati (ગુજરાતી)</option>
                  <option value="ml-IN">🇮🇳 Malayalam (മലയാളം)</option>
                  <option value="pa-IN">🇮🇳 Punjabi (ਪੰਜਾਬੀ)</option>
                  <option value="or-IN">🇮🇳 Odia (ଓଡ଼ିଆ)</option>
                  <option value="ur-IN">🇮🇳 Urdu (اردو)</option>
                  <option value="as-IN">🇮🇳 Assamese (অসমীয়া)</option>
                </select>
              </div>
            </div>

            {/* Scrollable Dialogue Area */}
            <div id="text-chat" className="chat-scroll-area flex-1 p-3 overflow-y-auto space-y-3" ref={chatScrollRef}>
              <div className="chat-welcome-card bg-white/[0.03] border border-white/10 rounded-xl p-3 text-xs space-y-2">
                <p className="welcome-title font-bold text-white">
                  👋 Namaste! Welcome to {brandName} Virtual Showroom.
                </p>
                <p className="welcome-desc text-[11px] text-slate-300 leading-relaxed">
                  {agentName} supports <strong>all Indian languages</strong> with live audio streaming. Ask any question about vehicle specs, pricing, or book a test drive slot.
                </p>
                <div className="suggested-questions flex flex-wrap gap-1.5 pt-1">
                  <button
                    className="suggestion-chip px-2.5 py-1 rounded-lg text-[10px] font-bold border flex items-center gap-1 transition-all cursor-pointer text-white"
                    style={{
                      backgroundColor: `${primaryColor}20`,
                      borderColor: `${primaryColor}50`
                    }}
                    onClick={() => {
                      setShowCalendar(true);
                      onSendMessage("I would like to check available slots and book a test drive.");
                    }}
                  >
                    <Calendar className="w-3 h-3 text-amber-300" />
                    <span>Book Test Drive (Live Slots)</span>
                  </button>
                  {suggestedQuestions.map((q, idx) => (
                    <button
                      key={idx}
                      className="suggestion-chip px-2.5 py-1 rounded-lg text-[10px] bg-white/5 hover:bg-white/10 text-slate-300 hover:text-white border border-white/10 transition-all cursor-pointer"
                      onClick={() => onSendMessage(q.text)}
                    >
                      {q.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Dialogue Bubbles */}
              {messages.map((msg) => {
                const isUser = msg.speaker === "customer";
                return (
                  <div
                    key={msg.id}
                    className={`flex flex-col ${
                      isUser ? "items-end" : "items-start"
                    } w-full`}
                  >
                    <div className="flex items-center gap-1.5 mb-1 px-1">
                      <span
                        className={`text-[10px] font-black tracking-wide ${
                          isUser ? "text-cyan-400" : "text-amber-400"
                        }`}
                      >
                        {isUser ? (name ? name.split(" ")[0] : "You") : agentName}
                      </span>
                      <span className="text-[9px] text-slate-500 font-mono">
                        {msg.timestamp}
                      </span>
                    </div>
                    <div
                      className={`chat-bubble max-w-[88%] rounded-2xl px-3.5 py-2.5 text-xs shadow-md ${
                        isUser
                          ? "bg-cyan-600 text-white rounded-br-none"
                          : "bg-[#182030] text-slate-200 border border-white/10 rounded-bl-none"
                      }`}
                    >
                      <p className="whitespace-pre-wrap leading-relaxed">{msg.text}</p>
                      {msg.toolCall && (
                        <span className="block mt-1.5 pt-1 border-t border-white/10 text-[9.5px] text-amber-300 font-mono font-bold flex items-center gap-1">
                          <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
                          Action: {msg.toolCall.replace(/_/g, " ")}
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}

              {/* Interactive Test Drive Calendar & Live Database Slots Card */}
              {showCalendar && (
                <TestDriveChatCalendar
                  vehicleId={activeVehicleId}
                  customerName={name || initialCustomerName || "Ajitesh Kumar"}
                  customerPhone={phone || initialCustomerPhone || "9154920275"}
                  onSlotBooked={(booking) => {
                    onSendMessage(
                      `I have successfully booked the ${booking.vehicle_name} (${booking.variant || ""}) test drive for ${booking.slot_date} at ${booking.slot_time}. Reference: ${booking.booking_reference}.`
                    );
                  }}
                  onClose={() => setShowCalendar(false)}
                />
              )}
            </div>

            {/* Input Bar */}
            <div className="chat-input-bar flex items-center gap-1.5 p-2.5 border-t border-white/10 bg-black/20">
              <button
                type="button"
                onClick={() => setShowCalendar((prev) => !prev)}
                className={`p-2 rounded-xl border transition-all text-xs flex items-center justify-center shrink-0 cursor-pointer ${
                  showCalendar
                    ? "bg-red-600 text-white border-red-400 shadow-md"
                    : "bg-white/5 border-white/10 text-slate-300 hover:text-white hover:border-cyan-400/50"
                }`}
                title="Open Test Drive Calendar & Available Slots"
              >
                <Calendar className="w-4 h-4 text-cyan-400" />
              </button>

              <input
                type="text"
                id="text-message"
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                placeholder={`Ask ${agentName} anything about ${brandName} vehicles...`}
                className="flex-1 bg-[#151D2C] border border-white/10 rounded-xl px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-400/60"
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    handleSend();
                  }
                }}
              />
              <button
                className="send-msg-btn p-2 rounded-xl text-white transition-all disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
                style={{ backgroundColor: primaryColor }}
                onClick={() => handleSend()}
                disabled={!inputText.trim()}
                title="Send"
              >
                <Send className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      )}
    </aside>
  );
}
