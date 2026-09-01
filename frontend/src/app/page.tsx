"use client";

import React, { useState, useEffect } from "react";
import { Header } from "@/components/Header";
import { PreSalesShowroom } from "@/components/PreSalesShowroom";
import { SalesMobileApp } from "@/components/SalesMobileApp";
import { OutboundCallSimulator } from "@/components/OutboundCallSimulator";
import { CustomerProfileDrawer } from "@/components/CustomerProfileDrawer";
import { CustomerLeadModal } from "@/components/CustomerLeadModal";
import { ChatAvatarPanel } from "@/components/ChatAvatarPanel";
import { BrandStudioModal } from "@/components/BrandStudioModal";
import { useCustomerProfile } from "@/hooks/useCustomerProfile";
import { useLiveVoice } from "@/hooks/useLiveVoice";
import { fetchCatalog, fetchDealerships, fetchActiveBrand } from "@/lib/api";
import { DEFAULT_VEHICLES } from "@/lib/defaultCatalog";
import {
  VehicleItem,
  DealershipItem,
  TestRideInsightResponse,
  BrandCatalog
} from "@/types";
import { Zap } from "lucide-react";

export default function Home() {
  const [activeBrand, setActiveBrand] = useState<BrandCatalog | null>(null);
  const { profile, setProfile, loadProfile, setPhase } = useCustomerProfile(undefined, activeBrand?.id);
  const [vehicles, setVehicles] = useState<VehicleItem[]>(DEFAULT_VEHICLES);
  const [dealerships, setDealerships] = useState<DealershipItem[]>([]);
  const [isBrandStudioOpen, setIsBrandStudioOpen] = useState(false);

  // Dynamic brand identities
  const brandName = activeBrand?.name ? activeBrand.name.replace(/\(.*\)/, "").trim() : "Mahindra";
  const primaryColor = activeBrand?.primary_color || "#d71920";
  const agentName = activeBrand?.agent_name || activeBrand?.avatar_name || "Kavya";

  // Active Omnichannel Stage
  const [activeStage, setActiveStage] = useState<
    "presales" | "sales_app" | "outbound_call"
  >("presales");

  // Selected vehicle & insights state
  const [selectedVehicleId, setSelectedVehicleId] = useState<string>("thar_roxx");
  const [testRideInsights, setTestRideInsights] = useState<TestRideInsightResponse | null>(null);
  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const [isGlobalLeadModalOpen, setIsGlobalLeadModalOpen] = useState(false);

  // Global Chat modal state
  const [isChatOpen, setIsChatOpen] = useState(false);

  /**
   * Generic vehicle matching across ALL vehicles in the active brand catalog.
   * Matches IDs, full vehicle names, and distinct vehicle model keywords.
   */
  const matchVehicleFromText = (text: string, vehicleList: VehicleItem[]): VehicleItem | null => {
    if (!text || !vehicleList || vehicleList.length === 0) return null;
    const clean = text.toLowerCase().replace(/[^a-z0-9\s]/g, " ");

    // 1. Direct ID check (exact or normalized)
    for (const v of vehicleList) {
      const vIdNorm = v.id.toLowerCase().replace(/[^a-z0-9]/g, "");
      const cleanTokens = clean.replace(/\s+/g, "");
      if (cleanTokens.includes(vIdNorm) && vIdNorm.length >= 3) {
        return v;
      }
    }

    // 2. Sort vehicles by name length descending so specific longer names match first
    const sortedVehicles = [...vehicleList].sort((a, b) => (b.name?.length || 0) - (a.name?.length || 0));

    // 3. Full vehicle name exact substring match
    for (const v of sortedVehicles) {
      const vName = v.name.toLowerCase().replace(/[^a-z0-9\s]/g, " ").trim();
      if (vName && clean.includes(vName)) {
        return v;
      }
    }

    // 4. Significant distinct token match (e.g. 'creta', 'vitara', 'fronx', 'jimny', 'roxx', 'scorpio', 'ioniq', 'brezza', 'swift')
    for (const v of sortedVehicles) {
      const tokens = v.name
        .toLowerCase()
        .split(/[\s-_]+/)
        .filter((t) => t.length >= 3 && !["suv", "car", "all", "new", "the", "and", "edition", "door"].includes(t));
      for (const token of tokens) {
        const regex = new RegExp(`\\b${token}\\b`, "i");
        if (regex.test(clean)) {
          return v;
        }
      }
    }

    return null;
  };

  // Live Voice UI Actions Handler
  const handleUiEvent = (event: any) => {
    // 1. User speech transcription broadcast (focus carousel in real-time as customer speaks)
    if (event.type === "USER_SPEECH_TEXT" && event.text) {
      const matched = matchVehicleFromText(event.text, vehicles);
      if (matched && matched.id !== selectedVehicleId) {
        setSelectedVehicleId(matched.id);
        setActiveStage("presales");
      }
      return;
    }

    const toolName = event.tool_name || event.toolCall || "";
    const args = event.tool_args || event.args || {};
    const rawCar = args.car_name || args.vehicle_id || args.model_of_interest || args.model_name || "";

    if (toolName === "book_test_drive") {
      setIsChatOpen(true);
      if (rawCar) {
        const matched = matchVehicleFromText(rawCar, vehicles) || vehicles.find((v) => v.id === rawCar);
        if (matched) {
          setSelectedVehicleId(matched.id);
        }
      }
      return;
    }

    if (toolName === "show_vehicle_spotlight" || toolName === "switch_vehicle_showroom" || rawCar) {
      const matched = (rawCar ? matchVehicleFromText(rawCar, vehicles) : null) || (rawCar ? vehicles.find((v) => v.id === rawCar) : null);
      if (matched) {
        setSelectedVehicleId(matched.id);
        setActiveStage("presales");
      }
    }
  };

  const liveVoice = useLiveVoice(handleUiEvent);

  // Synchronize vehicle spotlight whenever customer speaks or types about a vehicle in live chat
  useEffect(() => {
    if (liveVoice.messages.length === 0) return;
    const lastMsg = liveVoice.messages[liveVoice.messages.length - 1];
    if (lastMsg.speaker === "customer" && lastMsg.text) {
      const matched = matchVehicleFromText(lastMsg.text, vehicles);
      if (matched && matched.id !== selectedVehicleId) {
        setSelectedVehicleId(matched.id);
        setActiveStage("presales");
      }
    }
  }, [liveVoice.messages, vehicles, selectedVehicleId]);

  // Sync activeStage from URL parameters (e.g. ?stage=outbound_call)
  useEffect(() => {
    if (typeof window !== "undefined") {
      const urlParams = new URLSearchParams(window.location.search);
      const stageParam = urlParams.get("stage");
      if (stageParam === "outbound_call" || stageParam === "sales_app" || stageParam === "presales") {
        setActiveStage(stageParam as any);
      }
    }
  }, []);

  useEffect(() => {
    async function loadData() {
      try {
        const [brand, dealers] = await Promise.all([
          fetchActiveBrand().catch(() => null),
          fetchDealerships().catch(() => [])
        ]);
        if (brand) {
          setActiveBrand(brand);
          if (Array.isArray(brand.vehicles) && brand.vehicles.length > 0) {
            setVehicles(brand.vehicles);
            setSelectedVehicleId(brand.vehicles[0].id);
          }
          if (Array.isArray(brand.dealerships) && brand.dealerships.length > 0) {
            setDealerships(brand.dealerships);
          } else {
            setDealerships(dealers);
          }
        } else {
          const cat = await fetchCatalog().catch(() => DEFAULT_VEHICLES);
          if (Array.isArray(cat) && cat.length > 0) {
            setVehicles(cat);
          }
          setDealerships(dealers);
        }
      } catch (e) {
        console.error("Data load error:", e);
      }
    }
    loadData();
  }, []);

  const handleCustomerIdentified = (data: any) => {
    setProfile({
      id: 1,
      customer_id: data.customer_id,
      name: data.name,
      phone: data.phone,
      city: "Mumbai",
      preferred_language: "Hinglish",
      current_phase: "PRE_SALES",
      interested_vehicle_id: selectedVehicleId,
      interested_variant: "AX7L Diesel AT 4x4",
      budget_range: "₹18 Lakh - ₹25 Lakh",
      odometer_km: 9820
    });
    setActiveStage("presales");
  };

  const handleOpenChat = (targetVehicle?: VehicleItem) => {
    if (targetVehicle) {
      setSelectedVehicleId(targetVehicle.id);
    }
    setIsChatOpen(true);
  };

  const currentVehicle = vehicles.find((v) => v.id === selectedVehicleId) || vehicles[0];

  return (
    <div
      className="min-h-screen bg-slate-50 text-slate-900 flex flex-col font-sans"
      style={{ ["--brand-primary" as any]: primaryColor }}
    >
      {/* Crisp White Header */}
      <Header
        profile={profile}
        activeStage={activeStage}
        onSelectStage={(stage) => setActiveStage(stage)}
        onOpenProfile={() => {
          if (profile) {
            setIsProfileOpen(true);
          } else {
            setIsGlobalLeadModalOpen(true);
          }
        }}
        onOpenLeadModal={() => setIsGlobalLeadModalOpen(true)}
        onOpenAvatar={() => handleOpenChat(currentVehicle)}
        brand={activeBrand}
        onOpenBrandStudio={() => setIsBrandStudioOpen(true)}
      />

      {/* Main Container */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-6 w-full flex-1">
        {/* Stage 1: Pre-Sales Car Website & Virtual Showroom */}
        {activeStage === "presales" && (
          <PreSalesShowroom
            vehicles={vehicles}
            currentProfile={profile}
            selectedVehicleId={selectedVehicleId}
            onSelectVehicleId={setSelectedVehicleId}
            onOpenChat={handleOpenChat}
            isChatOpen={isChatOpen}
            onSendChatMessage={liveVoice.sendTextMessage}
            brand={activeBrand}
            onProfileUpdated={() => {
              if (profile?.phone) loadProfile(profile.phone);
            }}
          />
        )}

        {/* Stage 2: Sales Mobile App & Test Ride Recording */}
        {activeStage === "sales_app" && (
          <SalesMobileApp
            vehicles={vehicles}
            profile={profile}
            selectedVehicleId={selectedVehicleId}
            brand={activeBrand}
            onProceedToOutboundCall={(insights) => {
              setTestRideInsights(insights);
              setActiveStage("outbound_call");
            }}
          />
        )}

        {/* Stage 3: Proactive Post-Ride Outbound Voice Call */}
        {activeStage === "outbound_call" && (
          <OutboundCallSimulator
            profile={profile}
            testRideInsights={testRideInsights}
            brand={activeBrand}
          />
        )}


      </main>

      {/* Global Floating Chat & Avatar Panel (No backdrop blur - main window remains fully visible & interactive) */}
      {isChatOpen && (
        <div
          className="fixed bottom-4 right-4 sm:bottom-6 sm:right-6 z-50 w-full sm:w-[440px] md:w-[460px] max-w-[calc(100vw-32px)] h-[88vh] max-h-[760px] flex flex-col pointer-events-auto shadow-2xl animate-in slide-in-from-bottom-6 sm:slide-in-from-right-6 duration-300"
          role="region"
          aria-label={`${agentName} AI Virtual Showroom Specialist`}
        >
          <ChatAvatarPanel
            isRecording={liveVoice.isRecording}
            rmsLevel={liveVoice.rmsLevel}
            isAssistantSpeaking={liveVoice.isAssistantSpeaking}
            messages={liveVoice.messages}
            activeLanguage={liveVoice.activeLanguage}
            onToggleRecording={(custName, custPhone, vehId) => {
              if (liveVoice.isRecording) {
                liveVoice.stopVoiceRecording();
              } else {
                liveVoice.startVoiceRecording(
                  custName || profile?.name,
                  custPhone || profile?.phone,
                  vehId || selectedVehicleId
                );
              }
            }}
            onSendMessage={liveVoice.sendTextMessage}
            onSwitchLanguage={liveVoice.switchLanguage}
            onClose={() => {
              if (liveVoice.isRecording) liveVoice.stopVoiceRecording();
              setIsChatOpen(false);
            }}
            initialCustomerName={profile?.name}
            initialCustomerPhone={profile?.phone}
            activeVehicleId={selectedVehicleId}
            brand={activeBrand}
          />
        </div>
      )}

      {/* Global Floating "Talk to Specialist" Button (Always accessible when chat closed) */}
      {!isChatOpen && (
        <div className="fixed bottom-6 right-6 z-40 animate-in fade-in slide-in-from-bottom-4 duration-300">
          <button
            onClick={() => handleOpenChat(currentVehicle)}
            className="flex items-center gap-3 px-4 py-3 rounded-full bg-[#0B0F17] hover:bg-[#151D2C] border-2 shadow-2xl text-white font-black text-xs transition-all hover:scale-105 group active:scale-95 cursor-pointer"
            style={{ borderColor: primaryColor }}
            title={`Talk to ${agentName} AI Showroom Specialist (Gemini Live)`}
          >
            <div
              className="relative w-9 h-9 rounded-full flex items-center justify-center font-black text-white text-xs border border-white/20 shrink-0 shadow-md"
              style={{ backgroundColor: primaryColor }}
            >
              {agentName.charAt(0)}
              <span className="absolute bottom-0 right-0 w-2.5 h-2.5 rounded-full bg-emerald-400 border border-slate-900 animate-pulse"></span>
            </div>
            <div className="text-left">
              <div className="flex items-center gap-2">
                <span className="text-sm font-black tracking-tight text-white">Talk to {agentName}</span>
                <span
                  className="text-[9px] px-1.5 py-0.2 rounded font-mono border uppercase font-bold text-white"
                  style={{
                    backgroundColor: `${primaryColor}30`,
                    borderColor: `${primaryColor}70`
                  }}
                >
                  Live
                </span>
              </div>
              <p className="text-[10px] text-slate-300 font-medium">{brandName} AI Specialist</p>
            </div>
          </button>
        </div>
      )}

      {/* Global Lead Identify Modal */}
      <CustomerLeadModal
        isOpen={isGlobalLeadModalOpen}
        onClose={() => setIsGlobalLeadModalOpen(false)}
        selectedVehicle={currentVehicle}
        onCustomerIdentified={handleCustomerIdentified}
      />

      {/* Brand Studio Modal for Switching Brands, Crawling URLs, and Source of Truth Image Overrides */}
      <BrandStudioModal
        isOpen={isBrandStudioOpen}
        onClose={() => setIsBrandStudioOpen(false)}
        activeBrand={activeBrand}
        onBrandChanged={(newBrand) => {
          setActiveBrand(newBrand);
          if (newBrand.vehicles && newBrand.vehicles.length > 0) {
            setVehicles(newBrand.vehicles);
            setSelectedVehicleId(newBrand.vehicles[0].id);
          }
          if (newBrand.dealerships && newBrand.dealerships.length > 0) {
            setDealerships(newBrand.dealerships);
          }
          if (profile?.phone) {
            loadProfile(profile.phone, newBrand.id);
          }
        }}
      />

      {/* Customer Profile & Transcript Drawer */}
      <CustomerProfileDrawer
        isOpen={isProfileOpen}
        onClose={() => setIsProfileOpen(false)}
        profile={profile}
        brand={activeBrand}
        onSetPhase={(phase) => setPhase(phase)}
        onRefresh={() => {
          if (profile?.phone) loadProfile(profile.phone, activeBrand?.id);
        }}
      />
    </div>
  );
}
