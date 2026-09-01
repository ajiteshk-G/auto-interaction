"use client";

import React, { useState } from "react";
import { VehicleItem } from "@/types";
import { identifyCustomer } from "@/lib/api";
import {
  X,
  User,
  Phone,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  PhoneCall,
  MessageSquare,
  ShieldCheck,
  Bot
} from "lucide-react";

interface CustomerLeadModalProps {
  isOpen: boolean;
  onClose: () => void;
  selectedVehicle: VehicleItem | null;
  onCustomerIdentified: (data: {
    customer_id: string;
    name: string;
    phone: string;
    is_returning: boolean;
    session_id: string;
    greeting: string;
    session_type: "LIVE_CALL" | "CHAT_BOT";
  }) => void;
}

export function CustomerLeadModal({
  isOpen,
  onClose,
  selectedVehicle,
  onCustomerIdentified
}: CustomerLeadModalProps) {
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [sessionType, setSessionType] = useState<"LIVE_CALL" | "CHAT_BOT">("LIVE_CALL");
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  if (!isOpen) return null;

  // Strict Regex patterns
  const nameRegex = /^[a-zA-Z\s.']{2,50}$/;
  const cleanPhone = phone.replace(/[\s\-\(\)]/g, "");
  // Indian 10-digit starting with 6-9, optionally with +91 or 0 prefix
  const indianPhoneRegex = /^(?:\+91|0)?[6-9]\d{9}$/;

  const isNameValid = nameRegex.test(name.trim());
  const isPhoneValid = indianPhoneRegex.test(cleanPhone);
  const canSubmit = isNameValid && isPhoneValid;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit) {
      setErrorMessage("Please enter a valid Name (letters only) and 10-digit Mobile Number.");
      return;
    }

    setLoading(true);
    setErrorMessage("");

    try {
      const formattedPhone = cleanPhone.startsWith("+91")
        ? cleanPhone
        : cleanPhone.length === 10
        ? `+91${cleanPhone}`
        : cleanPhone.startsWith("0")
        ? `+91${cleanPhone.slice(1)}`
        : `+91${cleanPhone}`;

      const result = await identifyCustomer({
        name: name.trim(),
        phone: formattedPhone,
        session_type: sessionType,
        vehicle_id: selectedVehicle?.id || "thar_roxx"
      });

      onCustomerIdentified({
        customer_id: result.customer_id,
        name: result.name,
        phone: result.phone,
        is_returning: result.is_returning,
        session_id: result.session_id,
        greeting: result.greeting,
        session_type: sessionType
      });
      onClose();
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to register lead. Please check your inputs.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/80 backdrop-blur-md flex items-center justify-center p-4">
      <div className="bg-white border border-slate-200 rounded-3xl w-full max-w-lg shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="p-5 border-b border-slate-200 flex items-center justify-between bg-slate-50/80">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-red-600/10 border border-red-600/20 flex items-center justify-center text-red-600">
              <Bot className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-extrabold text-slate-900">Connect with Kavya</h2>
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
              </div>
              <p className="text-xs text-slate-500">AI Showroom Specialist</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-xl transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Selected Vehicle Context */}
        {selectedVehicle && (
          <div className="px-5 py-3 bg-slate-100/70 border-b border-slate-200 flex items-center gap-3">
            <img
              src={selectedVehicle.hero_image}
              alt={selectedVehicle.name}
              className="w-16 h-10 object-contain rounded-lg bg-white border border-slate-200 p-1 shrink-0"
            />
            <div className="text-xs">
              <div className="text-slate-500 text-[10px]">Active Consultation Vehicle:</div>
              <div className="font-black text-slate-900">{selectedVehicle.name}</div>
              <div className="text-red-600 text-[10px] font-bold">{selectedVehicle.price_range.split(" (")[0]}</div>
            </div>
          </div>
        )}

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4 text-xs">
          <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl text-slate-600 text-xs leading-relaxed">
            Please verify your details below. Kavya will personalize your live audio & co-browsing session in real time.
          </div>

          {/* Full Name Input with Regex check */}
          <div>
            <label className="block text-slate-700 font-bold mb-1.5 flex items-center justify-between">
              <span>Full Name <strong className="text-red-600">*</strong></span>
              {name.length > 0 && (
                <span
                  className={`text-[10px] font-bold flex items-center gap-1 ${
                    isNameValid ? "text-emerald-600" : "text-red-600"
                  }`}
                >
                  {isNameValid ? <CheckCircle2 className="w-3 h-3" /> : <AlertCircle className="w-3 h-3" />}
                  {isNameValid ? "Valid Name" : "Letters only (min 2 characters)"}
                </span>
              )}
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                <User className="w-4 h-4" />
              </div>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Kunal Mathuria"
                required
                className={`w-full bg-slate-50 border rounded-xl pl-9 pr-3 py-2.5 text-slate-900 font-medium placeholder-slate-400 focus:bg-white focus:outline-none transition-colors ${
                  name.length === 0
                    ? "border-slate-300 focus:border-red-600"
                    : isNameValid
                    ? "border-emerald-500 focus:border-emerald-500 ring-1 ring-emerald-500/20"
                    : "border-red-500 focus:border-red-500 ring-1 ring-red-500/20"
                }`}
              />
            </div>
          </div>

          {/* Phone Number Input with Regex check */}
          <div>
            <label className="block text-slate-700 font-bold mb-1.5 flex items-center justify-between">
              <span>Mobile Phone Number (10 Digits) <strong className="text-red-600">*</strong></span>
              {phone.length > 0 && (
                <span
                  className={`text-[10px] font-bold flex items-center gap-1 ${
                    isPhoneValid ? "text-emerald-600" : "text-red-600"
                  }`}
                >
                  {isPhoneValid ? <CheckCircle2 className="w-3 h-3" /> : <AlertCircle className="w-3 h-3" />}
                  {isPhoneValid ? "Valid Indian Mobile" : "10-digit number (e.g. 9820155432)"}
                </span>
              )}
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                <Phone className="w-4 h-4" />
              </div>
              <input
                type="tel"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="e.g. 9820155432 or +91 9820155432"
                required
                className={`w-full bg-slate-50 border rounded-xl pl-9 pr-3 py-2.5 text-slate-900 font-medium placeholder-slate-400 focus:bg-white focus:outline-none transition-colors ${
                  phone.length === 0
                    ? "border-slate-300 focus:border-red-600"
                    : isPhoneValid
                    ? "border-emerald-500 focus:border-emerald-500 ring-1 ring-emerald-500/20"
                    : "border-red-500 focus:border-red-500 ring-1 ring-red-500/20"
                }`}
              />
            </div>
          </div>

          {/* Mode Selector */}
          <div>
            <label className="block text-slate-700 font-bold mb-1.5">Preferred Interaction Mode</label>
            <div className="grid grid-cols-2 gap-2.5">
              <button
                type="button"
                onClick={() => setSessionType("LIVE_CALL")}
                className={`p-3 rounded-xl border flex items-center gap-2.5 transition-all text-left cursor-pointer ${
                  sessionType === "LIVE_CALL"
                    ? "border-red-600 bg-red-50 text-red-900 font-bold shadow-xs"
                    : "border-slate-200 bg-white text-slate-600 hover:border-slate-300"
                }`}
              >
                <PhoneCall className="w-4 h-4 text-red-600 shrink-0" />
                <div>
                  <div className="font-bold">Live Voice Stream</div>
                  <div className="text-[10px] text-slate-500 font-normal">Vertex AI Bidi PCM</div>
                </div>
              </button>

              <button
                type="button"
                onClick={() => setSessionType("CHAT_BOT")}
                className={`p-3 rounded-xl border flex items-center gap-2.5 transition-all text-left cursor-pointer ${
                  sessionType === "CHAT_BOT"
                    ? "border-red-600 bg-red-50 text-red-900 font-bold shadow-xs"
                    : "border-slate-200 bg-white text-slate-600 hover:border-slate-300"
                }`}
              >
                <MessageSquare className="w-4 h-4 text-cyan-600 shrink-0" />
                <div>
                  <div className="font-bold">Interactive Chat</div>
                  <div className="text-[10px] text-slate-500 font-normal">Multilingual Text</div>
                </div>
              </button>
            </div>
          </div>

          {/* Quick Demo Pre-fill */}
          <div className="flex items-center justify-between text-[11px] text-slate-500 pt-1">
            <span>Demo Shortcut:</span>
            <button
              type="button"
              onClick={() => {
                setName("Kunal Mathuria");
                setPhone("9820155432");
              }}
              className="text-red-600 hover:underline font-bold"
            >
              ⚡ Fill Kunal Mathuria (9820155432)
            </button>
          </div>

          {errorMessage && (
            <div className="p-3 rounded-xl bg-red-50 border border-red-200 text-red-700 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              {errorMessage}
            </div>
          )}

          {/* Submit Button */}
          <button
            type="submit"
            disabled={!canSubmit || loading}
            className="w-full bg-gradient-to-r from-red-600 to-red-700 hover:from-red-500 hover:to-red-600 disabled:opacity-40 text-white font-black py-3.5 rounded-xl transition-all shadow-md shadow-red-600/25 flex items-center justify-center gap-2 text-sm cursor-pointer"
          >
            <ShieldCheck className="w-4 h-4" />
            {loading ? "Verifying & Starting Kavya AI..." : "Start Live Consultation with Kavya →"}
          </button>
        </form>
      </div>
    </div>
  );
}
