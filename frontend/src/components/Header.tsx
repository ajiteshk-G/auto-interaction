"use client";

import React from "react";
import Link from "next/link";
import { CustomerProfile, BrandCatalog } from "@/types";
import {
  Sparkles,
  Smartphone,
  PhoneCall,
  Zap,
  UserCheck,
  MessageSquare,
  ShieldCheck,
  Layers,
  Palette
} from "lucide-react";

interface HeaderProps {
  profile: CustomerProfile | null;
  activeStage: "presales" | "sales_app" | "outbound_call";
  onSelectStage: (stage: "presales" | "sales_app" | "outbound_call") => void;
  onOpenProfile: () => void;
  onOpenLeadModal?: () => void;
  onOpenAvatar?: () => void;
  brand?: BrandCatalog | null;
  onOpenBrandStudio?: () => void;
}

export function Header({
  profile,
  activeStage,
  onSelectStage,
  onOpenProfile,
  onOpenLeadModal,
  onOpenAvatar,
  brand,
  onOpenBrandStudio
}: HeaderProps) {
  const stages = [
    { id: "presales" as const, label: "1. Pre-Sales Showroom", icon: Sparkles },
    { id: "sales_app" as const, label: "2. Sales Mobile App", icon: Smartphone },
    { id: "outbound_call" as const, label: "3. Outbound Call", icon: PhoneCall }
  ];

  const primaryColor = brand?.primary_color || "#d71920";

  return (
    <header className="w-full bg-white/95 border-b border-slate-200 sticky top-0 z-40 backdrop-blur-md shadow-xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-3">
        {/* Dynamic Brand Logo & Identity */}
        <div className="flex items-center gap-3 cursor-pointer" onClick={() => onSelectStage("presales")}>
          <div className="flex items-center gap-2">
            {brand?.logo_url ? (
              <img
                src={brand.logo_url}
                alt={brand.name}
                className="h-8 max-w-[120px] object-contain"
                onError={(e) => { (e.target as HTMLElement).style.display = "none"; }}
              />
            ) : (
              <span
                className="w-4 h-5 transform skew-x-[-15deg] inline-block rounded-xs"
                style={{ backgroundColor: primaryColor }}
              />
            )}
            <span className="text-lg font-black tracking-wider text-slate-900 uppercase">
              {brand?.name ? brand.name.replace(/\(.*\)/, "").trim() : "MAHINDRA"}
            </span>
          </div>
          <span className="text-[10px] px-2.5 py-0.5 rounded-full bg-slate-100 text-slate-600 font-bold border border-slate-200 hidden sm:inline-block">
            AI OMNICHANNEL
          </span>
        </div>

        {/* Omnichannel Journey Stage Navigation */}
        <nav className="flex items-center gap-1 bg-slate-100 p-1 rounded-full border border-slate-200 text-xs shrink-0 select-none">
          {stages.map((st) => {
            const Icon = st.icon;
            const isActive = activeStage === st.id;
            return (
              <button
                key={st.id}
                onClick={() => onSelectStage(st.id)}
                style={isActive ? { backgroundColor: primaryColor } : undefined}
                className={`px-3 py-1.5 rounded-full flex items-center gap-1.5 font-bold transition-all whitespace-nowrap cursor-pointer ${
                  isActive
                    ? "text-white shadow-xs"
                    : "text-slate-600 hover:text-slate-900 hover:bg-slate-200/70"
                }`}
              >
                <Icon className="w-3.5 h-3.5 shrink-0" />
                <span className="hidden lg:inline">{st.label}</span>
                <span className="inline lg:hidden">{st.label.replace(/^\d+\.\s*/, "")}</span>
              </button>
            );
          })}
        </nav>

        {/* Right Action Controls: Brand Studio + Admin Link + Logged-in Profile */}
        <div className="flex items-center gap-2">
          {/* Brand Studio Launcher Button */}
          {onOpenBrandStudio && (
            <button
              onClick={onOpenBrandStudio}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-indigo-50 hover:bg-indigo-100 text-indigo-700 border border-indigo-200 text-xs font-bold transition-all shadow-xs group"
              title="Open Brand Studio to switch brands, onboard via URLs, or upload custom images"
            >
              <Layers className="w-3.5 h-3.5 text-indigo-600 group-hover:scale-110 transition-transform" />
              <span className="hidden sm:inline">Brand Studio</span>
              <span className="w-2 h-2 rounded-full" style={{ backgroundColor: primaryColor }} />
            </button>
          )}

          {/* Admin Portal Button */}
          <Link
            href="/admin"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-slate-900 hover:bg-slate-800 text-slate-200 hover:text-white border border-slate-700 text-xs font-bold transition-all shadow-xs group"
            title="Open Test Rides & Transcripts Admin Portal"
          >
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400 group-hover:scale-110 transition-transform" />
            <span className="hidden sm:inline">Admin Portal</span>
          </Link>



          {/* Customer Profile Pill (Only shown when identified) */}
          {profile && (
            <button
              onClick={onOpenProfile}
              className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-50 hover:bg-slate-100 border border-slate-200 hover:border-slate-300 transition-all text-left"
            >
              <div className="w-7 h-7 rounded-full bg-emerald-100 border border-emerald-300 flex items-center justify-center text-emerald-700">
                <UserCheck className="w-4 h-4" />
              </div>
              <div className="hidden lg:block">
                <div className="text-xs font-bold text-slate-900 leading-none flex items-center gap-1">
                  {profile.name}
                </div>
                <div className="text-[10px] text-slate-500 font-mono mt-0.5">
                  {profile.phone}
                </div>
              </div>
            </button>
          )}
        </div>
      </div>
    </header>
  );
}
