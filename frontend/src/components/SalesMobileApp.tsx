"use client";

import React, { useState, useEffect, useRef } from "react";
import { VehicleItem, CustomerProfile, TestRideLeadItem, TestRideInsightResponse, DealershipItem } from "@/types";
import {
  Smartphone,
  Mic,
  Square,
  Play,
  Pause,
  UploadCloud,
  CheckCircle2,
  AlertCircle,
  TrendingUp,
  User,
  Car,
  Phone,
  PhoneCall,
  Clock,
  Sparkles,
  ArrowRight,
  Shield,
  FileText,
  Volume2,
  Share2,
  Database,
  Building2,
  MapPin,
  RefreshCw,
  ChevronRight,
  Filter
} from "lucide-react";
import { fetchSalesLeads, uploadTestRideRecording, fetchDealerships, fetchLatestTestRideInsights } from "@/lib/api";

interface SalesMobileAppProps {
  vehicles: VehicleItem[];
  profile: CustomerProfile | null;
  selectedVehicleId?: string;
  onProceedToOutboundCall: (insights: TestRideInsightResponse) => void;
  isStandalone?: boolean;
}

export function SalesMobileApp({
  vehicles,
  profile,
  selectedVehicleId = "thar_roxx",
  onProceedToOutboundCall,
  isStandalone = false
}: SalesMobileAppProps) {
  // Showrooms & Filtering
  const [dealerships, setDealerships] = useState<DealershipItem[]>([]);
  const [selectedShowroom, setSelectedShowroom] = useState<string>("ALL");
  const [isLoadingLeads, setIsLoadingLeads] = useState<boolean>(false);

  // Leads & Selected Test Ride
  const [leads, setLeads] = useState<TestRideLeadItem[]>([]);
  const [selectedLead, setSelectedLead] = useState<TestRideLeadItem | null>(null);
  const [testVehicleId, setTestVehicleId] = useState<string>(selectedVehicleId);
  const [selectedVariant, setSelectedVariant] = useState<string>("AX7L Diesel AT 4x4");
  const [activeTab, setActiveTab] = useState<"leads" | "record" | "insights">("leads");

  // Mobile Microphone Recording States
  const [isRecording, setIsRecording] = useState<boolean>(false);
  const [isPaused, setIsPaused] = useState<boolean>(false);
  const [recordingSeconds, setRecordingSeconds] = useState<number>(0);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [insights, setInsights] = useState<TestRideInsightResponse | null>(null);
  const [checkedChecklist, setCheckedChecklist] = useState<Record<string, boolean>>({});

  const toggleChecklistItem = (item: string) => {
    setCheckedChecklist((prev) => ({
      ...prev,
      [item]: !prev[item]
    }));
  };

  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  // 1. Load Dealerships on Mount
  useEffect(() => {
    async function loadDealers() {
      try {
        const dealers = await fetchDealerships();
        if (dealers && dealers.length > 0) {
          setDealerships(dealers);
        }
      } catch (e) {
        console.error("Failed to load dealerships:", e);
      }
    }
    loadDealers();
  }, []);

  // 2. Load Leads whenever selected showroom changes
  const loadLeadsForShowroom = async (dealershipId: string) => {
    setIsLoadingLeads(true);
    try {
      const data = await fetchSalesLeads(dealershipId);
      if (data && data.length > 0) {
        setLeads(data);
        // Select the first lead by default
        const first = data[0];
        setSelectedLead(first);
        if (first.vehicle_id) {
          setTestVehicleId(first.vehicle_id);
          setSelectedVariant(first.variant || "Official Variant");
        }
      } else {
        setLeads([]);
        setSelectedLead(null);
      }
    } catch (e) {
      console.error("Failed to load sales leads:", e);
      setLeads([]);
    } finally {
      setIsLoadingLeads(false);
    }
  };

  useEffect(() => {
    loadLeadsForShowroom(selectedShowroom);
  }, [selectedShowroom]);

  // Auto-fetch persisted test ride insights whenever selectedLead changes
  useEffect(() => {
    async function loadPersistedInsights() {
      if (!selectedLead && !profile) {
        setInsights(null);
        setRecordingSeconds(0);
        return;
      }
      try {
        const persisted = await fetchLatestTestRideInsights({
          customer_id: selectedLead?.customer_id || profile?.customer_id,
          booking_reference: selectedLead?.booking_reference,
          phone: selectedLead?.phone || profile?.phone
        });
        if (persisted && persisted.session_id) {
          setInsights(persisted);
          setRecordingSeconds(persisted.duration_seconds || 184);
        } else {
          setInsights(null);
          setRecordingSeconds(0);
        }
      } catch (e) {
        console.debug("No existing test ride insights found for lead:", e);
        setInsights(null);
        setRecordingSeconds(0);
      }
    }
    loadPersistedInsights();
  }, [selectedLead, profile]);

  // Handle lead selection - dynamic vehicle extraction from booking
  const handleSelectLead = async (lead: TestRideLeadItem) => {
    setSelectedLead(lead);
    setCheckedChecklist({});
    setInsights(null);
    setRecordingSeconds(0);
    setIsRecording(false);
    setIsPaused(false);
    setAudioUrl(null);

    const vId = lead.vehicle_id || "thar_roxx";
    setTestVehicleId(vId);
    setSelectedVariant(lead.variant || "AX7L Diesel AT 4x4");
    setActiveTab("record");

    // Immediately check if this specific lead has persisted insights
    try {
      const persisted = await fetchLatestTestRideInsights({
        customer_id: lead.customer_id,
        booking_reference: lead.booking_reference,
        phone: lead.phone
      });
      if (persisted && persisted.session_id) {
        setInsights(persisted);
        setRecordingSeconds(persisted.duration_seconds || 184);
      } else {
        setInsights(null);
        setRecordingSeconds(0);
      }
    } catch (e) {
      setInsights(null);
      setRecordingSeconds(0);
    }
  };

  // Recording Timer
  useEffect(() => {
    if (isRecording && !isPaused) {
      timerRef.current = setInterval(() => {
        setRecordingSeconds((prev) => prev + 1);
      }, 1000);
    } else if (timerRef.current) {
      clearInterval(timerRef.current);
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [isRecording, isPaused]);

  const startRecording = async () => {
    setRecordingSeconds(0);
    setAudioUrl(null);
    setInsights(null);
    audioChunksRef.current = [];

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          audioChunksRef.current.push(e.data);
        }
      };

      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: "audio/webm" });
        const url = URL.createObjectURL(audioBlob);
        setAudioUrl(url);
      };

      mediaRecorder.start(250);
      setIsRecording(true);
      setIsPaused(false);
    } catch (err) {
      console.warn("Microphone not accessible, fallback to mock timer:", err);
      setIsRecording(true);
      setIsPaused(false);
    }
  };

  const pauseRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
      mediaRecorderRef.current.pause();
    }
    setIsPaused(true);
  };

  const resumeRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === "paused") {
      mediaRecorderRef.current.resume();
    }
    setIsPaused(false);
  };

  const stopAndProcessRecording = async () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stop();
      mediaRecorderRef.current.stream.getTracks().forEach((t) => t.stop());
    }
    setIsRecording(false);
    setIsPaused(false);
    setIsUploading(true);

    try {
      let base64Audio: string | undefined = undefined;
      const detectedMime = audioChunksRef.current[0]?.type || "audio/webm";
      if (audioChunksRef.current.length > 0) {
        const audioBlob = new Blob(audioChunksRef.current, { type: detectedMime });
        const reader = new FileReader();
        base64Audio = await new Promise<string>((resolve) => {
          reader.onloadend = () => resolve(reader.result as string);
          reader.readAsDataURL(audioBlob);
        });
      }

      const response = await uploadTestRideRecording({
        customer_id: selectedLead?.customer_id || profile?.customer_id || "CUST-AARAV-001",
        booking_reference: selectedLead?.booking_reference,
        customer_name: selectedLead?.name || profile?.name,
        vehicle_id: testVehicleId,
        variant: selectedVariant,
        sales_advisor_name: selectedLead?.dealership_name ? `Specialist (${selectedLead.dealership_name})` : "Rajesh Varma (Bayview Mahindra)",
        duration_seconds: Math.max(recordingSeconds, 1),
        audio_format: detectedMime,
        audio_base64: base64Audio,
        simulated_scenario: "test_drive_recording",
        advisor_checklist: selectedLead?.advisor_checklist
      });

      setInsights(response);
      setActiveTab("insights");
      if (selectedLead) {
        setSelectedLead({
          ...selectedLead,
          booking_status: "TestRide_Completed"
        });
      }
      loadLeadsForShowroom(selectedShowroom);
    } catch (err) {
      console.error("Error uploading test ride:", err);
    } finally {
      setIsUploading(false);
    }
  };

  const simulateTestDriveRecording = async () => {
    setIsUploading(true);
    setRecordingSeconds(184);

    try {
      const response = await uploadTestRideRecording({
        customer_id: selectedLead?.customer_id || profile?.customer_id || "CUST-AARAV-001",
        booking_reference: selectedLead?.booking_reference,
        customer_name: selectedLead?.name || profile?.name,
        vehicle_id: testVehicleId,
        variant: selectedVariant,
        sales_advisor_name: selectedLead?.dealership_name ? `Specialist (${selectedLead.dealership_name})` : "Rajesh Varma (Bayview Mahindra)",
        duration_seconds: 184,
        audio_format: "audio/wav",
        simulated_scenario: "test_drive_simulation",
        advisor_checklist: selectedLead?.advisor_checklist
      });

      setInsights(response);
      setActiveTab("insights");
      if (selectedLead) {
        setSelectedLead({
          ...selectedLead,
          booking_status: "TestRide_Completed"
        });
      }
      loadLeadsForShowroom(selectedShowroom);
    } catch (err) {
      console.error("Error simulating test ride recording:", err);
    } finally {
      setIsUploading(false);
    }
  };

  const formatTime = (secs: number) => {
    const mins = Math.floor(secs / 60);
    const s = secs % 60;
    return `${mins.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  };

  const currentVehicleObj = vehicles.find((v) => v.id === testVehicleId) || vehicles[0];

  const activeShowroomName =
    selectedShowroom === "ALL"
      ? "All Regional Dealerships"
      : dealerships.find((d) => d.id === selectedShowroom)?.name || selectedShowroom;

  const renderMobileScreen = (fullViewport: boolean) => (
    <div className={`bg-slate-50 flex flex-col text-xs shadow-inner overflow-hidden ${fullViewport ? "h-full w-full rounded-none" : "h-[640px] rounded-[32px] border border-slate-200"}`}>
      {/* App Top Bar */}
      <div className="bg-white px-4 py-3 border-b border-slate-200 flex items-center justify-between shadow-2xs">
                <div>
                  <span className="text-[9.5px] text-red-600 font-bold uppercase tracking-wider block">
                    Mahindra Field Companion
                  </span>
                  <span className="font-black text-slate-900 text-xs truncate max-w-[190px] block">
                    {activeShowroomName}
                  </span>
                </div>
                <span className="text-[9.5px] px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-200 font-bold">
                  Online
                </span>
              </div>

              {/* Mobile Tabs (Light Theme) */}
              <div className="flex border-b border-slate-200 bg-slate-100 text-[11px]">
                <button
                  onClick={() => setActiveTab("leads")}
                  className={`flex-1 py-2.5 font-bold text-center transition-all cursor-pointer ${
                    activeTab === "leads"
                      ? "text-red-700 border-b-2 border-red-600 bg-white shadow-2xs"
                      : "text-slate-600 hover:text-slate-900 hover:bg-slate-200/60"
                  }`}
                >
                  📋 Leads ({leads.length})
                </button>
                <button
                  onClick={() => setActiveTab("record")}
                  className={`flex-1 py-2.5 font-bold text-center transition-all cursor-pointer ${
                    activeTab === "record"
                      ? "text-red-700 border-b-2 border-red-600 bg-white shadow-2xs"
                      : "text-slate-600 hover:text-slate-900 hover:bg-slate-200/60"
                  }`}
                >
                  🎙️ Test Ride
                </button>
                <button
                  onClick={() => setActiveTab("insights")}
                  className={`flex-1 py-2.5 font-bold text-center transition-all cursor-pointer ${
                    activeTab === "insights"
                      ? "text-red-700 border-b-2 border-red-600 bg-white shadow-2xs"
                      : "text-slate-600 hover:text-slate-900 hover:bg-slate-200/60"
                  }`}
                >
                  ✨ Insights
                </button>
              </div>

              {/* Mobile Tab Content */}
              <div className="flex-1 overflow-y-auto p-3.5 space-y-3">
                {/* TAB 1: Leads loaded for Selected Showroom */}
                {activeTab === "leads" && (
                  <div className="space-y-3">
                    {/* Showroom filter inside mobile */}
                    <div className="p-2.5 bg-white rounded-xl border border-slate-200 shadow-2xs space-y-1.5">
                      <div className="flex items-center justify-between text-[10px] text-slate-500">
                        <span className="font-bold uppercase tracking-wider text-slate-700 flex items-center gap-1">
                          <Building2 className="w-3 h-3 text-red-600" /> Showroom Filter
                        </span>
                        <span className="font-bold text-slate-700">{leads.length} Booked</span>
                      </div>
                      <select
                        value={selectedShowroom}
                        onChange={(e) => setSelectedShowroom(e.target.value)}
                        className="w-full bg-slate-50 text-slate-900 font-bold border border-slate-300 rounded-lg px-2 py-1 text-[11px] outline-none cursor-pointer"
                      >
                        <option value="ALL">All Dealerships</option>
                        {dealerships.map((d) => (
                          <option key={d.id} value={d.id}>
                            {d.name} ({d.city})
                          </option>
                        ))}
                      </select>
                    </div>

                    {isLoadingLeads ? (
                      <div className="py-8 text-center text-slate-500 space-y-1.5">
                        <RefreshCw className="w-5 h-5 animate-spin text-red-600 mx-auto" />
                        <p className="text-xs">Loading showroom leads...</p>
                      </div>
                    ) : leads.length === 0 ? (
                      <div className="py-8 text-center text-slate-500 p-4 bg-white rounded-2xl border border-slate-200 shadow-xs space-y-1">
                        <AlertCircle className="w-6 h-6 text-amber-500 mx-auto" />
                        <p className="font-bold text-slate-900 text-xs">No bookings for this showroom yet.</p>
                        <p className="text-[10.5px] text-slate-500">
                          Select &quot;All Dealerships&quot; or book a new test ride in Pre-Sales Showroom.
                        </p>
                      </div>
                    ) : (
                      <div className="space-y-2">
                        {leads.map((lead, idx) => {
                          const isSelected = selectedLead?.customer_id === lead.customer_id;
                          return (
                            <div
                              key={idx}
                              onClick={() => handleSelectLead(lead)}
                              className={`p-3 rounded-2xl border cursor-pointer transition-all ${
                                isSelected
                                  ? "bg-red-50 border-red-500 shadow-sm ring-1 ring-red-500/40"
                                  : "bg-white border-slate-200 hover:border-slate-300 hover:shadow-xs"
                              }`}
                            >
                              <div className="flex items-center justify-between">
                                <span className="font-bold text-slate-900 text-xs">{lead.name}</span>
                                <span className={`text-[9px] px-1.5 py-0.2 rounded-full font-bold ${lead.booking_status === "TestRide_Completed" ? "bg-purple-100 text-purple-900 border border-purple-300" : "bg-emerald-100 text-emerald-800 border border-emerald-300"}`}>
                                  {lead.booking_status}
                                </span>
                              </div>

                              <p className="text-slate-500 text-[10px] mt-1 flex items-center gap-1">
                                <Phone className="w-2.5 h-2.5 text-red-600" />
                                <span>{lead.phone}</span>
                                {lead.city && <span>• 📍 {lead.city}</span>}
                              </p>

                              {/* Booked Vehicle & Variant */}
                              <div className="mt-2 p-1.5 bg-slate-50 rounded-lg border border-slate-200 space-y-0.5">
                                <div className="text-slate-900 font-bold text-[10.5px] flex items-center gap-1">
                                  <Car className="w-3 h-3 text-red-600 shrink-0" />
                                  <span className="truncate">{lead.preferred_vehicle}</span>
                                </div>
                                <div className="flex items-center justify-between text-[9.5px] text-slate-500">
                                  <span>{lead.scheduled_slot}</span>
                                  {lead.booking_reference && (
                                    <span className="font-mono text-cyan-800 bg-cyan-50 px-1.5 py-0.2 rounded border border-cyan-200 font-bold">
                                      {lead.booking_reference}
                                    </span>
                                  )}
                                </div>
                              </div>

                              {lead.booking_type === "HOME_DOORSTEP" && lead.delivery_address && (
                                <div className="mt-1 text-[9.5px] text-emerald-700 truncate font-medium">
                                  🏠 Doorstep: {lead.delivery_address}
                                </div>
                              )}

                              {lead.is_custom_checklist && (
                                <div className="mt-1.5 flex items-center gap-1 text-[9px] text-amber-800 font-bold bg-amber-50 px-2 py-0.5 rounded-md border border-amber-200">
                                  <Sparkles className="w-2.5 h-2.5 text-amber-600 shrink-0" />
                                  <span className="truncate">AI Pre-Sales Checklist ({lead.advisor_checklist?.length || 0} asks)</span>
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    )}

                    {selectedLead && (
                      <div className="pt-1">
                        <button
                          onClick={() => setActiveTab("record")}
                          className="w-full py-2.5 bg-red-600 hover:bg-red-700 text-white font-bold rounded-xl text-xs flex items-center justify-center gap-1.5 shadow-sm cursor-pointer transition-all hover:scale-102"
                        >
                          <Mic className="w-3.5 h-3.5" />
                          <span>Start Test Ride for {selectedLead.name}</span>
                        </button>
                      </div>
                    )}
                  </div>
                )}

                {/* TAB 2: Mobile Audio Recording (Light Theme) */}
                {activeTab === "record" && (
                  <div className="space-y-3">
                    {/* Customer & Booked Vehicle Header */}
                    <div className="p-3 bg-white rounded-2xl border border-slate-200 shadow-2xs space-y-1.5">
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-[10px] text-slate-500 uppercase font-bold">Customer</span>
                        <span className="font-bold text-slate-900">{selectedLead?.name || "Valued Customer"}</span>
                      </div>
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-[10px] text-slate-500 uppercase font-bold">Phone</span>
                        <span className="font-mono text-slate-700 text-[11px]">{selectedLead?.phone || "—"}</span>
                      </div>
                      <div className="pt-1.5 border-t border-slate-100 flex items-center justify-between text-xs">
                        <span className="text-[10px] text-slate-500 uppercase font-bold">Test Ride Vehicle</span>
                        <span className="font-black text-slate-900 text-[11px]">
                          {currentVehicleObj?.name}
                        </span>
                      </div>
                      <div className="flex items-center justify-between text-[10.5px]">
                        <span className="text-[10px] text-slate-500 uppercase font-bold">Booked Variant</span>
                        <span className="px-2 py-0.5 rounded bg-red-50 text-red-700 border border-red-200 font-bold">
                          {selectedVariant}
                        </span>
                      </div>
                    </div>

                    {/* Advisor Demo Checklist (Light Theme) */}
                    {(() => {
                      const activeChecklist = (selectedLead?.advisor_checklist && selectedLead.advisor_checklist.length > 0)
                        ? selectedLead.advisor_checklist
                        : (currentVehicleObj?.key_highlights && currentVehicleObj.key_highlights.length > 0
                            ? currentVehicleObj.key_highlights.slice(0, 3).map(h => `Demonstrate / Highlight ${h}`)
                            : [
                                "Demonstrate Frequency Selective Damping (FSD) / Ride Pliability",
                                "Showcase Engine / EV Throttle Acceleration & Brake Feel",
                                "Highlight Skyroof, Cockpit Twin Displays & Rear Seat Comfort"
                              ]);
                      const isCustom = selectedLead?.is_custom_checklist ?? (selectedLead?.advisor_checklist && selectedLead.advisor_checklist.length > 0);

                      return (
                        <div className="p-3 bg-amber-50/60 rounded-2xl border border-amber-200 text-[10.5px] space-y-2 text-slate-800 shadow-2xs">
                          <div className="flex items-center justify-between gap-1">
                            <span className="text-[10px] font-bold text-amber-900 uppercase flex items-center gap-1 truncate">
                              <Sparkles className="w-3 h-3 text-amber-600 shrink-0" /> Demo Checklist ({currentVehicleObj?.name || "Mahindra SUV"}):
                            </span>
                            {isCustom ? (
                              <span className="text-[8.5px] font-bold px-1.5 py-0.5 rounded bg-amber-100 text-amber-900 border border-amber-300 shrink-0 flex items-center gap-1 shadow-2xs">
                                <Sparkles className="w-2.5 h-2.5 text-amber-700" /> AI-Tailored (DB)
                              </span>
                            ) : (
                              <span className="text-[8.5px] font-bold px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200 shrink-0">
                                Static Vehicle Demo
                              </span>
                            )}
                          </div>

                          <div className="space-y-1.5 pt-0.5">
                            {activeChecklist.map((item, idx) => {
                              const isChecked = !!checkedChecklist[item];
                              return (
                                <div
                                  key={idx}
                                  onClick={() => toggleChecklistItem(item)}
                                  className={`flex items-start gap-2 p-2 rounded-lg cursor-pointer transition-all ${
                                    isChecked
                                      ? "bg-emerald-100/70 text-emerald-900 border border-emerald-300 line-through"
                                      : "bg-white hover:bg-slate-50 text-slate-800 border border-slate-200 shadow-2xs"
                                  }`}
                                >
                                  <input
                                    type="checkbox"
                                    checked={isChecked}
                                    onChange={() => {}}
                                    className="mt-0.5 accent-emerald-600 rounded cursor-pointer shrink-0"
                                  />
                                  <span className={`text-[10.5px] leading-snug ${isChecked ? "text-emerald-800/80" : "text-slate-800"}`}>
                                    {item}
                                  </span>
                                </div>
                              );
                            })}
                          </div>
                          
                          <div className="text-[9px] text-slate-500 flex items-center justify-between pt-0.5 border-t border-amber-200/60">
                            <span className="font-medium text-slate-700">
                              {Object.values(checkedChecklist).filter(Boolean).length}/{activeChecklist.length} Items Demonstrated
                            </span>
                            <span className="text-[8.5px] text-slate-500 font-mono">
                              Source: {isCustom ? "Pre-Sales Voice Asks" : "Official Catalog"}
                            </span>
                          </div>
                        </div>
                      );
                    })()}

                    {/* Audio Waveform & Timer Recorder Shell (Light Theme) */}
                    <div className="p-4 bg-white rounded-2xl border border-slate-200 shadow-xs text-center space-y-3">
                      <div className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">
                        {isRecording ? "🔴 RECORDING IN PROGRESS" : (insights ? "TEST RIDE AUDIO CAPTURED" : "READY TO CAPTURE TEST RIDE AUDIO")}
                      </div>

                      {/* Timer Display */}
                      <div className="text-3xl font-black font-mono text-slate-900 tracking-widest">
                        {formatTime(recordingSeconds)}
                      </div>

                      {/* Animated Audio Waveform */}
                      <div className="h-10 flex items-center justify-center gap-1 px-4">
                        {[4, 10, 18, 28, 14, 34, 22, 12, 30, 20, 8, 24, 16, 6].map((h, i) => (
                          <span
                            key={i}
                            className={`w-1 rounded-full transition-all duration-150 ${
                              isRecording && !isPaused ? "bg-red-600 animate-pulse" : "bg-slate-200"
                            }`}
                            style={{
                              height: isRecording && !isPaused ? `${h * 1.1}px` : "6px",
                              animationDelay: `${i * 60}ms`
                            }}
                          ></span>
                        ))}
                      </div>

                      {/* Recording Controls */}
                      <div className="flex items-center justify-center gap-2 pt-1">
                        {!isRecording ? (
                          <div className="flex flex-col sm:flex-row items-center justify-center gap-2 w-full">
                            <button
                              onClick={startRecording}
                              className="w-full sm:w-auto px-4 py-2.5 bg-red-600 hover:bg-red-700 text-white font-bold rounded-xl text-xs flex items-center justify-center gap-2 shadow-xs cursor-pointer transition-all hover:scale-102"
                            >
                              <Mic className="w-4 h-4" />
                              <span>Start Ride Recording</span>
                            </button>

                            <button
                              onClick={simulateTestDriveRecording}
                              disabled={isUploading}
                              className="w-full sm:w-auto px-4 py-2.5 bg-purple-700 hover:bg-purple-800 text-white font-bold rounded-xl text-xs flex items-center justify-center gap-2 shadow-xs cursor-pointer transition-all hover:scale-102 disabled:opacity-50"
                            >
                              <Sparkles className="w-4 h-4 text-purple-200 animate-pulse" />
                              <span>Simulate Test Drive Recording</span>
                            </button>
                          </div>
                        ) : (
                          <>
                            {isPaused ? (
                              <button
                                onClick={resumeRecording}
                                className="p-2.5 bg-amber-600 hover:bg-amber-700 text-white rounded-full cursor-pointer shadow-xs"
                                title="Resume"
                              >
                                <Play className="w-4 h-4" />
                              </button>
                            ) : (
                              <button
                                onClick={pauseRecording}
                                className="p-2.5 bg-slate-200 hover:bg-slate-300 text-slate-800 rounded-full border border-slate-300 cursor-pointer shadow-2xs"
                                title="Pause"
                              >
                                <Pause className="w-4 h-4" />
                              </button>
                            )}

                            <button
                              onClick={stopAndProcessRecording}
                              className="px-4 py-2.5 bg-red-600 hover:bg-red-700 text-white font-bold rounded-full text-xs flex items-center gap-1.5 shadow-sm cursor-pointer"
                            >
                              <Square className="w-3.5 h-3.5" />
                              <span>Stop &amp; Upload to GCS</span>
                            </button>
                          </>
                        )}
                      </div>
                    </div>

                    {isUploading && (
                      <div className="p-3.5 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 text-center space-y-1 shadow-2xs">
                        <UploadCloud className="w-5 h-5 animate-bounce text-amber-600 mx-auto" />
                        <p className="font-bold text-xs">Uploading Audio to Cloud Storage &amp; Analyzing...</p>
                        <p className="text-[10px] text-amber-800">Executing Gemini Speaker Diarization &amp; Sentiment AI</p>
                      </div>
                    )}
                  </div>
                )}

                {/* TAB 3: AI Insights (Light Theme) */}
                {activeTab === "insights" && (
                  <div className="space-y-3 text-left">
                    {insights ? (
                      <>
                        <div className="p-3 rounded-2xl bg-white border border-slate-200 shadow-xs space-y-2">
                          <div className="flex items-center justify-between text-xs">
                            <span className="font-bold text-slate-900 truncate">{insights.vehicle_name}</span>
                            <span className="font-mono text-emerald-700 font-bold bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200 shrink-0">
                              {Math.round(insights.purchase_intent_score * 100)}% Intent
                            </span>
                          </div>
                          <div className="p-2 rounded-lg bg-slate-50 border border-slate-200 space-y-1">
                            <span className="text-[9px] font-bold text-purple-700 uppercase tracking-wider block">GCS Audio Storage:</span>
                            <div className="font-mono text-[9px] text-slate-800 break-all select-all font-semibold">
                              {insights.gcs_uri}
                            </div>
                          </div>
                        </div>

                        {/* Speaker Identified Test Ride Transcript */}
                        <div className="p-3 rounded-2xl bg-white border border-slate-200 shadow-xs space-y-2">
                          <div className="flex items-center justify-between">
                            <span className="text-[10px] font-bold text-purple-800 uppercase flex items-center gap-1">
                              <Volume2 className="w-3 h-3 text-purple-600" /> Test Ride Audio Transcript:
                            </span>
                            <span className="text-[9px] font-mono text-slate-500">{insights.duration_seconds}s</span>
                          </div>
                          <div className="space-y-1.5 max-h-48 overflow-y-auto text-[10px] font-mono pr-1">
                            {insights.transcript.split("\n").map((line, idx) => {
                              if (!line.trim()) return null;
                              const isAdv = line.toLowerCase().includes("advisor");
                              return (
                                <div
                                  key={idx}
                                  className={`p-2 rounded-lg border leading-relaxed ${
                                    isAdv
                                      ? "bg-purple-50 border-purple-200 text-purple-950"
                                      : "bg-cyan-50 border-cyan-200 text-cyan-950"
                                  }`}
                                >
                                  {line}
                                </div>
                              );
                            })}
                          </div>
                        </div>

                        <div className="p-3 rounded-2xl bg-emerald-50 border border-emerald-200 space-y-1 shadow-2xs">
                          <span className="text-[10px] font-bold text-emerald-800 uppercase flex items-center gap-1">
                            ✓ Loved Features (From Spoken Audio):
                          </span>
                          {insights.loved_features && insights.loved_features.length > 0 ? (
                            <ul className="text-[10px] text-slate-700 list-disc pl-4 space-y-0.5">
                              {insights.loved_features.map((f, i) => (
                                <li key={i}>{f}</li>
                              ))}
                            </ul>
                          ) : (
                            <p className="text-[10px] text-slate-600 pl-1">Overall test drive vehicle performance</p>
                          )}
                        </div>

                        <div className="p-3 rounded-2xl bg-amber-50 border border-amber-200 space-y-1 shadow-2xs">
                          <span className="text-[10px] font-bold text-amber-900 uppercase flex items-center gap-1">
                            Objections &amp; Concerns (From Spoken Audio):
                          </span>
                          {insights.objections_raised && insights.objections_raised.length > 0 ? (
                            <ul className="text-[10px] text-slate-700 list-disc pl-4 space-y-0.5">
                              {insights.objections_raised.map((o, i) => (
                                <li key={i}>{o}</li>
                              ))}
                            </ul>
                          ) : (
                            <p className="text-[10px] text-emerald-800 font-medium pl-1">
                              ✓ No major objections or concerns raised during the test drive.
                            </p>
                          )}
                        </div>

                        {onProceedToOutboundCall && (
                          <button
                            onClick={() => onProceedToOutboundCall(insights)}
                            className="w-full py-2.5 bg-red-600 hover:bg-red-700 text-white font-bold rounded-xl text-xs flex items-center justify-center gap-1.5 shadow-sm cursor-pointer"
                          >
                            <PhoneCall className="w-3.5 h-3.5" />
                            <span>Proceed to Outbound Call (Stage 3)</span>
                          </button>
                        )}
                      </>
                    ) : (
                      <div className="py-8 text-center text-slate-400">
                        <AlertCircle className="w-6 h-6 text-slate-400 mx-auto mb-1" />
                        <p className="text-xs">Complete a test drive recording first to generate AI insights.</p>
                      </div>
                    )}
                  </div>
                )}
              </div>
    </div>
  );

  if (isStandalone) {
    return (
      <div className="w-full h-full bg-slate-50 flex flex-col text-xs overflow-hidden">
        {renderMobileScreen(true)}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Stage Header Banner with Showroom Selector (Light Theme) */}
      <div className="bg-white p-6 rounded-3xl border border-slate-200 shadow-xs flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4">
        <div className="space-y-2">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-red-50 text-red-700 border border-red-200 text-xs font-bold uppercase tracking-wider">
            <Smartphone className="w-3.5 h-3.5 text-red-600" />
            Stage 2: Sales Advisor Companion &amp; Test Ride Recording
          </div>
          <h2 className="text-xl md:text-2xl font-black text-slate-900 tracking-tight flex items-center gap-2">
            <span>Advisor Field Companion &amp; GCS Audio Insights Engine</span>
          </h2>
          <p className="text-xs md:text-sm text-slate-600 max-w-2xl leading-relaxed">
            Select a showroom to load verified customer test drive bookings. The advisor companion automatically pulls the customer&apos;s booked vehicle from the database and captures in-vehicle audio with AI speaker diarization.
          </p>

          {/* Showroom Selector Dropdown in Banner */}
          <div className="flex flex-wrap items-center gap-2 pt-1">
            <div className="flex items-center gap-1.5 text-xs text-slate-700 font-bold bg-slate-50 px-3 py-1.5 rounded-xl border border-slate-200 shadow-xs">
              <Building2 className="w-3.5 h-3.5 text-red-600 shrink-0" />
              <span>Select Showroom:</span>
              <select
                value={selectedShowroom}
                onChange={(e) => setSelectedShowroom(e.target.value)}
                className="bg-white text-slate-900 font-bold border border-slate-300 rounded-lg px-2.5 py-1 text-xs outline-none focus:border-red-500 cursor-pointer shadow-2xs"
              >
                <option value="ALL">🏢 All Showrooms ({dealerships.length} Dealerships)</option>
                {dealerships.map((dealer) => (
                  <option key={dealer.id} value={dealer.id}>
                    {dealer.name} ({dealer.city})
                  </option>
                ))}
              </select>
            </div>

            <span className="text-[11px] font-mono font-bold text-slate-700 bg-slate-100 px-3 py-1 rounded-lg border border-slate-200">
              {leads.length} Booked Lead{leads.length !== 1 ? "s" : ""} Available
            </span>
          </div>
        </div>

        {insights && (
          <button
            onClick={() => onProceedToOutboundCall(insights)}
            className="bg-red-600 hover:bg-red-700 text-white text-xs md:text-sm font-bold px-4 py-2.5 rounded-xl transition-all shadow-sm flex items-center gap-2 shrink-0 cursor-pointer hover:scale-102"
          >
            <span>Proceed to Stage 3: Outbound Call</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Grid: 5 Cols Mobile Phone Frame | 7 Cols Audio AI Insights Dashboard */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left 5 Cols: Realistic Mobile Device View */}
        <div className="lg:col-span-5 flex justify-center">
          <div className="w-full max-w-sm bg-slate-900 rounded-[42px] p-3 shadow-2xl border-[6px] border-slate-700 relative">
            {/* Phone Notch / Dynamic Island */}
            <div className="w-28 h-5 bg-black rounded-full mx-auto mb-2 flex items-center justify-center gap-1.5 shadow-inner">
              <span className="w-2 h-2 rounded-full bg-neutral-800"></span>
              <span className="w-2 h-2 rounded-full bg-blue-900/80"></span>
            </div>

            {renderMobileScreen(false)}
          </div>
        </div>

        {/* Right 7 Cols: Detailed In-Vehicle Test Ride Audio & Insights Panel (Crisp Light Theme) */}
        <div className="lg:col-span-7 space-y-4 text-left">
          {/* Active Vehicle Card (From Booking API) */}
          <div className="p-5 rounded-2xl bg-white border border-slate-200 shadow-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="px-2.5 py-0.5 rounded-full bg-red-50 text-red-700 border border-red-200 font-mono text-[10px] font-bold uppercase">
                  Active Test Ride Vehicle
                </span>
                <span className="text-[11px] font-mono text-cyan-800 font-bold bg-cyan-50 px-2 py-0.5 rounded border border-cyan-200">
                  {selectedLead?.booking_reference || "LIVE BOOKING"}
                </span>
              </div>
              <h3 className="text-xl font-black text-slate-900">{currentVehicleObj.name}</h3>
              <p className="text-xs text-amber-800 font-bold">
                Variant: {selectedVariant} • Showroom: {selectedLead?.dealership_name || activeShowroomName}
              </p>
              <p className="text-[11px] text-slate-600">
                Customer: <strong className="text-slate-900">{selectedLead?.name || "Aarav Sharma"}</strong> ({selectedLead?.phone || "+91 98201 23456"})
              </p>
            </div>

            {/* Vehicle Image */}
            <div className="relative w-36 h-24 rounded-xl overflow-hidden border border-slate-200 bg-slate-100 shrink-0 shadow-2xs">
              <img
                src={
                  currentVehicleObj.hero_image ||
                  currentVehicleObj.image_url ||
                  `/assets/${currentVehicleObj.id.replace("_", "-")}.jpg`
                }
                alt={currentVehicleObj.name}
                className="w-full h-full object-cover"
                onError={(e) => {
                  e.currentTarget.src = "/assets/thar-roxx.jpg";
                }}
              />
            </div>
          </div>

          {/* AI Insights & Audio STT Transcript Details (Light Theme) */}
          {insights ? (
            <div className="space-y-4 animate-in fade-in duration-300">
              {/* Score Metric Cards */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="p-3.5 rounded-2xl bg-white border border-slate-200 shadow-xs">
                  <span className="text-[10px] text-slate-500 uppercase font-bold">Customer Sentiment</span>
                  <p className="text-xl font-black text-emerald-600 mt-1">
                    {Math.round(insights.customer_sentiment_score * 100)}% Positive
                  </p>
                </div>
                <div className="p-3.5 rounded-2xl bg-white border border-slate-200 shadow-xs">
                  <span className="text-[10px] text-slate-500 uppercase font-bold">Purchase Intent</span>
                  <p className="text-xl font-black text-cyan-600 mt-1">
                    {Math.round(insights.purchase_intent_score * 100)}% Ready
                  </p>
                </div>
                <div className="p-3.5 rounded-2xl bg-white border border-slate-200 shadow-xs">
                  <span className="text-[10px] text-slate-500 uppercase font-bold">Advisor Pitch Score</span>
                  <p className="text-xl font-black text-amber-600 mt-1">
                    {insights.advisor_pitch_score} / 10
                  </p>
                </div>
                <div className="p-3.5 rounded-2xl bg-white border border-slate-200 shadow-xs">
                  <span className="text-[10px] text-slate-500 uppercase font-bold">GCS Storage Status</span>
                  <p className="text-xs font-mono font-bold text-purple-700 mt-2 truncate">
                    Uploaded (GCS)
                  </p>
                </div>
              </div>

              {/* Full In-Vehicle Transcript Box */}
              <div className="p-5 rounded-2xl bg-white border border-slate-200 shadow-xs space-y-3">
                <div className="flex items-center justify-between border-b border-slate-200 pb-2.5">
                  <h4 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                    <Volume2 className="w-4 h-4 text-purple-600" />
                    <span>In-Vehicle Test Ride Audio STT Transcript (Multi-Turn)</span>
                  </h4>
                  <span className="text-[10px] font-mono text-slate-500 font-bold bg-slate-100 px-2 py-0.5 rounded">
                    Duration: {insights.duration_seconds}s
                  </span>
                </div>

                <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 text-xs font-mono text-slate-800 whitespace-pre-wrap leading-relaxed max-h-56 overflow-y-auto">
                  {insights.transcript}
                </div>
              </div>

              {/* GCS URI Card */}
              <div className="p-3.5 rounded-2xl bg-purple-50/70 border border-purple-200 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 shadow-2xs">
                <div>
                  <span className="text-[10px] font-bold text-purple-800 uppercase tracking-wider block">GCS Cloud Storage Audio Path:</span>
                  <p className="font-mono text-xs text-purple-950 break-all select-all mt-0.5 font-bold">{insights.gcs_uri}</p>
                </div>
                <span className="text-[9px] font-bold font-mono px-2 py-0.5 rounded bg-purple-100 text-purple-800 border border-purple-300 shrink-0">
                  WAV 16kHz
                </span>
              </div>

              {/* Loved Features & Objections Split Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div className="p-4 rounded-2xl bg-emerald-50/80 border border-emerald-200 space-y-2 shadow-2xs">
                  <span className="text-xs font-bold text-emerald-800 uppercase flex items-center gap-1">
                    ✓ Loved Features (From Spoken Audio) ({insights.loved_features?.length || 0})
                  </span>
                  {insights.loved_features && insights.loved_features.length > 0 ? (
                    <ul className="text-xs text-slate-700 space-y-1 list-disc pl-4">
                      {insights.loved_features.map((f, i) => (
                        <li key={i}>{f}</li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-xs text-slate-600 pl-1">Overall test drive vehicle performance</p>
                  )}
                </div>

                <div className="p-4 rounded-2xl bg-amber-50/80 border border-amber-200 space-y-2 shadow-2xs">
                  <span className="text-xs font-bold text-amber-900 uppercase flex items-center gap-1">
                    ⚠ Objections &amp; Concerns (From Spoken Audio) ({insights.objections_raised?.length || 0})
                  </span>
                  {insights.objections_raised && insights.objections_raised.length > 0 ? (
                    <ul className="text-xs text-slate-700 space-y-1 list-disc pl-4">
                      {insights.objections_raised.map((o, i) => (
                        <li key={i}>{o}</li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-xs text-emerald-800 font-medium pl-1">
                      ✓ No major objections or concerns raised during the test drive.
                    </p>
                  )}
                </div>
              </div>

              {/* Coaching Feedback & Next Action */}
              <div className="p-4 rounded-2xl bg-purple-50/80 border border-purple-200 space-y-2 shadow-2xs">
                <h4 className="text-xs font-bold text-purple-900 flex items-center gap-1.5">
                  <TrendingUp className="w-4 h-4 text-purple-600" />
                  <span>AI Coaching Feedback for Sales Advisor:</span>
                </h4>
                <p className="text-xs text-slate-800 leading-relaxed">
                  {insights.advisor_coaching_feedback}
                </p>
                <div className="pt-2 border-t border-purple-200 text-xs text-amber-900 font-bold">
                  Recommended Follow-up: {insights.recommended_action}
                </div>
              </div>

              {onProceedToOutboundCall && (
                <div className="pt-2">
                  <button
                    onClick={() => onProceedToOutboundCall(insights)}
                    className="w-full py-3.5 bg-red-600 hover:bg-red-700 text-white font-black rounded-xl text-sm flex items-center justify-center gap-2 shadow-md transition-all hover:scale-101 cursor-pointer"
                  >
                    <PhoneCall className="w-4 h-4" />
                    <span>Proceed to Proactive Outbound Call Simulator (Stage 3)</span>
                  </button>
                </div>
              )}
            </div>
          ) : (
            <div className="p-8 rounded-2xl bg-white border border-dashed border-slate-300 text-center space-y-3 shadow-xs">
              <div className="w-12 h-12 rounded-full bg-slate-100 border border-slate-200 flex items-center justify-center mx-auto text-slate-500">
                <Mic className="w-6 h-6 text-red-600" />
              </div>
              <h4 className="text-base font-bold text-slate-900">Ready for Test Ride Audio Capture</h4>
              <p className="text-xs text-slate-500 max-w-md mx-auto leading-relaxed">
                Select a customer lead on the mobile phone interface, tap &quot;Start Ride Recording&quot; to begin in-cabin audio recording, and upload to GCS to generate STT transcript and buyer sentiment analytics.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
