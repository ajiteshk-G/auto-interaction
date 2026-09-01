"use client";

import React, { useState, useEffect, useRef } from "react";
import { VehicleItem, CustomerProfile, BrandCatalog } from "@/types";
import { useLiveVoice } from "@/hooks/useLiveVoice";
import { ChatAvatarPanel } from "@/components/ChatAvatarPanel";
import { TestDriveModal } from "@/components/TestDriveModal";
import { CustomerLeadModal } from "@/components/CustomerLeadModal";
import { CustomerProfileDrawer } from "@/components/CustomerProfileDrawer";
import { ComparisonMatrix } from "@/components/ComparisonMatrix";
import { fetchCustomerSessions } from "@/lib/api";
import { getSmartPeerVehicle } from "@/lib/compareHelper";
import {
  Car,
  MessageSquare,
  Sparkles,
  Calendar,
  Layers,
  Shield,
  Zap,
  Award,
  History,
  Bot,
  ChevronLeft,
  ChevronRight,
  LayoutGrid,
  SlidersHorizontal,
  ArrowUpRight,
  CheckCircle2
} from "lucide-react";

interface PreSalesShowroomProps {
  vehicles: VehicleItem[];
  currentProfile: CustomerProfile | null;
  onProfileUpdated: () => void;
  selectedVehicleId: string;
  onSelectVehicleId: (id: string) => void;
  onOpenChat: (targetVehicle?: VehicleItem) => void;
  isChatOpen: boolean;
  onSendChatMessage?: (text: string) => void;
  brand?: BrandCatalog | null;
}

export function PreSalesShowroom({
  vehicles,
  currentProfile,
  onProfileUpdated,
  selectedVehicleId,
  onSelectVehicleId,
  onOpenChat,
  isChatOpen,
  onSendChatMessage,
  brand
}: PreSalesShowroomProps) {
  const [selectedCategory, setSelectedCategory] = useState<string>("ALL");

  // Dynamic brand identities
  const brandName = brand?.name ? brand.name.replace(/\(.*\)/, "").trim() : "Mahindra";
  const primaryColor = brand?.primary_color || "#d71920";
  const agentName =
    brand?.agent_name ||
    (brandName.toLowerCase().includes("hyundai")
      ? "Aarav"
      : brandName.toLowerCase().includes("maruti")
      ? "Rohan"
      : "Kabir");

  // Layout mode: "carousel" (like reference app) or "grid"
  const [viewMode, setViewMode] = useState<"carousel" | "grid">("carousel");

  // Modals state
  const [isTestDriveOpen, setIsTestDriveOpen] = useState(false);
  const [isCompareOpen, setIsCompareOpen] = useState(false);
  const [isLeadModalOpen, setIsLeadModalOpen] = useState(false);
  const [isHistoryModalOpen, setIsHistoryModalOpen] = useState(false);
  const [modalVehicle, setModalVehicle] = useState<VehicleItem | null>(null);
  const [compareVehicle2, setCompareVehicle2] = useState<VehicleItem | null>(null);
  const [pastSessions, setPastSessions] = useState<any[]>([]);

  // Carousel ref for horizontal scrolling
  const carouselRef = useRef<HTMLDivElement>(null);
  const heroCardRef = useRef<HTMLDivElement>(null);
  const [showStickyBar, setShowStickyBar] = useState(false);

  // Active Session
  const [activeSession, setActiveSession] = useState<{
    customer_id: string;
    name: string;
    phone: string;
    session_id: string;
    session_type: "LIVE_CALL" | "CHAT_BOT";
    is_returning: boolean;
  } | null>(null);

  // Track scroll position to show sticky vehicle bar when hero is out of view
  useEffect(() => {
    const handleScroll = () => {
      if (heroCardRef.current) {
        const rect = heroCardRef.current.getBoundingClientRect();
        setShowStickyBar(rect.bottom < 120);
      }
    };
    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  // Auto-scroll the vehicle carousel to keep the active vehicle centered
  useEffect(() => {
    const card = document.getElementById(`carousel-card-${selectedVehicleId}`);
    if (card && carouselRef.current) {
      card.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "center" });
    }
  }, [selectedVehicleId]);

  // Compute categories dynamically from vehicles
  const categories = React.useMemo(() => {
    const rawCategories = Array.from(
      new Set(vehicles.map((v) => v.category || "SUV").filter(Boolean))
    );
    return [
      { id: "ALL", label: `All Lineup (${vehicles.length})` },
      ...rawCategories.map((cat) => ({
        id: cat,
        label: `${cat} (${vehicles.filter((v) => v.category === cat).length})`
      }))
    ];
  }, [vehicles]);

  const filteredVehicles = selectedCategory === "ALL"
    ? vehicles
    : vehicles.filter((v) => v.category === selectedCategory);

  const currentVehicle = vehicles.find((v) => v.id === selectedVehicleId) || vehicles[0];
  const isElectric = currentVehicle?.category === "Born Electric SUV";

  const handleStartConsultation = (vehicle?: VehicleItem) => {
    const target = vehicle || currentVehicle;
    if (vehicle) onSelectVehicleId(vehicle.id);
    onOpenChat(target);
  };

  const handleCustomerIdentified = (data: any) => {
    setActiveSession({
      customer_id: data.customer_id,
      name: data.name,
      phone: data.phone,
      session_id: data.session_id,
      session_type: data.session_type,
      is_returning: data.is_returning
    });
    setIsLeadModalOpen(false);
    onProfileUpdated();
    onOpenChat(currentVehicle);
  };

  const handleOpenTestDrive = (targetVehicle: VehicleItem) => {
    setModalVehicle(targetVehicle);
    setIsTestDriveOpen(true);
  };

  const handleOpenCompare = (targetVehicle: VehicleItem) => {
    setModalVehicle(targetVehicle);
    const peer = getSmartPeerVehicle(targetVehicle, vehicles);
    setCompareVehicle2(peer);
    setIsCompareOpen(true);
  };

  const loadPastSessions = async () => {
    const phoneOrId = activeSession?.phone || currentProfile?.phone || "+919820155432";
    try {
      const sess = await fetchCustomerSessions(phoneOrId);
      setPastSessions(sess);
      setIsHistoryModalOpen(true);
    } catch (e) {
      console.error("Error loading sessions:", e);
    }
  };

  const scrollCarousel = (direction: "left" | "right") => {
    if (carouselRef.current) {
      const offset = direction === "left" ? -320 : 320;
      carouselRef.current.scrollBy({ left: offset, behavior: "smooth" });
    }
  };

  const scrollToHero = () => {
    if (heroCardRef.current) {
      heroCardRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  };

  return (
    <div className="space-y-6 pb-20 relative">
      {/* 1. DOCKED STICKY VEHICLE SPOTLIGHT STRIP (Appears whenever scrolled past hero) */}
      <div
        className={`fixed top-16 left-0 right-0 z-30 bg-white/95 backdrop-blur-md border-b border-slate-200 shadow-md transition-all duration-300 transform ${
          showStickyBar ? "translate-y-0 opacity-100" : "-translate-y-full opacity-0 pointer-events-none"
        }`}
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-2.5 flex items-center justify-between gap-3">
          {/* Selected Vehicle Thumbnail & Title */}
          <div
            onClick={scrollToHero}
            className="flex items-center gap-3 cursor-pointer group"
          >
            <div className="w-12 h-9 bg-slate-100 rounded-lg p-1 border border-slate-200 flex items-center justify-center shrink-0">
              <img
                src={currentVehicle.hero_image}
                alt={currentVehicle.name}
                className="max-h-full max-w-full object-contain"
              />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-black text-slate-900 group-hover:opacity-80 transition-opacity" style={{ color: primaryColor }}>
                  {currentVehicle.name}
                </span>
                <span
                  className={`text-[9px] font-extrabold px-2 py-0.2 rounded-full uppercase ${
                    isElectric
                      ? "bg-cyan-100 text-cyan-800 border border-cyan-200"
                      : "bg-slate-100 text-slate-800 border border-slate-200"
                  }`}
                >
                  {currentVehicle.category}
                </span>
              </div>
              <p className="text-[11px] font-bold" style={{ color: primaryColor }}>
                {currentVehicle.price_range.split(" (")[0]}
              </p>
            </div>
          </div>

          {/* Quick Actions Strip */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => handleStartConsultation(currentVehicle)}
              style={{ backgroundColor: primaryColor }}
              className="text-white px-3 py-1.5 rounded-lg text-xs font-bold flex items-center gap-1.5 shadow-xs transition-all hover:opacity-90"
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Ask {agentName}</span>
            </button>

            <button
              onClick={() => handleOpenTestDrive(currentVehicle)}
              className="bg-slate-900 hover:bg-slate-800 text-white px-3 py-1.5 rounded-lg text-xs font-bold flex items-center gap-1.5 transition-all"
            >
              <Calendar className="w-3.5 h-3.5 text-amber-400" />
              <span className="hidden md:inline">Book Test Drive</span>
            </button>

            <button
              onClick={() => handleOpenCompare(currentVehicle)}
              className="bg-slate-100 hover:bg-slate-200 text-slate-700 px-3 py-1.5 rounded-lg text-xs font-bold flex items-center gap-1.5 border border-slate-200 transition-all"
            >
              <Layers className="w-3.5 h-3.5 text-cyan-600" />
              <span className="hidden md:inline">Compare</span>
            </button>
          </div>
        </div>
      </div>

      {/* Top Experience Sub-Header: Single clean Transcripts link */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-3 border-b border-slate-200">
        <div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full animate-pulse" style={{ backgroundColor: primaryColor }}></span>
            <span className="text-xs font-black uppercase tracking-widest text-slate-800">
              {brandName} • Virtual Experience Center
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Interactive Co-Browsing Showroom with {agentName} AI Specialist & Live Audio Stream
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* View Mode Toggle: Horizontal Carousel vs Full Grid */}
          <div className="flex items-center bg-slate-100 p-0.5 rounded-xl border border-slate-200">
            <button
              onClick={() => setViewMode("carousel")}
              className={`p-1.5 rounded-lg text-xs font-bold flex items-center gap-1 transition-all ${
                viewMode === "carousel" ? "bg-white text-slate-900 shadow-xs" : "text-slate-500 hover:text-slate-900"
              }`}
              title="Carousel Mode (Selected Car always in view)"
            >
              <SlidersHorizontal className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Carousel</span>
            </button>

            <button
              onClick={() => setViewMode("grid")}
              className={`p-1.5 rounded-lg text-xs font-bold flex items-center gap-1 transition-all ${
                viewMode === "grid" ? "bg-white text-slate-900 shadow-xs" : "text-slate-500 hover:text-slate-900"
              }`}
              title="Grid Mode"
            >
              <LayoutGrid className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Grid</span>
            </button>
          </div>

          <button
            onClick={loadPastSessions}
            className="px-3 py-1.5 rounded-xl border border-slate-200 hover:border-slate-300 bg-white text-xs font-bold text-slate-700 hover:text-slate-900 flex items-center gap-1.5 transition-all shadow-xs"
          >
            <History className="w-3.5 h-3.5 text-slate-500" />
            <span className="hidden sm:inline">Past Transcripts</span>
          </button>
        </div>
      </div>

      {/* Showroom Showcase Container */}
      <div className="w-full space-y-6">
        <div className="w-full space-y-6">
          {/* Active Car Hero Spotlight Stage Card */}
          <div
            ref={heroCardRef}
            className="bg-white rounded-3xl border border-slate-200 shadow-xl overflow-hidden p-6 space-y-5 transition-all duration-300"
          >
            {/* Top Stage Header */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span
                  className={`text-[10px] font-extrabold px-3 py-1 rounded-full uppercase tracking-wider flex items-center gap-1 shadow-xs ${
                    isElectric
                      ? "bg-cyan-100 text-cyan-800 border border-cyan-300"
                      : "bg-slate-100 text-slate-800 border border-slate-200"
                  }`}
                >
                  {isElectric ? <Zap className="w-3 h-3 text-cyan-600" /> : <Shield className="w-3 h-3 text-slate-600" />}
                  {currentVehicle.category}
                </span>

                <span className="text-[10px] font-bold px-2.5 py-1 rounded-full bg-slate-100 text-slate-700 border border-slate-200">
                  {currentVehicle.seating_capacity}
                </span>
              </div>

              <div className="flex items-center gap-2">
                {currentVehicle?.is_custom_source_of_truth && (
                  <span className="text-[10px] font-bold text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-full border border-emerald-300 flex items-center gap-1">
                    <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                    Source of Truth (User Upload)
                  </span>
                )}
                <span className="text-[10px] font-bold text-slate-700 bg-slate-100 px-2.5 py-1 rounded-full border border-slate-200">
                  {currentVehicle.category || "SUV"}
                </span>
              </div>
            </div>

            {/* Vehicle Title & Tagline + Avatar Quick Action Banner */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <div className="text-[10px] font-extrabold uppercase tracking-widest" style={{ color: primaryColor }}>Active Spotlight</div>
                <h2 className="text-2xl font-black text-slate-900 tracking-tight mt-0.5">
                  {currentVehicle.name}
                </h2>
                <p className="text-xs text-slate-600 mt-1 line-clamp-2 leading-relaxed font-medium">
                  {currentVehicle.tagline}
                </p>
              </div>

              <button
                onClick={() => handleStartConsultation(currentVehicle)}
                className="self-start sm:self-auto flex items-center gap-3 p-2.5 pr-4 rounded-2xl bg-gradient-to-r from-slate-900 via-slate-850 to-slate-900 border border-cyan-500/30 hover:border-cyan-400 text-white shadow-lg transition-all hover:scale-102 cursor-pointer group text-left shrink-0"
                title={`Ask ${agentName} about ${currentVehicle.name}`}
              >
                <div
                  className="relative w-10 h-10 rounded-full flex items-center justify-center font-black text-white text-sm shadow-md border-2 border-white/20 shrink-0"
                  style={{ backgroundColor: primaryColor }}
                >
                  {agentName.charAt(0)}
                  <span className="absolute bottom-0 right-0 w-2.5 h-2.5 rounded-full bg-emerald-400 border-2 border-slate-900 animate-pulse"></span>
                </div>
                <div>
                  <div className="flex items-center gap-1.5">
                    <span className="text-xs font-black text-white group-hover:text-cyan-300 transition-colors">
                      Consult with {agentName}
                    </span>
                    <span className="text-[9px] font-mono text-cyan-400 bg-cyan-950/80 px-1.5 py-0.2 rounded border border-cyan-500/30">
                      LIVE
                    </span>
                  </div>
                  <p className="text-[10px] text-slate-400 group-hover:text-slate-300">
                    Ask about specs, comparisons &amp; booking
                  </p>
                </div>
              </button>
            </div>

            {/* Studio Presentation Canvas */}
            <div className="relative h-64 sm:h-72 w-full bg-gradient-to-b from-slate-100/90 via-slate-50 to-white rounded-2xl border border-slate-200/80 flex items-center justify-center p-4 overflow-hidden car-reflection">
              <img
                key={currentVehicle.id}
                src={currentVehicle.hero_image}
                alt={currentVehicle.name}
                className="max-h-full max-w-full object-contain filter drop-shadow-2xl transition-all duration-500 hover:scale-105"
              />
            </div>

            {/* Specs Strip */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="p-3 rounded-2xl bg-slate-50 border border-slate-200/80">
                <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Ex-Showroom Price</p>
                <p className="text-sm font-black text-slate-900 mt-0.5">{currentVehicle.price_range.split(" (")[0]}</p>
              </div>

              <div className="p-3 rounded-2xl bg-slate-50 border border-slate-200/80">
                <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                  {isElectric ? "Battery & Range" : "Fuel & Engine"}
                </p>
                <p className="text-sm font-black text-slate-900 mt-0.5 truncate">
                  {currentVehicle.range_or_mileage}
                </p>
              </div>

              <div className="p-3 rounded-2xl bg-slate-50 border border-slate-200/80">
                <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Powertrain</p>
                <p className="text-sm font-black text-slate-900 mt-0.5 truncate">{currentVehicle.engine_specs}</p>
              </div>

              <div className="p-3 rounded-2xl bg-slate-50 border border-slate-200/80">
                <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Top Features</p>
                <p className="text-sm font-black text-slate-900 mt-0.5 truncate">{currentVehicle.key_highlights?.[0] || currentVehicle.usp}</p>
              </div>
            </div>

            {/* Contextual Action Buttons */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2">
              <button
                onClick={() => handleStartConsultation(currentVehicle)}
                style={{ backgroundColor: primaryColor }}
                className="text-white py-3 rounded-xl font-black shadow-md flex items-center justify-center gap-2 transition-all hover:opacity-90 text-xs cursor-pointer"
              >
                <Sparkles className="w-4 h-4" />
                <span>Speak with {agentName} about {currentVehicle.name.split(" (")[0]}</span>
              </button>

              <button
                onClick={() => handleOpenTestDrive(currentVehicle)}
                className="bg-slate-900 hover:bg-slate-800 text-white py-3 rounded-xl font-black shadow-md flex items-center justify-center gap-2 transition-all text-xs cursor-pointer"
              >
                <Calendar className="w-4 h-4 text-red-400" />
                <span>Book Test Drive / Enquiry</span>
              </button>

              <button
                onClick={() => handleOpenCompare(currentVehicle)}
                className="bg-white hover:bg-slate-100 text-slate-700 py-3 rounded-xl font-bold border border-slate-300 flex items-center justify-center gap-2 shadow-xs transition-all text-xs cursor-pointer"
              >
                <Layers className="w-4 h-4 text-cyan-600" />
                <span>Compare Specs Matrix</span>
              </button>
            </div>
          </div>

          {/* Bottom Lineup Portfolio Section */}
          <div className="space-y-4">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
              <div>
                <h3 className="text-lg font-black text-slate-900 flex items-center gap-2">
                  <Car className="w-4 h-4" style={{ color: primaryColor }} />
                  <span>Explore {brandName} Lineup ({filteredVehicles.length} Models)</span>
                </h3>
              </div>

              <div className="flex items-center gap-3">
                {/* Category Filter Pills */}
                <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-2xl border border-slate-200 overflow-x-auto max-w-full">
                  {categories.map((cat) => (
                    <button
                      key={cat.id}
                      onClick={() => setSelectedCategory(cat.id)}
                      className={`px-3 py-1 rounded-xl text-xs font-black transition-all whitespace-nowrap cursor-pointer ${
                        selectedCategory === cat.id
                          ? "bg-white text-slate-900 shadow-sm border border-slate-200"
                          : "text-slate-600 hover:text-slate-900"
                      }`}
                    >
                      {cat.label}
                    </button>
                  ))}
                </div>

                {/* Carousel Scroll Buttons (When in carousel mode) */}
                {viewMode === "carousel" && (
                  <div className="hidden sm:flex items-center gap-1">
                    <button
                      onClick={() => scrollCarousel("left")}
                      className="p-1.5 rounded-full bg-white border border-slate-200 hover:bg-slate-100 shadow-xs text-slate-700 cursor-pointer"
                      title="Scroll Left"
                    >
                      <ChevronLeft className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => scrollCarousel("right")}
                      className="p-1.5 rounded-full bg-white border border-slate-200 hover:bg-slate-100 shadow-xs text-slate-700 cursor-pointer"
                      title="Scroll Right"
                    >
                      <ChevronRight className="w-4 h-4" />
                    </button>
                  </div>
                )}
              </div>
            </div>

            {/* Lineup Portfolio Render: Carousel Mode (keeps selected vehicle always in view) vs Grid Mode */}
            {viewMode === "carousel" ? (
              <div
                ref={carouselRef}
                className="flex items-stretch gap-4 overflow-x-auto pb-4 pt-1 snap-x no-scrollbar scroll-smooth"
              >
                {filteredVehicles.map((vehicle) => {
                  const isSelected = vehicle.id === selectedVehicleId;
                  const isEV = vehicle.category === "Born Electric SUV";

                  return (
                    <div
                      key={vehicle.id}
                      id={`carousel-card-${vehicle.id}`}
                      onClick={() => {
                        onSelectVehicleId(vehicle.id);
                        if (isChatOpen && onSendChatMessage) {
                          onSendChatMessage(`Tell me about ${vehicle.name}`);
                        }
                      }}
                      className={`min-w-[240px] max-w-[260px] rounded-2xl transition-all duration-300 cursor-pointer overflow-hidden border p-3.5 flex flex-col justify-between group bg-white shadow-xs shrink-0 snap-start ${
                        isSelected
                          ? isEV
                            ? "border-cyan-500 ring-2 ring-cyan-500/20 shadow-md bg-cyan-50/20"
                            : "border-slate-800 ring-2 ring-slate-400 shadow-md bg-slate-50/50"
                          : "border-slate-200 hover:border-slate-300 hover:shadow-md"
                      }`}
                    >
                      <div className="relative h-28 w-full bg-slate-50 flex items-center justify-center p-2 rounded-xl mb-2">
                        <img
                          src={vehicle.hero_image}
                          alt={vehicle.name}
                          className="w-full h-full object-contain filter drop-shadow-sm group-hover:scale-105 transition-transform duration-300"
                        />
                        {vehicle.is_custom_source_of_truth && (
                          <span className="absolute top-2 left-2 bg-emerald-600 text-white text-[8px] font-bold px-1.5 py-0.5 rounded-md uppercase shadow-xs">
                            ✓ Truth
                          </span>
                        )}
                        {isSelected && (
                          <span
                            className="absolute top-2 right-2 text-white text-[9px] font-black px-2 py-0.5 rounded-full uppercase shadow-xs"
                            style={{ backgroundColor: primaryColor }}
                          >
                            Active
                          </span>
                        )}
                      </div>

                      <div className="space-y-1 mb-3">
                        <h4 className="text-xs font-black text-slate-900 truncate">{vehicle.name}</h4>
                        <p className="text-[11px] font-bold" style={{ color: primaryColor }}>{vehicle.price_range.split(" (")[0]}</p>
                      </div>

                      {/* 2 Clean Actions on Every Grid Card */}
                      <div className="grid grid-cols-2 gap-1.5 pt-2 border-t border-slate-100">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleOpenTestDrive(vehicle);
                          }}
                          className="py-1.5 px-2 rounded-lg bg-slate-900 hover:bg-slate-800 text-white text-[10px] font-bold flex items-center justify-center gap-1 transition-colors cursor-pointer"
                        >
                          <Calendar className="w-3 h-3 text-amber-400" />
                          <span>Book Drive</span>
                        </button>

                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleOpenCompare(vehicle);
                          }}
                          className="py-1.5 px-2 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-[10px] font-bold flex items-center justify-center gap-1 transition-colors border border-slate-200 cursor-pointer"
                        >
                          <Layers className="w-3 h-3 text-cyan-600" />
                          <span>Compare</span>
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className={`grid gap-4 ${isChatOpen ? "grid-cols-1 sm:grid-cols-2 xl:grid-cols-3" : "grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4"}`}>
                {filteredVehicles.map((vehicle) => {
                  const isSelected = vehicle.id === selectedVehicleId;
                  const isEV = vehicle.category === "Born Electric SUV";

                  return (
                    <div
                      key={vehicle.id}
                      id={`grid-card-${vehicle.id}`}
                      onClick={() => {
                        onSelectVehicleId(vehicle.id);
                        if (isChatOpen && onSendChatMessage) {
                          onSendChatMessage(`Tell me about ${vehicle.name}`);
                        }
                      }}
                      className={`rounded-2xl transition-all duration-300 cursor-pointer overflow-hidden border p-3.5 flex flex-col justify-between group bg-white shadow-xs ${
                        isSelected
                          ? isEV
                            ? "border-cyan-500 ring-2 ring-cyan-500/20 shadow-md bg-cyan-50/20"
                            : "border-slate-800 ring-2 ring-slate-400 shadow-md bg-slate-50/50"
                          : "border-slate-200 hover:border-slate-300 hover:shadow-md"
                      }`}
                    >
                      <div className="relative h-32 w-full bg-slate-50 flex items-center justify-center p-2 rounded-xl mb-3">
                        <img
                          src={vehicle.hero_image}
                          alt={vehicle.name}
                          className="w-full h-full object-contain filter drop-shadow-sm group-hover:scale-105 transition-transform duration-300"
                        />
                        {vehicle.is_custom_source_of_truth && (
                          <span className="absolute top-2 left-2 bg-emerald-600 text-white text-[8px] font-bold px-1.5 py-0.5 rounded-md uppercase shadow-xs">
                            ✓ Truth
                          </span>
                        )}
                        {isSelected && (
                          <span
                            className="absolute top-2 right-2 text-white text-[9px] font-black px-2 py-0.5 rounded-full uppercase shadow-xs"
                            style={{ backgroundColor: primaryColor }}
                          >
                            Active
                          </span>
                        )}
                      </div>

                      <div className="space-y-1 mb-3">
                        <h4 className="text-xs font-black text-slate-900 truncate">{vehicle.name}</h4>
                        <p className="text-[11px] font-bold" style={{ color: primaryColor }}>{vehicle.price_range.split(" (")[0]}</p>
                      </div>

                      {/* 2 Clean Actions on Every Grid Card */}
                      <div className="grid grid-cols-2 gap-1.5 pt-2 border-t border-slate-100">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleOpenTestDrive(vehicle);
                          }}
                          className="py-1.5 px-2 rounded-lg bg-slate-900 hover:bg-slate-800 text-white text-[10px] font-bold flex items-center justify-center gap-1 transition-colors cursor-pointer"
                        >
                          <Calendar className="w-3 h-3 text-amber-400" />
                          <span>Book Drive</span>
                        </button>

                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleOpenCompare(vehicle);
                          }}
                          className="py-1.5 px-2 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-[10px] font-bold flex items-center justify-center gap-1 transition-colors border border-slate-200 cursor-pointer"
                        >
                          <Layers className="w-3 h-3 text-cyan-600" />
                          <span>Compare</span>
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Modals for Test Drive, Compare, Lead Identification, and History */}
      {modalVehicle && (
        <TestDriveModal
          isOpen={isTestDriveOpen}
          onClose={() => setIsTestDriveOpen(false)}
          vehicle={modalVehicle}
          dealerships={[]}
          customerId={currentProfile?.customer_id || "CUST-9820155432"}
          onBookingSuccess={() => setIsTestDriveOpen(false)}
        />
      )}

      {modalVehicle && (
        <ComparisonMatrix
          isOpen={isCompareOpen}
          onClose={() => setIsCompareOpen(false)}
          vehicle1={modalVehicle}
          vehicle2={compareVehicle2 || vehicles.find((v) => v.id !== modalVehicle.id) || vehicles[0]}
          allVehicles={vehicles}
          onSelectVehicle1={(v) => setModalVehicle(v)}
          onSelectVehicle2={(v) => setCompareVehicle2(v)}
          onBookTestDrive={(v) => {
            setIsCompareOpen(false);
            setModalVehicle(v);
            setIsTestDriveOpen(true);
          }}
        />
      )}

      <CustomerLeadModal
        isOpen={isLeadModalOpen}
        onClose={() => setIsLeadModalOpen(false)}
        selectedVehicle={currentVehicle}
        onCustomerIdentified={handleCustomerIdentified}
      />

      <CustomerProfileDrawer
        isOpen={isHistoryModalOpen}
        onClose={() => setIsHistoryModalOpen(false)}
        profile={currentProfile}
        onSetPhase={() => {}}
        onRefresh={() => {}}
      />
    </div>
  );
}
