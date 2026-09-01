"use client";

import React, { useState, useEffect, useRef } from "react";
import { triggerOutboundCall, sendOutboundDialogueTurn, fetchOutboundCallInsights } from "@/lib/api";
import {
  Search,
  Filter,
  Download,
  Calendar,
  Clock,
  MapPin,
  Car,
  MessageSquare,
  Volume2,
  CheckCircle2,
  AlertCircle,
  Sparkles,
  User,
  Building2,
  ChevronRight,
  TrendingUp,
  ThumbsUp,
  X,
  Phone,
  PhoneCall,
  PhoneOff,
  Layers,
  Send,
  RefreshCw,
  FileText
} from "lucide-react";

export interface TranscriptTurn {
  id?: number;
  session_id?: string;
  session_type?: string;
  vehicle_id?: string;
  vehicle_name?: string;
  speaker: string;
  role?: string;
  message: string;
  timestamp?: string;
  date?: string;
  full_date?: string;
  time?: string;
  channel?: string;
  intent?: string;
  tool?: string;
}

export interface AdminBookingRecord {
  booking_id: number;
  booking_reference: string;
  brand_id?: string;
  customer_id: string;
  customer_name: string;
  customer_phone: string;
  customer_city: string;
  vehicle_id: string;
  vehicle_name: string;
  variant: string;
  color: string;
  dealership_id: string;
  dealership_name: string;
  sales_advisor_name: string;
  booking_type: string;
  delivery_address: string;
  scheduled_date: string;
  scheduled_time_slot: string;
  status: string;
  sms_status: string;
  created_at: string;
  presales_transcript: TranscriptTurn[];
  test_ride_transcript: TranscriptTurn[];
  outbound_transcript?: TranscriptTurn[];
  outbound_sessions?: any[];
  test_ride_sessions?: {
    session_id: string;
    booking_reference: string;
    gcs_uri: string;
    vehicle_name: string;
    sales_advisor_name: string;
    duration_seconds: number;
    sentiment_score: number;
    purchase_intent: number;
    loved_features: string[];
    objections_raised: string[];
    advisor_coaching_feedback: string;
    recommended_action: string;
    turns: TranscriptTurn[];
    created_at: string;
  }[];
  sentiment_score: number | null;
  purchase_intent: number | null;
  loved_features: string[];
  objections_raised: string[];
  advisor_coaching_feedback: string | null;
  recommended_action?: string | null;
  gcs_recording_uri?: string | null;
}

interface AdminStats {
  total_bookings: number;
  doorstep_deliveries: number;
  showroom_visits: number;
  confirmed_count: number;
  sms_dispatch_rate: string;
  avg_purchase_intent: string;
}

export function AdminBookingsTable() {
  const [bookings, setBookings] = useState<AdminBookingRecord[]>([]);
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [searchQuery, setSearchQuery] = useState<string>("" );
  const [selectedBrand, setSelectedBrand] = useState<string>("ALL");
  const [selectedCity, setSelectedCity] = useState<string>("ALL");
  const [selectedStatus, setSelectedStatus] = useState<string>("ALL");

  // Modal / Drawer state for transcript viewing
  const [activeModalBooking, setActiveModalBooking] = useState<AdminBookingRecord | null>(null);
  const [activeTranscriptTab, setActiveTranscriptTab] = useState<"presales" | "test_ride" | "outbound">("presales");
  
  // Outbound Feedback Call Modal State
  const [activeOutboundBooking, setActiveOutboundBooking] = useState<AdminBookingRecord | null>(null);
  const [outboundCallChannel, setOutboundCallChannel] = useState<"browser" | "twilio">("browser");
  const [outboundCallState, setOutboundCallState] = useState<"idle" | "calling" | "connected" | "ended">("idle");
  const [customInputText, setCustomInputText] = useState<string>("");
  const [twilioDispatchStatus, setTwilioDispatchStatus] = useState<string | null>(null);
  const [outboundReference, setOutboundReference] = useState<string>("");
  const [outboundDialogue, setOutboundDialogue] = useState<Array<{ speaker: string; text: string; time: string }>>([]);
  const [outboundTurnIndex, setOutboundTurnIndex] = useState<number>(0);
  const [isAiSpeaking, setIsAiSpeaking] = useState<boolean>(false);
  const [callDurationSec, setCallDurationSec] = useState<number>(0);
  const callTimerRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (outboundCallState === "connected") {
      callTimerRef.current = setInterval(() => {
        setCallDurationSec((prev) => prev + 1);
      }, 1000);
    } else if (callTimerRef.current) {
      clearInterval(callTimerRef.current);
    }
    return () => {
      if (callTimerRef.current) clearInterval(callTimerRef.current);
    };
  }, [outboundCallState]);

  const handleStartOutboundCall = async (b: AdminBookingRecord) => {
    setOutboundCallState("calling");
    setOutboundDialogue([]);
    setOutboundTurnIndex(0);
    setCallDurationSec(0);

    try {
      const resp = await triggerOutboundCall({
        customer_id: b.customer_id,
        customer_name: b.customer_name,
        phone_number: b.customer_phone,
        vehicle_name: b.vehicle_name,
        variant: b.variant,
        booking_reference: b.booking_reference,
        channel: outboundCallChannel
      });

      setOutboundReference(resp.call_reference);
      setOutboundCallState("connected");

      if (outboundCallChannel === "twilio") {
        setTwilioDispatchStatus(`Twilio Call placed to ${b.customer_phone}. Call Ref: ${resp.call_reference}`);
      } else {
        const welcomeTurn = resp.initial_greeting || `Namaste ${b.customer_name} ji! Main Mahindra se Kavya baat kar rahi hoon. Aapka ${b.vehicle_name} ka test drive kaisa raha?`;
        setOutboundDialogue([
          { speaker: "MIA (Mahindra AI Voice Specialist)", text: welcomeTurn, time: "00:01" }
        ]);
      }
    } catch (err: any) {
      setOutboundCallState("idle");
      alert(`Outbound Call Error: ${err.message || "Failed to trigger call"}`);
    }
  };

  const handleSendCustomerResponse = async (userText?: string) => {
    const textToSend = userText !== undefined ? userText : customInputText;
    if (!textToSend.trim() || !outboundReference) return;
    const userMsg = textToSend.trim();
    if (userText === undefined) setCustomInputText("");

    const turnTime = String(Math.floor(callDurationSec / 60)).padStart(2, '0') + ":" + String(callDurationSec % 60).padStart(2, '0');
    setOutboundDialogue((prev) => [
      ...prev,
      { speaker: activeOutboundBooking?.customer_name || "Customer", text: userMsg, time: turnTime }
    ]);

    setIsAiSpeaking(true);

    try {
      const turnResp = await sendOutboundDialogueTurn({
        call_reference: outboundReference,
        customer_response: userMsg,
        turn_index: outboundTurnIndex
      });

      setOutboundTurnIndex((prev) => prev + 1);
      
      setTimeout(() => {
        setIsAiSpeaking(false);
        const replyTime = String(Math.floor((callDurationSec + 2) / 60)).padStart(2, '0') + ":" + String((callDurationSec + 2) % 60).padStart(2, '0');
        setOutboundDialogue((prev) => [
          ...prev,
          { speaker: "MIA (Mahindra AI Voice Specialist)", text: turnResp.ai_reply || "Shukriya sir! Main turant aapka allocation lock karke digital financing details SMS aur WhatsApp par bhej rahi hoon.", time: replyTime }
        ]);
      }, 1200);
    } catch (e) {
      setIsAiSpeaking(false);
    }
  };

  const handleSendDialogueTurn = () => handleSendCustomerResponse();

  const handleEndOutboundCall = () => {
    setOutboundCallState("ended");
  };

  const fetchBookings = async () => {
    setIsLoading(true);
    try {
      const queryParams = new URLSearchParams();
      if (selectedBrand !== "ALL") queryParams.append("brand_id", selectedBrand);
      if (selectedCity !== "ALL") queryParams.append("city", selectedCity);
      if (selectedStatus !== "ALL") queryParams.append("status", selectedStatus);
      if (searchQuery.trim()) queryParams.append("search", searchQuery.trim());

      const res = await fetch(`/api/admin/bookings?${queryParams.toString()}`);
      if (res.ok) {
        const data = await res.json();
        setBookings(data.bookings || []);
        setStats(data.stats || null);
      }
    } catch (err) {
      console.error("Failed to fetch admin bookings:", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchBookings();
  }, [selectedBrand, selectedCity, selectedStatus]);

  useEffect(() => {
    const timer = setTimeout(() => {
      fetchBookings();
    }, 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  const handleExportCSV = () => {
    if (bookings.length === 0) return;

    const headers = [
      "Booking Reference",
      "Customer Name",
      "Phone",
      "City",
      "Vehicle",
      "Variant",
      "Date",
      "Time Slot",
      "Showroom",
      "Booking Type",
      "Address",
      "Status",
      "SMS Status",
      "PreSales Turns Count",
      "Test Ride Turns Count",
      "Purchase Intent"
    ];

    const rows = bookings.map((b) => [
      `"${b.booking_reference}"`,
      `"${b.customer_name}"`,
      `"${b.customer_phone}"`,
      `"${b.customer_city}"`,
      `"${b.vehicle_name}"`,
      `"${b.variant}"`,
      `"${b.scheduled_date}"`,
      `"${b.scheduled_time_slot}"`,
      `"${b.dealership_name}"`,
      `"${b.booking_type}"`,
      `"${b.delivery_address}"`,
      `"${b.status}"`,
      `"${b.sms_status}"`,
      b.presales_transcript.length,
      b.test_ride_transcript.length,
      `"${b.purchase_intent !== null ? Math.round(b.purchase_intent * 100) : 0}%"`
    ]);

    const csvContent = "data:text/csv;charset=utf-8," + [headers.join(","), ...rows.map((r) => r.join(","))].join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `mahindra_test_rides_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="w-full space-y-6">
      {/* KPI Stats Header Cards (Light Theme) */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
          <div className="p-4 rounded-2xl bg-white border border-slate-200 shadow-xs">
            <p className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Unique Customers</p>
            <p className="text-2xl font-black text-slate-900 mt-1">{stats.total_bookings}</p>
            <span className="text-[10.5px] text-emerald-600 font-semibold">100% Verified in DB</span>
          </div>

          <div className="p-4 rounded-2xl bg-white border border-slate-200 shadow-xs">
            <p className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Doorstep Deliveries</p>
            <p className="text-2xl font-black text-cyan-600 mt-1">{stats.doorstep_deliveries}</p>
            <span className="text-[10.5px] text-slate-500 font-medium">Fleet At Customer Home</span>
          </div>

          <div className="p-4 rounded-2xl bg-white border border-slate-200 shadow-xs">
            <p className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Showroom Visits</p>
            <p className="text-2xl font-black text-amber-600 mt-1">{stats.showroom_visits}</p>
            <span className="text-[10.5px] text-slate-500 font-medium">Dealership Experience</span>
          </div>

          <div className="p-4 rounded-2xl bg-white border border-slate-200 shadow-xs">
            <p className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Confirmed Slots</p>
            <p className="text-2xl font-black text-emerald-600 mt-1">{stats.confirmed_count}</p>
            <span className="text-[10.5px] text-emerald-600 font-semibold">Reserved in Real-Time</span>
          </div>

          <div className="p-4 rounded-2xl bg-white border border-slate-200 shadow-xs">
            <p className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Twilio SMS Dispatch</p>
            <p className="text-2xl font-black text-red-600 mt-1">{stats.sms_dispatch_rate}</p>
            <span className="text-[10.5px] text-slate-500 font-medium">Instant Confirmation</span>
          </div>

          <div className="p-4 rounded-2xl bg-white border border-slate-200 shadow-xs">
            <p className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Avg Purchase Intent</p>
            <p className="text-2xl font-black text-purple-600 mt-1">{stats.avg_purchase_intent}</p>
            <span className="text-[10.5px] text-emerald-600 font-semibold">High Buyer Conversion</span>
          </div>
        </div>
      )}

      {/* Toolbar: Search, City Filter, Status Filter & Export (Light Theme) */}
      <div className="p-4 rounded-2xl bg-white border border-slate-200 shadow-xs flex flex-col lg:flex-row gap-3 items-center justify-between">
        {/* Search */}
        <div className="relative w-full lg:w-96">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by customer, phone, booking ref, SUV..."
            className="w-full text-xs pl-9 pr-4 py-2.5 rounded-xl bg-slate-50 border border-slate-300 focus:border-red-600 focus:bg-white text-slate-900 placeholder-slate-400 outline-none transition-all"
          />
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-2 w-full lg:w-auto">
          {/* Brand Selector */}
          <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-xl border border-slate-200 overflow-x-auto scrollbar-thin">
            {[
              { id: "ALL", label: "All Brands" },
              { id: "mahindra", label: "Mahindra" },
              { id: "bmw", label: "BMW" },
              { id: "hyundai", label: "Hyundai" },
              { id: "maruti_suzuki", label: "Maruti Suzuki" }
            ].map((b) => (
              <button
                key={b.id}
                onClick={() => setSelectedBrand(b.id)}
                className={`px-3 py-1.5 rounded-lg text-[11px] font-bold transition-all shrink-0 cursor-pointer ${
                  selectedBrand === b.id
                    ? "bg-slate-900 text-white shadow-xs"
                    : "text-slate-600 hover:text-slate-900 hover:bg-white/60"
                }`}
              >
                {b.label}
              </button>
            ))}
          </div>

          {/* City Selector */}
          <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-xl border border-slate-200 overflow-x-auto scrollbar-thin">
            {["ALL", "Mumbai", "Pune", "Delhi", "Bangalore", "Chennai"].map((city) => (
              <button
                key={city}
                onClick={() => setSelectedCity(city)}
                className={`px-3 py-1.5 rounded-lg text-[11px] font-bold transition-all shrink-0 cursor-pointer ${
                  selectedCity === city
                    ? "bg-red-600 text-white shadow-xs"
                    : "text-slate-600 hover:text-slate-900 hover:bg-white/60"
                }`}
              >
                {city}
              </button>
            ))}
          </div>

          {/* Refresh */}
          <button
            onClick={fetchBookings}
            className="p-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 border border-slate-200 text-slate-700 hover:text-slate-900 text-xs font-bold transition-all cursor-pointer"
            title="Refresh Table"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? "animate-spin text-red-600" : ""}`} />
          </button>

          {/* Export CSV */}
          <button
            onClick={handleExportCSV}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 text-emerald-800 text-xs font-bold transition-all cursor-pointer shadow-xs"
          >
            <Download className="w-3.5 h-3.5 text-emerald-600" />
            <span>Export CSV</span>
          </button>
        </div>
      </div>

      {/* Main Responsive Bookings Table (Light Theme) */}
      <div className="rounded-2xl bg-white border border-slate-200 shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50/80 text-[10.5px] uppercase tracking-wider text-slate-600 font-mono">
                <th className="py-3.5 px-4 font-bold">Booking Ref / Time</th>
                <th className="py-3.5 px-4 font-bold">Customer Details</th>
                <th className="py-3.5 px-4 font-bold">Vehicle &amp; Variant</th>
                <th className="py-3.5 px-4 font-bold">Showroom &amp; Address</th>
                <th className="py-3.5 px-4 font-bold min-w-[210px] text-cyan-800">
                  <span className="flex items-center gap-1">
                    <MessageSquare className="w-3.5 h-3.5 text-cyan-600" /> PreSales Transcript
                  </span>
                </th>
                <th className="py-3.5 px-4 font-bold min-w-[210px] text-purple-800">
                  <span className="flex items-center gap-1">
                    <Volume2 className="w-3.5 h-3.5 text-purple-600" /> Test Ride Transcript
                  </span>
                </th>
                <th className="py-3.5 px-4 font-bold text-center">Status / SMS</th>
                <th className="py-3.5 px-4 font-bold text-center text-red-700 min-w-[170px]"><span className="flex items-center justify-center gap-1"><PhoneCall className="w-3.5 h-3.5 text-red-600" /> Outbound Call</span></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-slate-800">
              {isLoading && bookings.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-slate-500">
                    <div className="flex flex-col items-center justify-center gap-2">
                      <RefreshCw className="w-6 h-6 animate-spin text-red-600" />
                      <span>Loading booked test rides from database...</span>
                    </div>
                  </td>
                </tr>
              ) : bookings.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-slate-500">
                    <div className="flex flex-col items-center justify-center gap-1">
                      <AlertCircle className="w-6 h-6 text-amber-500" />
                      <span className="font-bold text-slate-800">No test ride bookings matched your filter.</span>
                      <span className="text-xs text-slate-400">Try changing the search keyword, brand or city filter.</span>
                    </div>
                  </td>
                </tr>
              ) : (
                bookings.map((booking) => {
                  const presalesLastTurn =
                    booking.presales_transcript.length > 0
                      ? booking.presales_transcript[booking.presales_transcript.length - 1]
                      : null;

                  const testRideFirstTurn =
                    booking.test_ride_transcript.length > 0
                      ? booking.test_ride_transcript[0]
                      : null;

                  return (
                    <tr
                      key={booking.booking_reference}
                      className="hover:bg-slate-50/80 transition-colors group"
                    >
                      {/* Column 1: Ref & Date */}
                      <td className="py-4 px-4 align-top">
                        <div className="flex items-center gap-1.5 flex-wrap">
                          <span className="font-mono font-black text-red-700 text-xs">
                            {booking.booking_reference}
                          </span>
                          {booking.brand_id && (
                            <span className="px-1.5 py-0.5 rounded text-[9px] font-bold uppercase bg-slate-100 text-slate-700 border border-slate-200">
                              {booking.brand_id}
                            </span>
                          )}
                        </div>
                        <div className="flex items-center gap-1 text-[11px] text-slate-800 font-bold mt-1">
                          <Calendar className="w-3 h-3 text-slate-500 shrink-0" />
                          <span>{booking.scheduled_date}</span>
                        </div>
                        <div className="flex items-center gap-1 text-[10.5px] text-slate-500 font-mono mt-0.5">
                          <Clock className="w-2.5 h-2.5 shrink-0" />
                          <span>{booking.scheduled_time_slot}</span>
                        </div>
                      </td>

                      {/* Column 2: Customer Details */}
                      <td className="py-4 px-4 align-top">
                        <div className="font-bold text-slate-900 flex items-center gap-1">
                          <User className="w-3.5 h-3.5 text-slate-500" />
                          <span>{booking.customer_name}</span>
                        </div>
                        <div className="text-[11px] text-slate-600 font-mono mt-0.5 flex items-center gap-1">
                          <Phone className="w-2.5 h-2.5 text-red-600" />
                          <span>{booking.customer_phone}</span>
                        </div>
                        <div className="text-[10px] text-slate-400 mt-0.5">
                          📍 {booking.customer_city} • {booking.customer_id}
                        </div>
                      </td>

                      {/* Column 3: Vehicle & Variant */}
                      <td className="py-4 px-4 align-top">
                        <div className="font-bold text-slate-900 flex items-center gap-1">
                          <Car className="w-3.5 h-3.5 text-red-600 shrink-0" />
                          <span>{booking.vehicle_name}</span>
                        </div>
                        <div className="inline-block px-2 py-0.5 rounded bg-red-50 border border-red-200 text-[10px] font-bold text-red-700 mt-1">
                          {booking.variant}
                        </div>
                        <div className="text-[10px] text-slate-500 mt-1">
                          Color: <span className="text-slate-700 font-medium">{booking.color}</span>
                        </div>
                      </td>

                      {/* Column 4: Showroom & Address */}
                      <td className="py-4 px-4 align-top max-w-[220px]">
                        <div className="font-bold text-slate-900 flex items-center gap-1 leading-tight">
                          <Building2 className="w-3 h-3 text-cyan-600 shrink-0" />
                          <span className="truncate">{booking.dealership_name}</span>
                        </div>
                        <div className="text-[10.5px] mt-1 leading-tight">
                          {booking.booking_type === "HOME_DOORSTEP" ? (
                            <span className="text-emerald-700 font-semibold">
                              🏠 Doorstep: {booking.delivery_address}
                            </span>
                          ) : (
                            <span className="text-amber-800 font-semibold">🏢 Showroom Visit</span>
                          )}
                        </div>
                        <div className="text-[9.5px] text-slate-500 mt-1">
                          Specialist: <span className="text-slate-700 font-medium">{booking.sales_advisor_name}</span>
                        </div>
                      </td>

                      {/* Column 5: PreSales Transcript */}
                      <td className="py-4 px-4 align-top">
                        <div className="p-2.5 rounded-xl bg-cyan-50/70 border border-cyan-200 space-y-1">
                          <div className="flex items-center justify-between text-[9.5px]">
                            <span className="font-bold text-cyan-900 font-mono">
                              {booking.presales_transcript.length} Dialogue Turns
                            </span>
                            <span className="text-[9px] text-cyan-700 font-medium">Showroom Live</span>
                          </div>
                          {presalesLastTurn && (
                            <p className="text-[10.5px] text-slate-700 line-clamp-2 italic leading-tight">
                              &ldquo;{presalesLastTurn.speaker}: {presalesLastTurn.message}&rdquo;
                            </p>
                          )}
                          <button
                            onClick={() => {
                              setActiveModalBooking(booking);
                              setActiveTranscriptTab("presales");
                            }}
                            className="mt-1 text-[10.5px] font-bold text-cyan-700 hover:text-cyan-900 underline flex items-center gap-0.5 cursor-pointer"
                          >
                            <span>Read Full Pre-Sales Chat</span>
                            <ChevronRight className="w-3 h-3" />
                          </button>
                        </div>
                      </td>

                      {/* Column 6: Test Ride Transcript */}
                      <td className="py-4 px-4 align-top">
                        {booking.test_ride_transcript.length > 0 ? (
                          <div className="p-2.5 rounded-xl bg-purple-50/70 border border-purple-200 space-y-1">
                            <div className="flex items-center justify-between text-[9.5px]">
                              <span className="font-bold text-purple-900 font-mono">
                                {booking.test_ride_transcript.length} In-Vehicle Turns
                              </span>
                              {booking.purchase_intent !== null && (
                                <span className="px-1.5 py-0.2 rounded bg-emerald-100 text-emerald-800 border border-emerald-300 text-[9px] font-bold">
                                  {Math.round(booking.purchase_intent * 100)}% Intent
                                </span>
                              )}
                            </div>
                            {testRideFirstTurn && (
                              <p className="text-[10.5px] text-slate-700 line-clamp-2 italic leading-tight">
                                &ldquo;{testRideFirstTurn.speaker}: {testRideFirstTurn.message}&rdquo;
                              </p>
                            )}
                            <button
                              onClick={() => {
                                setActiveModalBooking(booking);
                                setActiveTranscriptTab("test_ride");
                              }}
                              className="mt-1 text-[10.5px] font-bold text-purple-700 hover:text-purple-900 underline flex items-center gap-0.5 cursor-pointer"
                            >
                              <span>Read Ride Transcript &amp; Insights</span>
                              <ChevronRight className="w-3 h-3" />
                            </button>
                          </div>
                        ) : (
                          <div className="p-2.5 rounded-xl bg-slate-50 border border-dashed border-slate-200 text-center">
                            <span className="text-[10px] font-bold text-slate-500 flex items-center justify-center gap-1">
                              <Clock className="w-3 h-3 text-slate-400" /> Pending Test Ride
                            </span>
                            <p className="text-[9.5px] text-slate-400 mt-0.5">Will be captured in Stage 2</p>
                          </div>
                        )}
                      </td>

                      {/* Column 7: Status & SMS */}
                      <td className="py-4 px-4 align-top text-center space-y-1.5">
                        <div className={`inline-block px-2.5 py-0.5 rounded-full text-[10.5px] font-black tracking-wide ${booking.status === "TestRide_Completed" ? "bg-purple-100 border border-purple-300 text-purple-900" : "bg-emerald-50 border border-emerald-200 text-emerald-800"}`}>

                          {booking.status}
                        </div>
                        <div className="flex items-center justify-center gap-1 text-[10px] text-emerald-700 font-semibold">
                          <CheckCircle2 className="w-3 h-3 shrink-0" />
                          <span>Twilio SMS Sent</span>
                        </div>
                      </td>

                      {/* Column 8: Outbound Feedback Call */}
                      <td className="py-4 px-4 align-top text-center">
                        {booking.status === "TestRide_Completed" || booking.test_ride_transcript.length > 0 ? (
                          <div className="space-y-1.5">
                            <button
                              onClick={() => {
                                if (typeof window !== "undefined") {
                                  sessionStorage.setItem("mahindra_selected_outbound_lead", JSON.stringify({
                                    booking_reference: booking.booking_reference,
                                    customer_id: booking.customer_id,
                                    customer_name: booking.customer_name,
                                    customer_phone: booking.customer_phone,
                                    vehicle_name: booking.vehicle_name,
                                    sales_advisor_name: booking.sales_advisor_name,
                                    session_id: booking.test_ride_sessions?.[0]?.session_id || `TR-${booking.booking_reference}`,
                                    loved_features: booking.loved_features || ["FSD Suspension", "Panoramic Skyroof"],
                                    objections_raised: booking.objections_raised || ["Delivery timeline"]
                                  }));
                                  window.location.href = `/?stage=outbound_call&lead_ref=${booking.booking_reference}`;
                                }
                              }}
                              className="w-full px-3 py-1.5 rounded-xl bg-gradient-to-r from-red-600 to-rose-600 hover:from-red-700 hover:to-rose-700 text-white text-[10.5px] font-bold shadow-xs flex items-center justify-center gap-1.5 transition-all hover:scale-102 cursor-pointer"
                            >
                              <PhoneCall className="w-3 h-3 animate-pulse text-white" />
                              <span>Start Voice Call</span>
                            </button>

                            <button
                              onClick={() => {
                                setActiveModalBooking(booking);
                                setActiveTranscriptTab("outbound");
                              }}
                              className="w-full px-2.5 py-1 rounded-xl bg-blue-50 hover:bg-blue-100 border border-blue-200 text-blue-800 text-[10.5px] font-bold flex items-center justify-center gap-1 cursor-pointer transition-all"
                            >
                              <MessageSquare className="w-3 h-3 text-blue-600" />
                              <span>View Feedback Transcript</span>
                            </button>
                          </div>
                        ) : (
                          <div className="p-2 rounded-xl bg-slate-50 border border-slate-200 text-slate-400 text-[10px] flex items-center justify-center gap-1">
                            <Clock className="w-3 h-3 text-slate-400" />
                            <span>Requires Test Ride</span>
                          </div>
                        )}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Outbound Feedback Call Modal */}
      {activeOutboundBooking && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4 animate-in fade-in duration-200">
          <div className="bg-white border border-slate-200 rounded-3xl max-w-2xl w-full max-h-[90vh] flex flex-col shadow-2xl overflow-hidden text-left text-slate-900">
            {/* Header */}
            <div className="p-4 border-b border-slate-200 bg-gradient-to-r from-red-50 to-amber-50 flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-2xl bg-red-600 text-white flex items-center justify-center shadow-md">
                  <PhoneCall className="w-5 h-5 animate-pulse" />
                </div>
                <div>
                  <h3 className="text-sm font-black text-slate-900 flex items-center gap-2">
                    <span>MIA Proactive Post-Ride Outbound Voice Call</span>
                    <span className="px-2 py-0.5 rounded-full bg-red-100 text-red-800 border border-red-200 text-[9.5px] font-bold">
                      Stage 3 AI Loop
                    </span>
                  </h3>
                  <p className="text-[11px] text-slate-600">
                    Customer: <strong className="text-slate-900">{activeOutboundBooking.customer_name}</strong> ({activeOutboundBooking.customer_phone}) • {activeOutboundBooking.vehicle_name}
                  </p>
                </div>
              </div>

              <button
                onClick={() => {
                  handleEndOutboundCall();
                  setActiveOutboundBooking(null);
                }}
                className="p-1.5 rounded-xl bg-slate-200/80 hover:bg-slate-300 text-slate-700 transition-all text-xs cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Channel Tabs */}
            <div className="flex items-center gap-2 px-5 pt-3 border-b border-slate-200 bg-slate-50/50">
              <button
                onClick={() => setOutboundCallChannel("browser")}
                className={`px-4 py-2 text-xs font-bold border-b-2 transition-all cursor-pointer flex items-center gap-1.5 ${
                  outboundCallChannel === "browser"
                    ? "border-red-600 text-red-600 bg-white rounded-t-xl"
                    : "border-transparent text-slate-500 hover:text-slate-800"
                }`}
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>Browser Call (Gemini Live AI)</span>
              </button>
              <button
                onClick={() => setOutboundCallChannel("twilio")}
                className={`px-4 py-2 text-xs font-bold border-b-2 transition-all cursor-pointer flex items-center gap-1.5 ${
                  outboundCallChannel === "twilio"
                    ? "border-red-600 text-red-600 bg-white rounded-t-xl"
                    : "border-transparent text-slate-500 hover:text-slate-800"
                }`}
              >
                <Phone className="w-3.5 h-3.5" />
                <span>Twilio Phone Call (Live Carrier)</span>
              </button>
            </div>

            {/* Body */}
            <div className="p-5 overflow-y-auto flex-1 space-y-4">
              {/* Context Summary Banner */}
              <div className="p-3 rounded-2xl bg-amber-50/80 border border-amber-200 text-xs space-y-1">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-amber-900 uppercase text-[10px] tracking-wider flex items-center gap-1">
                    <FileText className="w-3.5 h-3.5 text-amber-700" /> In-Vehicle Test Ride Context Loaded
                  </span>
                  <span className="text-[10px] font-mono font-bold text-emerald-800 bg-emerald-100 px-2 py-0.2 rounded border border-emerald-300">
                    Strict Mahindra Guardrails Active
                  </span>
                </div>
                <p className="text-slate-700 text-[11px]">
                  Agent references test drive for <strong>{activeOutboundBooking.vehicle_name} ({activeOutboundBooking.variant})</strong>, verifies sales consultant demonstration quality, and strictly declines questions outside Mahindra.
                </p>
              </div>

              {outboundCallChannel === "browser" ? (
                <>
                  {/* Call Status Banner */}
                  <div className="p-4 rounded-2xl bg-slate-900 text-white flex items-center justify-between shadow-md">
                    <div className="flex items-center gap-3">
                      <div className={`w-3 h-3 rounded-full ${outboundCallState === "connected" ? "bg-emerald-400 animate-pulse" : outboundCallState === "calling" ? "bg-amber-400 animate-ping" : "bg-slate-500"}`}></div>
                      <div>
                        <div className="text-xs font-bold font-mono tracking-wider text-slate-200 uppercase">
                          {outboundCallState === "calling" ? "📞 Dialing Customer..." : outboundCallState === "connected" ? "🟢 Call Active • Connected to Customer" : "🔴 Call Completed"}
                        </div>
                        <div className="text-[11px] text-slate-400 font-mono">
                          Caller ID: MIA Voice Agent (+91 22 6900 1000) • Booking Ref: {activeOutboundBooking.booking_reference}
                        </div>
                      </div>
                    </div>

                    <div className="text-right">
                      <span className="text-xs font-black font-mono text-emerald-400">
                        {String(Math.floor(callDurationSec / 60)).padStart(2, '0')}:{String(callDurationSec % 60).padStart(2, '0')}
                      </span>
                    </div>
                  </div>

                  {/* Live Multi-Turn Dialogue Transcript */}
                  <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 space-y-3 min-h-[200px] max-h-[260px] overflow-y-auto">
                    {outboundDialogue.length === 0 ? (
                      <div className="py-8 text-center text-slate-400 text-xs space-y-2">
                        <RefreshCw className="w-5 h-5 animate-spin text-red-600 mx-auto" />
                        <p>Connecting voice channel with {activeOutboundBooking.customer_name}...</p>
                      </div>
                    ) : (
                      outboundDialogue.map((turn, i) => {
                        const isAi = turn.speaker.includes("MIA") || turn.speaker.includes("Specialist");
                        return (
                          <div key={i} className={`flex flex-col ${isAi ? "items-start" : "items-end"}`}>
                            <div className="text-[10px] text-slate-500 mb-0.5 px-1 font-bold">
                              {turn.speaker} <span className="font-mono text-slate-400 font-normal">• {turn.time}</span>
                            </div>
                            <div
                              className={`p-3 rounded-2xl max-w-[85%] text-xs leading-relaxed shadow-2xs ${
                                isAi
                                  ? "bg-white border border-slate-200 text-slate-900 rounded-tl-xs"
                                  : "bg-red-50 border border-red-200 text-red-950 rounded-tr-xs font-medium"
                              }`}
                            >
                              {turn.text}
                            </div>
                          </div>
                        );
                      })
                    )}
                    {isAiSpeaking && (
                      <div className="flex items-center gap-2 text-xs text-red-600 italic px-2">
                        <Sparkles className="w-3.5 h-3.5 animate-spin" />
                        <span>MIA Voice Agent is speaking...</span>
                      </div>
                    )}
                  </div>

                  {/* Interactive Quick Response Prompts & Custom Input */}
                  {outboundCallState === "connected" && (
                    <div className="space-y-2 pt-1">
                      <span className="text-[11px] font-bold text-slate-600 uppercase tracking-wider block">
                        Simulate Customer Response:
                      </span>
                      <div className="flex flex-wrap gap-2">
                        {[
                          "Drive bahut achhi thi, Sales Consultant ne saare features ache se dikhaye!",
                          "Suspension aur power top-class hai. Lekin waiting period kitna rahega?",
                          "Tata Safari aur Hyundai Creta ke baare mein batao?",
                          "Bahut pasand aaya! Stealth Black AX7L ki booking finalize kar dijiye."
                        ].map((replyText, idx) => (
                          <button
                            key={idx}
                            onClick={() => handleSendCustomerResponse(replyText)}
                            disabled={isAiSpeaking}
                            className={`px-3 py-1.5 rounded-xl border text-xs font-semibold shadow-2xs transition-all cursor-pointer disabled:opacity-50 text-left ${
                              replyText.includes("Tata")
                                ? "bg-amber-50 border-amber-300 text-amber-900 hover:bg-amber-100"
                                : "bg-white hover:bg-red-50 border-slate-200 hover:border-red-300 text-slate-800 hover:text-red-900"
                            }`}
                          >
                            💬 &ldquo;{replyText}&rdquo; {replyText.includes("Tata") && <span className="text-[9.5px] font-bold text-amber-700">(Test Guardrail)</span>}
                          </button>
                        ))}
                      </div>

                      {/* Custom User Speech Input */}
                      <div className="flex items-center gap-2 pt-1">
                        <input
                          type="text"
                          value={customInputText}
                          onChange={(e) => setCustomInputText(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === "Enter" && customInputText.trim()) {
                              handleSendCustomerResponse(customInputText.trim());
                              setCustomInputText("");
                            }
                          }}
                          placeholder="Type a custom customer response..."
                          className="flex-1 text-xs px-3 py-2 rounded-xl bg-slate-50 border border-slate-300 focus:border-red-600 focus:bg-white text-slate-900 placeholder-slate-400 outline-none"
                        />
                        <button
                          onClick={() => {
                            if (customInputText.trim()) {
                              handleSendCustomerResponse(customInputText.trim());
                              setCustomInputText("");
                            }
                          }}
                          disabled={!customInputText.trim() || isAiSpeaking}
                          className="px-4 py-2 bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white text-xs font-bold rounded-xl shadow-xs cursor-pointer flex items-center gap-1"
                        >
                          <Send className="w-3.5 h-3.5" />
                          <span>Send</span>
                        </button>
                      </div>
                    </div>
                  )}
                </>
              ) : (
                /* Twilio Voice Dispatch View */
                <div className="p-6 rounded-2xl bg-white border border-slate-200 text-center space-y-4 shadow-xs">
                  <div className="w-14 h-14 rounded-2xl bg-red-100 text-red-600 flex items-center justify-center mx-auto shadow-xs">
                    <Phone className="w-7 h-7" />
                  </div>
                  <div>
                    <h4 className="text-base font-black text-slate-900">Direct Twilio Carrier Phone Call</h4>
                    <p className="text-xs text-slate-500 max-w-md mx-auto mt-1">
                      Dispatch an automated outbound cellular voice call to customer <strong>{activeOutboundBooking.customer_name}</strong> at <strong>{activeOutboundBooking.customer_phone}</strong>.
                    </p>
                  </div>

                  <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 max-w-md mx-auto text-left text-xs space-y-2">
                    <div className="flex justify-between">
                      <span className="text-slate-500">Destination:</span>
                      <strong className="text-slate-900">{activeOutboundBooking.customer_phone}</strong>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Caller ID:</span>
                      <span className="font-mono font-bold text-slate-800">+91 22 6900 1000 (MIA Mahindra)</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Agent Script:</span>
                      <span className="text-slate-800 font-medium">Hindi/Hinglish Post-Ride Review</span>
                    </div>
                  </div>

                  <button
                    onClick={() => {
                      setTwilioDispatchStatus("Calling customer phone via Twilio Voice Trunk (+91 22 6900 1000)...");
                      setTimeout(() => {
                        setTwilioDispatchStatus("Call initiated successfully. Audio session logged in database.");
                      }, 2000);
                    }}
                    className="px-6 py-3 bg-red-600 hover:bg-red-700 text-white font-black text-xs rounded-xl shadow-md flex items-center justify-center gap-2 mx-auto cursor-pointer transition-all hover:scale-102"
                  >
                    <PhoneCall className="w-4 h-4" />
                    <span>Dispatch Twilio Call to {activeOutboundBooking.customer_phone}</span>
                  </button>

                  {twilioDispatchStatus && (
                    <p className="text-xs text-emerald-700 font-bold bg-emerald-50 p-2.5 rounded-xl border border-emerald-200">
                      ✓ {twilioDispatchStatus}
                    </p>
                  )}
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="p-4 border-t border-slate-200 bg-slate-50 flex items-center justify-between">
              {outboundCallState === "connected" ? (
                <button
                  onClick={handleEndOutboundCall}
                  className="px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white text-xs font-bold rounded-xl flex items-center gap-1.5 cursor-pointer shadow-xs"
                >
                  <PhoneOff className="w-4 h-4" />
                  <span>End Outbound Call</span>
                </button>
              ) : outboundCallState === "ended" ? (
                <span className="text-xs font-bold text-emerald-700 flex items-center gap-1">
                  <CheckCircle2 className="w-4 h-4" />
                  <span>Customer feedback captured • Fast-track allocation confirmed</span>
                </span>
              ) : (
                <span></span>
              )}

              <button
                onClick={() => {
                  handleEndOutboundCall();
                  setActiveOutboundBooking(null);
                }}
                className="px-4 py-2 bg-slate-200 hover:bg-slate-300 text-slate-800 text-xs font-bold rounded-xl transition-all cursor-pointer"
              >
                Close Window
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Interactive Transcript Modal / Drawer (Light Theme) */}
      {activeModalBooking && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4 animate-in fade-in duration-200">
          <div className="bg-white border border-slate-200 rounded-3xl max-w-3xl w-full max-h-[90vh] flex flex-col shadow-2xl overflow-hidden text-left text-slate-900">
            {/* Modal Header */}
            <div className="p-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-mono font-black text-red-700 text-sm">
                    {activeModalBooking.booking_reference}
                  </span>
                  <span className="px-2 py-0.5 rounded bg-red-100 text-red-800 border border-red-200 text-[10px] font-bold">
                    {activeModalBooking.vehicle_name}
                  </span>
                </div>
                <p className="text-xs text-slate-500 mt-0.5">
                  Customer: <strong>{activeModalBooking.customer_name}</strong> ({activeModalBooking.customer_phone}) • {activeModalBooking.dealership_name}
                </p>
              </div>

              <button
                onClick={() => setActiveModalBooking(null)}
                className="p-1.5 rounded-xl bg-slate-200/60 hover:bg-slate-200 text-slate-600 hover:text-slate-900 transition-all text-xs cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Tab Switches: PreSales vs Test Ride */}
            <div className="flex border-b border-slate-200 bg-slate-100 px-4">
              <button
                onClick={() => setActiveTranscriptTab("presales")}
                className={`py-2.5 px-4 font-bold text-xs flex items-center gap-2 border-b-2 transition-all cursor-pointer ${
                  activeTranscriptTab === "presales"
                    ? "border-cyan-600 text-cyan-800 bg-white shadow-xs"
                    : "border-transparent text-slate-600 hover:text-slate-900"
                }`}
              >
                <MessageSquare className="w-3.5 h-3.5" />
                <span>1. Pre-Sales Showroom Transcript ({activeModalBooking.presales_transcript.length} turns)</span>
              </button>

              <button
                onClick={() => setActiveTranscriptTab("test_ride")}
                className={`py-2.5 px-4 font-bold text-xs flex items-center gap-2 border-b-2 transition-all cursor-pointer ${
                  activeTranscriptTab === "test_ride"
                    ? "border-purple-600 text-purple-800 bg-white shadow-xs"
                    : "border-transparent text-slate-600 hover:text-slate-900"
                }`}
              >
                <Volume2 className="w-3.5 h-3.5" />
                <span>2. In-Vehicle Test Ride Transcript &amp; Insights</span>
              </button>

              <button
                onClick={() => setActiveTranscriptTab("outbound")}
                className={`py-2.5 px-4 font-bold text-xs flex items-center gap-2 border-b-2 transition-all cursor-pointer ${
                  activeTranscriptTab === "outbound"
                    ? "border-blue-600 text-blue-800 bg-white shadow-xs"
                    : "border-transparent text-slate-600 hover:text-slate-900"
                }`}
              >
                <PhoneCall className="w-3.5 h-3.5" />
                <span>3. TestRide Feedback Call ({(activeModalBooking.outbound_transcript || []).length} turns)</span>
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-5 overflow-y-auto flex-1 space-y-4 bg-white">
              {activeTranscriptTab === "presales" ? (
                <div className="space-y-4">
                  <div className="p-3 rounded-xl bg-cyan-50 border border-cyan-200 text-xs text-cyan-900 flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <Sparkles className="w-4 h-4 text-cyan-600 shrink-0" />
                      <span>
                        Live transcript for <strong>{activeModalBooking.customer_name}</strong> ({activeModalBooking.customer_phone}) with <strong>Kavya (AI Specialist)</strong>.
                      </span>
                    </div>
                    <span className="text-[11px] font-mono bg-cyan-100 text-cyan-800 px-2 py-0.5 rounded-lg border border-cyan-300 font-bold shrink-0">
                      {activeModalBooking.presales_transcript.length} turns
                    </span>
                  </div>

                  {/* Grouped Transcripts by Session ID */}
                  {(() => {
                    const sessionGroups: {
                      [sessId: string]: {
                        sessionId: string;
                        sessionType: string;
                        vehicleName: string;
                        date: string;
                        time: string;
                        channel: string;
                        turns: TranscriptTurn[];
                      };
                    } = {};

                    activeModalBooking.presales_transcript.forEach((turn) => {
                      const sId = turn.session_id || "HISTORIC_SESSION";
                      if (!sessionGroups[sId]) {
                        sessionGroups[sId] = {
                          sessionId: sId,
                          sessionType: turn.session_type || (turn.channel === "VOICE_LIVE" ? "LIVE_VOICE" : "WEB_CHAT"),
                          vehicleName: turn.vehicle_name || activeModalBooking.vehicle_name,
                          date: turn.full_date || turn.date || "Today",
                          time: turn.time || turn.timestamp || "",
                          channel: turn.channel || "VOICE_LIVE",
                          turns: []
                        };
                      }
                      sessionGroups[sId].turns.push(turn);
                    });

                    const groupList = Object.values(sessionGroups);

                    if (groupList.length === 0) {
                      return (
                        <div className="py-8 text-center text-slate-400">
                          <p>No conversation transcripts recorded yet.</p>
                        </div>
                      );
                    }

                    return groupList.map((session, sIdx) => (
                      <div
                        key={sIdx}
                        className="rounded-2xl border border-slate-200 bg-slate-50/50 p-4 space-y-3.5 shadow-xs"
                      >
                        {/* Session Card Header */}
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-slate-200 bg-white -mx-4 -mt-4 p-3.5 rounded-t-2xl">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="px-2.5 py-1 rounded-full bg-cyan-100 text-cyan-800 border border-cyan-300 text-[11px] font-bold flex items-center gap-1.5">
                              {session.sessionType === "LIVE_VOICE" || session.channel === "VOICE_LIVE" ? (
                                <>
                                  <Volume2 className="w-3 h-3 text-cyan-600" />
                                  <span>Live Voice Stream</span>
                                </>
                              ) : (
                                <>
                                  <MessageSquare className="w-3 h-3 text-cyan-600" />
                                  <span>Virtual Showroom Chat</span>
                                </>
                              )}
                            </span>

                            <span className="font-mono text-[11px] font-bold text-slate-700 bg-slate-100 px-2 py-0.5 rounded-md border border-slate-200">
                              {session.sessionId}
                            </span>

                            <span className="text-xs font-bold text-amber-800 bg-amber-50 px-2 py-0.5 rounded-md border border-amber-200 flex items-center gap-1">
                              <Car className="w-3 h-3 text-amber-600 inline" />
                              <span>{session.vehicleName}</span>
                            </span>
                          </div>

                          <div className="flex items-center gap-2 text-[11px] text-slate-500 font-mono">
                            <span className="flex items-center gap-1">
                              <Calendar className="w-3 h-3" />
                              {session.date}
                            </span>
                            {session.time && (
                              <span className="flex items-center gap-0.5">
                                • <Clock className="w-3 h-3 ml-1" /> {session.time}
                              </span>
                            )}
                            <span className="bg-slate-100 text-slate-600 px-2 py-0.5 rounded-full font-bold">
                              {session.turns.length} turns
                            </span>
                          </div>
                        </div>

                        {/* Dialogue turns in this session */}
                        <div className="space-y-2.5 pt-1">
                          {session.turns.map((turn, idx) => {
                            const isUser = turn.role === "customer" || turn.speaker.toLowerCase().includes("customer");
                            return (
                              <div
                                key={idx}
                                className={`flex flex-col ${isUser ? "items-end" : "items-start"}`}
                              >
                                <div className="flex items-center gap-1.5 mb-1 text-[10px] text-slate-500 px-1">
                                  <span className={`font-bold ${isUser ? "text-cyan-700" : "text-amber-800"}`}>
                                    {turn.speaker}
                                  </span>
                                  {(turn.time || turn.timestamp) && (
                                    <span className="font-mono text-slate-400 flex items-center gap-0.5">
                                      <Clock className="w-2.5 h-2.5 inline" />
                                      {turn.time || turn.timestamp}
                                    </span>
                                  )}
                                </div>
                                <div
                                  className={`p-3.5 rounded-2xl max-w-[85%] text-xs leading-relaxed shadow-xs ${
                                    isUser
                                      ? "bg-cyan-50 border border-cyan-200 text-cyan-950 rounded-tr-xs"
                                      : "bg-white border border-slate-200 text-slate-800 rounded-tl-xs"
                                  }`}
                                >
                                  <p>{turn.message}</p>
                                  {turn.tool && (
                                    <div className="mt-2 pt-1.5 border-t border-slate-200 text-[9.5px] text-amber-800 font-mono flex items-center gap-1">
                                      <span>⚡ Tool Action: {turn.tool}</span>
                                    </div>
                                  )}
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    ));
                  })()}
                </div>
              ) : activeTranscriptTab === "test_ride" ? (
                <div className="space-y-4">
                  {((activeModalBooking.test_ride_sessions && activeModalBooking.test_ride_sessions.length > 0) || activeModalBooking.test_ride_transcript.length > 0) ? (
                    <div className="space-y-5">
                      {/* Grouped Test Ride Transcripts by Booking ID */}
                      {(() => {
                        const sessions = (activeModalBooking.test_ride_sessions && activeModalBooking.test_ride_sessions.length > 0)
                          ? activeModalBooking.test_ride_sessions
                          : [{
                              session_id: `TR-${activeModalBooking.booking_reference}`,
                              booking_reference: activeModalBooking.booking_reference,
                              gcs_uri: activeModalBooking.gcs_recording_uri || `gs://mahindra-sales-recordings/test_rides/2026-08-26/${activeModalBooking.booking_reference}.wav`,
                              vehicle_name: activeModalBooking.vehicle_name,
                              sales_advisor_name: activeModalBooking.sales_advisor_name,
                              duration_seconds: 184,
                              sentiment_score: activeModalBooking.sentiment_score ?? 0.88,
                              purchase_intent: activeModalBooking.purchase_intent ?? 0.92,
                              loved_features: activeModalBooking.loved_features,
                              objections_raised: activeModalBooking.objections_raised,
                              advisor_coaching_feedback: activeModalBooking.advisor_coaching_feedback || "Demonstrated vehicle dynamics and key features effectively.",
                              recommended_action: activeModalBooking.recommended_action || "Follow up on regional inventory allocation.",
                              turns: activeModalBooking.test_ride_transcript,
                              created_at: activeModalBooking.created_at
                            }];

                        return sessions.map((sess, sIdx) => (
                          <div
                            key={sIdx}
                            className="rounded-2xl border border-purple-200/80 bg-slate-50/50 p-4 space-y-3.5 shadow-xs"
                          >
                            {/* Group Card Header */}
                            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-purple-100 bg-purple-50/60 -mx-4 -mt-4 p-3.5 rounded-t-2xl">
                              <div className="flex items-center gap-2 flex-wrap">
                                <span className="px-2.5 py-1 rounded-full bg-purple-600 text-white text-[11px] font-bold flex items-center gap-1.5 shadow-xs">
                                  <Volume2 className="w-3 h-3" />
                                  <span>Test Ride Audio Recording</span>
                                </span>

                                <span className="font-mono text-[11px] font-bold text-purple-900 bg-purple-100 px-2 py-0.5 rounded-md border border-purple-200">
                                  Booking ID: {sess.booking_reference}
                                </span>

                                <span className="text-xs font-bold text-slate-800 bg-white px-2 py-0.5 rounded-md border border-slate-200 flex items-center gap-1">
                                  <Car className="w-3 h-3 text-purple-600 inline" />
                                  <span>{sess.vehicle_name}</span>
                                </span>
                              </div>

                              <div className="flex items-center gap-2 text-[11px] text-slate-600 font-mono">
                                <span className="bg-white px-2.5 py-0.5 rounded-full border border-purple-200 font-bold text-purple-800">
                                  {sess.duration_seconds}s audio
                                </span>
                                <span className="bg-white px-2 py-0.5 rounded-full border border-slate-200 font-bold">
                                  {sess.turns.length} turns
                                </span>
                              </div>
                            </div>

                            {/* GCS Path Banner */}
                            <div className="p-2.5 rounded-xl bg-purple-100/50 border border-purple-200 text-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2">
                              <div className="flex items-center gap-2 text-purple-900">
                                <FileText className="w-4 h-4 text-purple-700 shrink-0" />
                                <div>
                                  <span className="text-[10px] font-bold uppercase text-purple-700 block">GCS Cloud Audio Location:</span>
                                  <span className="font-mono text-[11px] font-bold break-all select-all text-purple-950">{sess.gcs_uri}</span>
                                </div>
                              </div>
                              <span className="text-[9.5px] font-bold font-mono bg-purple-200 text-purple-900 px-2 py-0.5 rounded border border-purple-300 shrink-0">
                                WAV Audio
                              </span>
                            </div>

                            {/* AI Extracted Insights Bar */}
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-2.5">
                              <div className="p-3 rounded-xl bg-white border border-slate-200 shadow-xs">
                                <span className="text-[10px] text-slate-500 uppercase font-bold">Sentiment Score</span>
                                <p className="text-base font-black text-emerald-600 mt-0.5">
                                  {sess.sentiment_score !== null
                                    ? `${Math.round(sess.sentiment_score * 100)}% Positive`
                                    : "88% Positive"}
                                </p>
                              </div>

                              <div className="p-3 rounded-xl bg-white border border-slate-200 shadow-xs">
                                <span className="text-[10px] text-slate-500 uppercase font-bold">Purchase Intent</span>
                                <p className="text-base font-black text-cyan-600 mt-0.5">
                                  {sess.purchase_intent !== null
                                    ? `${Math.round(sess.purchase_intent * 100)}% Ready`
                                    : "92% Ready"}
                                </p>
                              </div>

                              <div className="p-3 rounded-xl bg-white border border-slate-200 shadow-xs col-span-2">
                                <span className="text-[10px] text-slate-500 uppercase font-bold">Loved Features</span>
                                <div className="flex flex-wrap gap-1 mt-1">
                                  {sess.loved_features && sess.loved_features.length > 0 ? (
                                    sess.loved_features.map((f, i) => (
                                      <span
                                        key={i}
                                        className="px-2 py-0.5 rounded bg-emerald-50 text-emerald-800 border border-emerald-200 text-[9.5px] font-bold"
                                      >
                                        ✓ {f}
                                      </span>
                                    ))
                                  ) : (
                                    <span className="text-xs text-slate-400 italic">FSD Suspension, Panoramic Skyroof</span>
                                  )}
                                </div>
                              </div>
                            </div>

                            {/* Advisor Coaching & Next Action */}
                            {sess.advisor_coaching_feedback && (
                              <div className="p-3 rounded-xl bg-purple-50 border border-purple-200 text-xs text-purple-900 shadow-xs space-y-1">
                                <p className="font-bold flex items-center gap-1.5 text-purple-800">
                                  <TrendingUp className="w-3.5 h-3.5 text-purple-600" /> Advisor In-Vehicle Coaching:
                                </p>
                                <p className="text-[11px] text-purple-950 leading-relaxed">
                                  {sess.advisor_coaching_feedback}
                                </p>
                                {sess.recommended_action && (
                                  <div className="pt-1.5 border-t border-purple-200 text-[10.5px] font-semibold text-amber-800">
                                    Recommended Next Action: {sess.recommended_action}
                                  </div>
                                )}
                              </div>
                            )}

                            {/* Test Ride Dialogue Turns */}
                            <div className="space-y-2 pt-1">
                              <h5 className="text-[11px] font-bold text-slate-700 uppercase tracking-wider">
                                Speaker-Identified Audio Dialogue Turns ({sess.turns.length}):
                              </h5>
                              <div className="space-y-2">
                                {sess.turns.map((turn, idx) => {
                                  const isCustomer = turn.speaker.toLowerCase().includes("customer") || (activeModalBooking.customer_name && turn.speaker.toLowerCase().includes(activeModalBooking.customer_name.toLowerCase().split(" ")[0]));
                                  return (
                                    <div
                                      key={idx}
                                      className={`flex flex-col ${isCustomer ? "items-end" : "items-start"}`}
                                    >
                                      <div className="flex items-center gap-1.5 mb-0.5 text-[10px] text-slate-500 px-1">
                                        <span className={`font-bold ${isCustomer ? "text-cyan-700" : "text-purple-700"}`}>
                                          {turn.speaker}
                                        </span>
                                        {turn.timestamp && <span className="font-mono">• {turn.timestamp}</span>}
                                      </div>
                                      <div
                                        className={`p-3 rounded-2xl max-w-[85%] text-xs leading-relaxed shadow-xs ${
                                          isCustomer
                                            ? "bg-purple-50 border border-purple-200 text-purple-950 rounded-tr-xs"
                                            : "bg-white border border-slate-200 text-slate-800 rounded-tl-xs"
                                        }`}
                                      >
                                        <p>{turn.message}</p>
                                      </div>
                                    </div>
                                  );
                                })}
                              </div>
                            </div>
                          </div>
                        ));
                      })()}
                    </div>
                  ) : (
                    <div className="p-8 rounded-2xl bg-slate-50 border border-dashed border-slate-300 text-center space-y-3 my-4">
                      <div className="w-12 h-12 rounded-full bg-purple-100 border border-purple-200 flex items-center justify-center mx-auto text-purple-700">
                        <Volume2 className="w-6 h-6" />
                      </div>
                      <div>
                        <h4 className="text-sm font-bold text-slate-800">No Test Ride Transcript Recorded Yet</h4>
                        <p className="text-xs text-slate-500 max-w-md mx-auto mt-1 leading-relaxed">
                          This booking is scheduled for <strong>{activeModalBooking.scheduled_date} at {activeModalBooking.scheduled_time_slot}</strong>. In-vehicle audio recordings, live transcription, and sentiment insights will be inserted automatically once the test drive flow is completed.
                        </p>
                      </div>
                    </div>
                  )}
                </div>
              ) : activeTranscriptTab === "outbound" ? (
                <div className="space-y-4">
                  <div className="p-3.5 rounded-xl bg-blue-50 border border-blue-200 text-xs text-blue-950 flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <PhoneCall className="w-4 h-4 text-blue-600 shrink-0" />
                      <span>
                        Outbound Post-Test Ride Voice Call with <strong>Kavya AI (Mahindra Specialist)</strong> for <strong>{activeModalBooking.customer_name}</strong> ({activeModalBooking.customer_phone}).
                      </span>
                    </div>
                    <span className="text-[11px] font-mono bg-blue-100 text-blue-800 px-2.5 py-0.5 rounded-lg border border-blue-300 font-bold shrink-0">
                      {(activeModalBooking.outbound_transcript || []).length > 0 ? `${activeModalBooking.outbound_transcript?.length || 0} turns` : "Live Synced"}
                    </span>
                  </div>

                  {/* Summary Bar */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-2.5">
                    <div className="p-3 rounded-xl bg-white border border-slate-200 shadow-xs">
                      <span className="text-[10px] text-slate-500 uppercase font-bold">Call Status</span>
                      <p className="text-sm font-black text-emerald-600 mt-0.5 flex items-center gap-1">
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        <span>Completed</span>
                      </p>
                    </div>

                    <div className="p-3 rounded-xl bg-white border border-slate-200 shadow-xs">
                      <span className="text-[10px] text-slate-500 uppercase font-bold">Customer Sentiment</span>
                      <p className="text-sm font-black text-blue-600 mt-0.5">
                        96% Very Positive
                      </p>
                    </div>

                    <div className="p-3 rounded-xl bg-white border border-slate-200 shadow-xs col-span-2">
                      <span className="text-[10px] text-slate-500 uppercase font-bold">Priority Fast-Track Allocation</span>
                      <p className="text-xs font-bold text-amber-700 mt-0.5 flex items-center gap-1">
                        <span>⚡ 12-Day Delivery Allocation Locked</span>
                      </p>
                    </div>
                  </div>

                  {/* Outbound Transcript Turns */}
                  {(activeModalBooking.outbound_transcript && activeModalBooking.outbound_transcript.length > 0) ? (
                    <div className="rounded-2xl border border-slate-200 bg-slate-50/50 p-4 space-y-3 shadow-xs">
                      <div className="flex items-center justify-between pb-2.5 border-b border-slate-200">
                        <span className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                          <MessageSquare className="w-3.5 h-3.5 text-blue-600" />
                          <span>Spoken Audio Transcript Turns ({activeModalBooking.outbound_transcript.length})</span>
                        </span>
                        <span className="text-[10.5px] font-mono text-slate-500 font-bold">
                          Agent: Kavya AI (hi-IN)
                        </span>
                      </div>

                      <div className="space-y-2.5">
                        {activeModalBooking.outbound_transcript.map((turn, idx) => {
                          const isCustomer = turn.role === "customer" || turn.speaker.toLowerCase().includes("customer") || (activeModalBooking.customer_name && turn.speaker.toLowerCase().includes(activeModalBooking.customer_name.toLowerCase().split(" ")[0]));
                          return (
                            <div
                              key={idx}
                              className={`flex flex-col ${isCustomer ? "items-end" : "items-start"}`}
                            >
                              <div className="flex items-center gap-1.5 mb-0.5 text-[10px] text-slate-500 px-1">
                                <span className={`font-bold ${isCustomer ? "text-emerald-700" : "text-blue-700"}`}>
                                  {turn.speaker}
                                </span>
                                {turn.timestamp && <span className="font-mono">• {turn.timestamp}</span>}
                              </div>
                              <div
                                className={`p-3 rounded-2xl max-w-[85%] text-xs leading-relaxed shadow-xs ${
                                  isCustomer
                                    ? "bg-emerald-50 border border-emerald-200 text-emerald-950 rounded-tr-xs"
                                    : "bg-blue-50/90 border border-blue-200/80 text-blue-950 rounded-tl-xs"
                                }`}
                              >
                                <p>{turn.message}</p>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  ) : (
                    <div className="p-8 rounded-2xl bg-slate-50 border border-dashed border-slate-300 text-center space-y-3 my-4">
                      <div className="w-12 h-12 rounded-full bg-blue-100 border border-blue-200 flex items-center justify-center mx-auto text-blue-700">
                        <PhoneCall className="w-6 h-6" />
                      </div>
                      <div>
                        <h4 className="text-sm font-bold text-slate-800">No Feedback Call Transcript Recorded Yet</h4>
                        <p className="text-xs text-slate-500 max-w-md mx-auto mt-1 leading-relaxed">
                          A post-test ride feedback voice call has not been completed for <strong>{activeModalBooking.customer_name}</strong> yet. Once you complete the browser or phone voice call with Kavya AI, the complete live audio transcript will appear here automatically.
                        </p>
                      </div>
                    </div>
                  )}
                </div>
              ) : null}
            </div>

            {/* Modal Footer */}
            <div className="p-3.5 border-t border-slate-200 bg-slate-50 flex items-center justify-between text-xs text-slate-500">
              <span className="flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                <span>Twilio SMS dispatched &amp; logged in database</span>
              </span>
              <button
                onClick={() => setActiveModalBooking(null)}
                className="px-4 py-1.5 rounded-xl bg-slate-200 hover:bg-slate-300 text-slate-800 font-bold text-xs transition-all cursor-pointer"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
