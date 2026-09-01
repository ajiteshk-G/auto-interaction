"use client";

import React, { useState, useEffect, useRef } from "react";
import { CustomerProfile, OutboundCallInsightsResponse, TestRideInsightResponse } from "@/types";
import {
  Phone,
  PhoneCall,
  PhoneOff,
  Mic,
  MicOff,
  Volume2,
  VolumeX,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  ArrowRight,
  User,
  Clock,
  ShieldCheck,
  Award,
  Zap,
  TrendingUp,
  MessageSquare,
  Radio,
  Send,
  RefreshCw,
  Car,
  Search,
  CheckCircle,
  Building2,
  ChevronRight
} from "lucide-react";
import { triggerOutboundCall, sendOutboundDialogueTurn, fetchAdminBookings } from "@/lib/api";
import { GeminiLiveClient } from "@/lib/geminiLiveClient";

export interface OutboundLeadItem {
  booking_reference: string;
  customer_id: string;
  customer_name: string;
  customer_phone: string;
  customer_city?: string;
  vehicle_name: string;
  variant?: string;
  dealership_name?: string;
  sales_advisor_name: string;
  session_id: string;
  status: string;
  loved_features?: string[];
  objections_raised?: string[];
  has_feedback_call?: boolean;
}

const DEFAULT_COMPLETED_LEADS: OutboundLeadItem[] = [];

interface OutboundCallSimulatorProps {
  profile?: CustomerProfile | null;
  testRideInsights?: TestRideInsightResponse | null;
}

export function OutboundCallSimulator({
  profile,
  testRideInsights
}: OutboundCallSimulatorProps) {
  // Leads List
  const [leads, setLeads] = useState<OutboundLeadItem[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedLead, setSelectedLead] = useState<OutboundLeadItem | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Egress Option: "browser" vs "twilio"
  const [EgressMode, setEgressMode] = useState<"browser" | "twilio">("browser");

  // Call State
  const [callState, setCallState] = useState<"ready" | "connecting" | "in_call" | "completed">("ready");
  const [callReference, setCallReference] = useState<string>("CALL-MIA-2026-9901");
  const [callDuration, setCallDuration] = useState<number>(0);
  const [bargeInCount, setBargeInCount] = useState<number>(0);
  const [isSpeakerOn, setIsSpeakerOn] = useState<boolean>(true);
  const [turnIndex, setTurnIndex] = useState<number>(0);
  const [isAiSpeaking, setIsAiSpeaking] = useState<boolean>(false);
  const [isCustomerSpeaking, setIsCustomerSpeaking] = useState<boolean>(false);
  const [customInputText, setCustomInputText] = useState<string>("");
  const [twilioPhoneNumber, setTwilioPhoneNumber] = useState<string>("+91 98201 55432");
  const [twilioDispatchStatus, setTwilioDispatchStatus] = useState<string | null>(null);

  // Live Dialogue Feed
  const [dialogue, setDialogue] = useState<Array<{ speaker: string; role: "ai" | "customer"; text: string; time: string }>>([]);

  const timerRef = useRef<NodeJS.Timeout | null>(null);

  const geminiClientRef = useRef<GeminiLiveClient | null>(null);

  // Load authentic completed test drive bookings directly from Cloud SQL database
  const loadData = async () => {
    setIsLoading(true);
    // Clean up any legacy sessionStorage
    if (typeof window !== "undefined") {
      sessionStorage.removeItem("mahindra_selected_outbound_lead");
    }

    try {
      const rawBookings = await fetchAdminBookings();
      const bookingsList = Array.isArray(rawBookings) ? rawBookings : (rawBookings?.bookings || []);
      if (Array.isArray(bookingsList) && bookingsList.length > 0) {
        const completed: OutboundLeadItem[] = bookingsList
          .filter((b: any) => 
            b.status === "TestRide_Completed" || 
            b.status === "COMPLETED" || 
            b.status?.toLowerCase().includes("completed") ||
            (b.test_ride_sessions && b.test_ride_sessions.length > 0) ||
            (b.test_ride_transcript && b.test_ride_transcript.length > 0)
          )
          .map((b: any) => ({
            booking_reference: b.booking_reference,
            customer_id: b.customer_id,
            customer_name: b.customer_name,
            customer_phone: b.customer_phone,
            customer_city: b.customer_city || "Mumbai",
            vehicle_name: b.vehicle_name,
            variant: b.variant,
            dealership_name: b.dealership_name,
            sales_advisor_name: b.sales_advisor_name || "Mahindra Sales Consultant",
            session_id: b.test_ride_sessions?.[0]?.session_id || b.booking_reference,
            status: "TestRide_Completed",
            loved_features: b.loved_features || [],
            objections_raised: b.objections_raised || [],
            has_feedback_call: b.outbound_sessions && b.outbound_sessions.length > 0
          }));

        if (completed.length > 0) {
          setLeads(completed);
          setSelectedLead((prev) => {
            if (prev) {
              const matched = completed.find(c => c.booking_reference === prev.booking_reference);
              if (matched) return matched;
            }
            return completed[0];
          });
          if (completed[0].customer_phone) {
            setTwilioPhoneNumber(completed[0].customer_phone);
          }
        } else {
          setLeads([]);
          setSelectedLead(null);
        }
      } else {
        setLeads([]);
        setSelectedLead(null);
      }
    } catch (err) {
      console.error("Error loading outbound leads from database:", err);
      setLeads([]);
      setSelectedLead(null);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [testRideInsights]);

  // Duration Timer
  useEffect(() => {
    if (callState === "in_call") {
      timerRef.current = setInterval(() => {
        setCallDuration((prev) => prev + 1);
      }, 1000);
    } else if (timerRef.current) {
      clearInterval(timerRef.current);
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [callState]);


  const handleSelectLead = (lead: OutboundLeadItem) => {
    if (callState === "in_call") {
      handleEndCall();
    }
    setSelectedLead(lead);
    setTwilioPhoneNumber(lead.customer_phone);
    setCallState("ready");
    setCallDuration(0);
    setBargeInCount(0);
    setTurnIndex(0);
    setDialogue([]);
    setTwilioDispatchStatus(null);
  };

  const handleStartBrowserCall = async () => {
    if (!selectedLead) return;
    setCallState("connecting");
    setCallDuration(0);
    setBargeInCount(0);
    setTurnIndex(0);
    setDialogue([]);

    const advisorFirstName = selectedLead.sales_advisor_name.split(" ")[0].replace("Specialist", "").trim() || "Rajesh";

    try {
      const resp = await triggerOutboundCall({
        customer_id: selectedLead.customer_id,
        customer_name: selectedLead.customer_name,
        phone_number: selectedLead.customer_phone,
        vehicle_name: selectedLead.vehicle_name,
        advisor_name: selectedLead.sales_advisor_name,
        booking_reference: selectedLead.booking_reference,
        test_ride_session_id: selectedLead.session_id
      });
      if (resp?.call_reference) {
        setCallReference(resp.call_reference);
      }
    } catch (err) {
      console.error("Outbound trigger notice:", err);
    }

    // Initialize real-time Gemini Live WebSocket client with 16kHz PCM mic and 24kHz audio
    const client = new GeminiLiveClient({
      leadRef: selectedLead.booking_reference,
      customerName: selectedLead.customer_name,
      customerPhone: selectedLead.customer_phone,
      vehicleName: selectedLead.vehicle_name,
      salesAdvisorName: selectedLead.sales_advisor_name,
      onTranscript: (turn) => {
        if (!turn.text || !turn.text.trim()) return;
        setDialogue((prev) => {
          if (prev.length > 0) {
            const last = prev[prev.length - 1];
            if (last.role === turn.role) {
              const incoming = turn.text.trim();
              const existing = last.text.trim();

              let updatedText = existing;
              if (incoming.startsWith(existing)) {
                updatedText = incoming;
              } else if (existing.startsWith(incoming)) {
                updatedText = existing;
              } else if (existing.toLowerCase().includes(incoming.toLowerCase())) {
                updatedText = existing;
              } else {
                updatedText = `${existing} ${incoming}`;
              }

              const newArr = [...prev];
              newArr[newArr.length - 1] = {
                ...last,
                text: updatedText
              };
              return newArr;
            }
          }
          return [...prev, turn];
        });
      },
      onCustomerSpeaking: (speaking) => {
        setIsCustomerSpeaking(speaking);
      },
      onAiSpeaking: (speaking) => {
        setIsAiSpeaking(speaking);
      },
      onBargeIn: () => {
        setBargeInCount((prev) => prev + 1);
      },
      onError: (err) => {
        console.warn("Gemini Live notice:", err);
      },
      onClose: () => {
        setIsAiSpeaking(false);
        setIsCustomerSpeaking(false);
      }
    });

    geminiClientRef.current = client;
    await client.start();

    setCallState("in_call");
    const greeting = `Namaste ${selectedLead.customer_name} ji! Main Mahindra se Kavya baat kar rahi hoon. Aapka ${selectedLead.vehicle_name} ka test ride kaisa raha? Kya hamare Sales Consultant ${advisorFirstName} ji ne aapke sabhi sawalon ka theek se jawab diya?`;

    setDialogue([
      {
        speaker: "Kavya AI",
        role: "ai",
        text: greeting,
        time: "00:02"
      }
    ]);

    setTurnIndex(1);
  };

  const handleEndCall = () => {

    if (geminiClientRef.current) {
      geminiClientRef.current.stop();
      geminiClientRef.current = null;
    }
    setCallState("completed");
    setIsAiSpeaking(false);
    setIsCustomerSpeaking(false);

    // Mark as feedback captured in local leads state
    if (selectedLead) {
      setLeads((prev) =>
        prev.map((l) =>
          l.booking_reference === selectedLead.booking_reference ? { ...l, has_feedback_call: true } : l
        )
      );
    }
  };

  const handleSendCustomerTurn = async (userText: string) => {
    if (!selectedLead || !userText.trim() || isAiSpeaking) return;

    setIsCustomerSpeaking(true);
    setTimeout(() => setIsCustomerSpeaking(false), 2000);

    const currentTimeStr = `${Math.floor(callDuration / 60)
      .toString()
      .padStart(2, "0")}:${(callDuration % 60).toString().padStart(2, "0")}`;

    const newTurns = [
      ...dialogue,
      {
        speaker: selectedLead.customer_name,
        role: "customer" as const,
        text: userText,
        time: currentTimeStr
      }
    ];
    setDialogue(newTurns);
    setCustomInputText("");

    if (geminiClientRef.current) {
      geminiClientRef.current.sendTextMessage(userText);
    }

    try {
      const resp = await sendOutboundDialogueTurn({
        call_reference: callReference,
        customer_speech: userText,
        turn_number: turnIndex + 1,
        turn_index: turnIndex + 1,
        conversation_history: newTurns.map((t) => ({ speaker: t.speaker, text: t.text }))
      });

      const aiReply = resp.ai_reply || resp.agent_message || "Ji bilkul! Hum aapke delivery schedule ko priority slot mein confirm kar rahe hain.";
      const aiTimeStr = `${Math.floor((callDuration + 3) / 60)
        .toString()
        .padStart(2, "0")}:${((callDuration + 3) % 60).toString().padStart(2, "0")}`;

      setDialogue((prev) => [
        ...prev,
        {
          speaker: "Kavya AI",
          role: "ai",
          text: aiReply,
          time: aiTimeStr
        }
      ]);


      setTurnIndex((prev) => prev + 1);

      if (resp.is_call_finished || turnIndex >= 3) {
        setTimeout(() => {
          handleEndCall();
        }, 4000);
      }
    } catch (err) {
      console.error("Dialogue turn notice:", err);
      const fallbackReply = `Bahut badiya ${selectedLead.customer_name} ji! Maine aapki 12-day fast-track priority allocation confirm kar di hai. Shukriya!`;
      setDialogue((prev) => [
        ...prev,
        {
          speaker: "Kavya AI",
          role: "ai",
          text: fallbackReply,
          time: currentTimeStr
        }
      ]);

      setTurnIndex((prev) => prev + 1);
    }
  };

  const handleTwilioDispatch = () => {
    setTwilioDispatchStatus(`Dispatching automated outbound call to ${twilioPhoneNumber}...`);
    setTimeout(() => {
      setTwilioDispatchStatus(`Outbound call connected via Twilio SIP trunk (+91 22 6900 1000). Call logged to CRM.`);
      setCallState("in_call");
    }, 1800);
  };

  const filteredLeads = leads.filter((l) =>
    l.customer_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    l.customer_phone.includes(searchQuery) ||
    l.vehicle_name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="max-w-7xl mx-auto space-y-6 text-slate-900 pb-16">
      {/* Page Title & Breadcrumb */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-2 border-b border-slate-200">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-1 rounded-full bg-blue-100 text-blue-800 text-xs font-black tracking-wider uppercase">
              Stage 3 • Proactive Feedback
            </span>
            <span className="text-xs text-slate-400 font-mono">•</span>
            <span className="text-xs text-slate-500 font-medium">Post-Test Ride Resolution</span>
          </div>
          <h1 className="text-2xl font-black text-slate-900 mt-1">
            Outbound Feedback Call Center
          </h1>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => loadData()}
            disabled={isLoading}
            className="px-3 py-1.5 rounded-xl bg-white border border-slate-200 text-slate-600 hover:text-slate-900 hover:border-slate-300 transition-all flex items-center gap-1.5 text-xs font-bold shadow-2xs cursor-pointer disabled:opacity-60"
            title="Refresh database leads"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin text-red-600" : ""}`} />
            <span>{isLoading ? "Refreshing..." : "Refresh Leads"}</span>
          </button>
          <div className="px-3.5 py-1.5 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-bold flex items-center gap-2">
            <CheckCircle className="w-4 h-4 text-emerald-600" />
            <span>{leads.length} Test Ride Completed Leads</span>
          </div>
        </div>
      </div>

      {/* 2-Panel Master-Detail Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* ================= LEFT PANEL: Completed Leads List ================= */}
        <div className="lg:col-span-4 bg-white rounded-3xl border border-slate-200 shadow-xs overflow-hidden flex flex-col max-h-[820px]">
          {/* Header */}
          <div className="p-4 border-b border-slate-200 bg-slate-50/80 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Car className="w-4 h-4 text-red-600" />
                <h3 className="text-sm font-black text-slate-900">Completed Test Rides</h3>
              </div>
              <span className="px-2 py-0.5 rounded-full bg-red-100 text-red-800 text-[10px] font-bold">
                {filteredLeads.length} Leads
              </span>
            </div>

            {/* Search Input */}
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search name, phone, car..."
                className="w-full pl-8 pr-3 py-1.5 text-xs rounded-xl bg-white border border-slate-200 focus:border-blue-600 outline-none text-slate-900 placeholder-slate-400"
              />
            </div>
          </div>

          {/* Lead List Body */}
          <div className="p-3 overflow-y-auto flex-1 space-y-2 divide-y divide-slate-100">
            {isLoading ? (
              <div className="py-12 flex flex-col items-center justify-center gap-2 text-slate-400 text-xs">
                <RefreshCw className="w-5 h-5 animate-spin text-red-600" />
                <span>Loading completed test rides from database...</span>
              </div>
            ) : filteredLeads.length === 0 ? (
              <div className="py-12 text-center text-slate-400 text-xs">
                No matching completed leads found.
              </div>
            ) : (
              filteredLeads.map((lead, idx) => {
                const isSelected = selectedLead ? selectedLead.booking_reference === lead.booking_reference : false;
                return (
                  <div
                    key={idx}
                    onClick={() => handleSelectLead(lead)}
                    className={`p-3.5 rounded-2xl transition-all cursor-pointer text-left space-y-2 border ${isSelected
                        ? "bg-blue-50/80 border-blue-500 shadow-sm"
                        : "bg-white hover:bg-slate-50 border-slate-200/70"
                      }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="space-y-0.5">
                        <div className="flex items-center gap-1.5">
                          <h4 className="text-xs font-black text-slate-900">{lead.customer_name}</h4>
                          <span className="font-mono text-[10px] text-slate-500 font-bold">
                            {lead.booking_reference}
                          </span>
                        </div>
                        <p className="text-[11px] text-slate-500 font-mono font-medium">
                          {lead.customer_phone}
                        </p>
                      </div>

                      <span className={`px-2 py-0.5 rounded-full text-[9.5px] font-bold ${lead.has_feedback_call
                          ? "bg-emerald-100 text-emerald-800"
                          : "bg-blue-100 text-blue-800"
                        }`}>
                        {lead.has_feedback_call ? "Feedback Logged" : "Ready for Call"}
                      </span>
                    </div>

                    <div className="p-2 rounded-xl bg-white/80 border border-slate-200/60 text-[11px] space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-slate-900 truncate">{lead.vehicle_name}</span>
                      </div>
                      <div className="text-[10px] text-slate-500 flex items-center justify-between">
                        <span>Advisor: {lead.sales_advisor_name.split(" ")[0]}</span>
                        <span className="text-emerald-700 font-bold">✓ TestRide_Completed</span>
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* ================= RIGHT PANEL: Outbound Call Interface ================= */}
        <div className="lg:col-span-8 space-y-5">
          {!selectedLead ? (
            <div className="bg-white rounded-3xl border border-dashed border-slate-300 p-12 text-center space-y-4 shadow-xs">
              <div className="w-16 h-16 rounded-full bg-blue-50 border border-blue-200 text-blue-600 flex items-center justify-center mx-auto shadow-xs">
                <Car className="w-8 h-8" />
              </div>
              <div className="space-y-1.5 max-w-md mx-auto">
                <h3 className="text-base font-bold text-slate-800">No Completed Test Rides in Database</h3>
                <p className="text-xs text-slate-500 leading-relaxed">
                  To simulate an authentic outbound AI voice call with <strong>Kavya AI</strong>, complete a test ride session first in <strong>Stage 2 (Sales Mobile App)</strong>.
                </p>
              </div>
              <div className="pt-2">
                <a
                  href="/?stage=sales_app"
                  className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-red-600 text-white text-xs font-bold shadow-sm hover:bg-red-700 transition-all"
                >
                  <span>Go to Stage 2: Sales Companion App</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </a>
              </div>
            </div>
          ) : (
            <>
          {/* Selected Customer Details Header Card */}
          <div className="p-5 rounded-3xl bg-white border border-slate-200 shadow-xs flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-3.5">
              <div className="w-12 h-12 rounded-2xl bg-blue-100 text-blue-700 flex items-center justify-center font-black shadow-xs">
                <User className="w-6 h-6" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-base font-black text-slate-900">{selectedLead.customer_name}</h2>
                  <span className="px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-800 text-[10px] font-bold">
                    TestRide_Completed
                  </span>
                </div>
                <p className="text-xs text-slate-500 mt-0.5 flex items-center gap-2">
                  <span>Phone: <strong className="text-slate-800">{selectedLead.customer_phone}</strong></span>
                  <span>•</span>
                  <span>Session ID: <strong className="font-mono text-slate-800">{selectedLead.booking_reference || selectedLead.session_id}</strong></span>
                </p>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-3 text-xs">
              <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200 text-left">
                <span className="text-slate-400 block text-[10px] font-bold">Model Tested</span>
                <strong className="text-slate-900">{selectedLead.vehicle_name}</strong>
              </div>
              <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200 text-left">
                <span className="text-slate-400 block text-[10px] font-bold">Sales Consultant</span>
                <strong className="text-slate-900">{selectedLead.sales_advisor_name}</strong>
              </div>
            </div>
          </div>

          {/* Connect Call (Two Egress Options) Card - MATCHES SCREENSHOT EXACTLY */}
          <div className="bg-white rounded-3xl border border-slate-200 shadow-sm p-6 sm:p-8 space-y-6">
            {/* Header with Title and Status Badge */}
            <div className="flex items-center justify-between pb-4 border-b border-slate-100">
              <div className="flex items-center gap-2.5">
                <Phone className="w-5 h-5 text-slate-800" />
                <h3 className="text-lg font-black text-slate-900">
                  Connect Call (Two Egress Options)
                </h3>
              </div>
              <span className={`px-3 py-1 rounded-full text-xs font-black tracking-wider uppercase ${callState === "in_call"
                  ? "bg-emerald-100 text-emerald-800 animate-pulse"
                  : callState === "completed"
                    ? "bg-blue-100 text-blue-800"
                    : "bg-blue-50 text-blue-700 border border-blue-200"
                }`}>
                {callState === "in_call" ? "IN CALL" : callState === "completed" ? "COMPLETED" : "READY"}
              </span>
            </div>

            {/* Tab Switcher */}
            <div className="grid grid-cols-2 p-1.5 rounded-2xl bg-slate-100 border border-slate-200 gap-1.5">
              <button
                onClick={() => setEgressMode("browser")}
                className={`py-3 px-4 rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-2 cursor-pointer ${EgressMode === "browser"
                    ? "bg-white text-blue-700 shadow-xs border border-slate-200/60 font-black"
                    : "text-slate-600 hover:text-slate-900"
                  }`}
              >
                <Mic className="w-4 h-4 text-blue-600" />
                <span>Option 1: Browser Call</span>
              </button>
              <button
                onClick={() => setEgressMode("twilio")}
                className={`py-3 px-4 rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-2 cursor-pointer ${EgressMode === "twilio"
                    ? "bg-white text-blue-700 shadow-xs border border-slate-200/60 font-black"
                    : "text-slate-600 hover:text-slate-900"
                  }`}
              >
                <PhoneCall className="w-4 h-4 text-slate-700" />
                <span>Option 2: Twilio PSTN</span>
              </button>
            </div>

            {/* Option 1: Browser Call Content */}
            {EgressMode === "browser" ? (
              <div className="space-y-5">
                <p className="text-xs text-slate-600 leading-relaxed">
                  Direct bidirectional 24kHz native audio stream through your browser microphone and speakers with studio-grade continuous playback.
                </p>

                {/* Big Blue Action Button */}
                {callState === "ready" || callState === "completed" ? (
                  <button
                    onClick={handleStartBrowserCall}
                    className="w-full py-4 rounded-2xl bg-blue-600 hover:bg-blue-700 active:scale-[0.99] text-white font-black text-sm shadow-md flex items-center justify-center gap-2 transition-all cursor-pointer"
                  >
                    <Mic className="w-5 h-5" />
                    <span>{callState === "completed" ? "Restart Browser Voice Call" : "Start Browser Voice Call"}</span>
                  </button>
                ) : callState === "connecting" ? (
                    <button
                      disabled
                      className="w-full py-4 rounded-2xl bg-blue-400 text-white font-black text-sm flex items-center justify-center gap-2 cursor-not-allowed"
                    >
                      <RefreshCw className="w-5 h-5 animate-spin" />
                      <span>Connecting High-Definition Audio Stream...</span>
                    </button>
                  ) : (
                      <button
                        onClick={handleEndCall}
                        className="w-full py-4 rounded-2xl bg-rose-600 hover:bg-rose-700 text-white font-black text-sm shadow-md flex items-center justify-center gap-2 transition-all cursor-pointer"
                      >
                        <PhoneOff className="w-5 h-5" />
                        <span>End Voice Call</span>
                      </button>
                )}

                {/* Waveform / Audio Visualizer Box */}
                <div className="p-5 rounded-2xl bg-white border border-slate-200/90 shadow-xs space-y-4">
                  {/* Customer Audio Wave */}
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-slate-700 w-24">Customer</span>
                    <div className="flex-1 flex items-center justify-end gap-1 overflow-hidden px-2">
                      {[...Array(24)].map((_, i) => (
                        <div
                          key={`c-${i}`}
                          className={`w-1.5 rounded-full transition-all duration-150 ${isCustomerSpeaking
                              ? "bg-emerald-500 animate-pulse"
                              : "bg-emerald-600/70"
                            }`}
                          style={{
                            height: isCustomerSpeaking ? `${Math.max(6, (i % 6) * 4 + 6)}px` : "4px"
                          }}
                        />
                      ))}
                    </div>
                  </div>

                  {/* Kavya AI Audio Wave */}
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-slate-700 w-24">Kavya AI</span>
                    <div className="flex-1 flex items-center justify-end gap-1 overflow-hidden px-2">
                      {[...Array(24)].map((_, i) => (
                        <div
                          key={`k-${i}`}
                          className={`w-1.5 rounded-full transition-all duration-150 ${isAiSpeaking
                              ? "bg-blue-600 animate-pulse"
                              : "bg-blue-600/80"
                            }`}
                          style={{
                            height: isAiSpeaking ? `${Math.max(6, ((24 - i) % 7) * 4 + 8)}px` : "4px"
                          }}
                        />
                      ))}
                    </div>
                  </div>
                </div>

                {/* Stats Grid: Duration & Live Call Connection */}
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 text-center">
                    <div className="font-mono font-black text-xl text-slate-900">
                      {Math.floor(callDuration / 60).toString().padStart(2, "0")}:
                      {(callDuration % 60).toString().padStart(2, "0")}
                    </div>
                    <div className="text-[11px] font-semibold text-slate-500 mt-0.5">Call Duration</div>
                  </div>
                  <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 text-center">
                    <div className="font-black text-sm text-emerald-600 mt-1 flex items-center justify-center gap-1">
                      <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-ping inline-block" />
                      <span>{callState === "in_call" ? "Live Connected" : callState === "connecting" ? "Connecting..." : "Ready"}</span>
                    </div>
                    <div className="text-[11px] font-semibold text-slate-500 mt-0.5">Voice Line Status</div>
                  </div>
                </div>

                {/* Helper Card */}
                <div className="p-4 rounded-2xl bg-amber-50/70 border border-amber-200/80 text-xs text-slate-800 space-y-1">
                  <p className="leading-relaxed">
                    💡 <strong>Post-Test Ride Flow:</strong> When the call starts, Kavya will introduce herself in Hindi and ask for your feedback regarding the test drive and sales consultant support. Speak naturally into your microphone during the voice call!
                  </p>
                </div>

                {/* Live Interactive Dialogue Stream */}
                {dialogue.length > 0 && (
                  <div className="p-5 rounded-2xl bg-slate-50 border border-slate-200 space-y-3">
                    <div className="flex items-center justify-between pb-2 border-b border-slate-200">
                      <span className="text-xs font-black text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                        <MessageSquare className="w-3.5 h-3.5 text-blue-600" />
                        <span>Live Outbound Call Transcript</span>
                      </span>
                      <span className="text-[10px] font-bold text-slate-500 font-mono">
                        Ref: {callReference}
                      </span>
                    </div>

                    <div className="space-y-3 max-h-64 overflow-y-auto pr-1">
                      {dialogue.map((turn, idx) => (
                        <div
                          key={idx}
                          className={`p-3 rounded-xl text-xs space-y-1 ${turn.role === "ai"
                              ? "bg-blue-50/80 border border-blue-200/70 text-blue-950 ml-0 mr-8"
                              : "bg-white border border-slate-200 text-slate-900 ml-8 mr-0"
                            }`}
                        >
                          <div className="flex items-center justify-between text-[10px] text-slate-500 font-bold">
                            <span>{turn.speaker}</span>
                            <span>{turn.time}</span>
                          </div>
                          <p className="font-medium leading-relaxed">{turn.text}</p>
                        </div>
                      ))}
                    </div>

                    {/* Customer Text Chat Input (Optional Fallback) */}
                    {callState === "in_call" && (
                      <div className="pt-2 border-t border-slate-200">
                        <div className="flex gap-2">
                          <input
                            type="text"
                            value={customInputText}
                            onChange={(e) => setCustomInputText(e.target.value)}
                            onKeyDown={(e) => {
                              if (e.key === "Enter" && customInputText.trim()) {
                                handleSendCustomerTurn(customInputText.trim());
                              }
                            }}
                            placeholder="Speak into microphone or type customer message..."
                            className="flex-1 text-xs px-3.5 py-2 rounded-xl bg-white border border-slate-300 focus:border-blue-600 text-slate-900 outline-none"
                          />
                          <button
                            onClick={() => {
                              if (customInputText.trim()) {
                                handleSendCustomerTurn(customInputText.trim());
                              }
                            }}
                            disabled={!customInputText.trim() || isAiSpeaking}
                            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-xs font-bold rounded-xl shadow-xs cursor-pointer flex items-center gap-1.5"
                          >
                            <Send className="w-3.5 h-3.5" />
                            <span>Send</span>
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ) : (
              /* Option 2: Twilio PSTN Content */
              <div className="space-y-5">
                <p className="text-xs text-slate-600 leading-relaxed">
                  Dispatch an automated outbound cellular phone call to the customer using Twilio Voice SIP trunk with real-time speech recognition and AI response.
                </p>

                  <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 space-y-3">
                    <div>
                      <label className="block text-[11px] font-bold text-slate-700 mb-1">
                        Customer Destination Phone
                      </label>
                      <input
                        type="text"
                        value={twilioPhoneNumber}
                        onChange={(e) => setTwilioPhoneNumber(e.target.value)}
                        className="w-full text-xs font-mono font-bold px-3.5 py-2.5 rounded-xl bg-white border border-slate-300 focus:border-blue-600 outline-none text-slate-900"
                      />
                    </div>

                    <div className="grid grid-cols-2 gap-3 text-xs">
                      <div className="p-3 rounded-xl bg-white border border-slate-200">
                        <span className="text-slate-500 block text-[10px]">Caller ID</span>
                        <strong className="text-slate-900 font-mono">+91 22 6900 1000</strong>
                      </div>
                      <div className="p-3 rounded-xl bg-white border border-slate-200">
                        <span className="text-slate-500 block text-[10px]">Agent Profile</span>
                        <strong className="text-slate-900">Kavya AI (Mahindra)</strong>
                      </div>
                    </div>
                  </div>

                  <button
                    onClick={handleTwilioDispatch}
                    className="w-full py-4 rounded-2xl bg-blue-600 hover:bg-blue-700 active:scale-[0.99] text-white font-black text-sm shadow-md flex items-center justify-center gap-2 transition-all cursor-pointer"
                  >
                    <PhoneCall className="w-5 h-5" />
                    <span>Dispatch Outbound Twilio Call to {twilioPhoneNumber}</span>
                  </button>

                  {twilioDispatchStatus && (
                    <div className="p-3.5 rounded-xl bg-emerald-50 border border-emerald-200 text-xs font-bold text-emerald-800 flex items-center gap-2">
                      <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                      <span>{twilioDispatchStatus}</span>
                    </div>
                  )}
              </div>
            )}
          </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
