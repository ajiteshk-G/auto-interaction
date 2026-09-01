"use client";

import React from "react";
import { CustomerProfile, BrandCatalog } from "@/types";
import { X, User, Phone, Mail, MapPin, ShieldCheck, Car, CreditCard, Sparkles, Clock, RefreshCw } from "lucide-react";

interface CustomerProfileDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  profile: CustomerProfile | null;
  brand?: BrandCatalog | null;
  onSetPhase: (phase: "PRE_SALES" | "FINANCING" | "PURCHASED" | "POST_SALES") => void;
  onRefresh: () => void;
}

export function CustomerProfileDrawer({
  isOpen,
  onClose,
  profile,
  brand,
  onSetPhase,
  onRefresh
}: CustomerProfileDrawerProps) {
  if (!isOpen || !profile) return null;

  const brandColor = brand?.primary_color || "#e31837";
  const brandName = brand?.name || "Official Auto";

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex justify-end">
      <div className="bg-mahindra-card border-l border-mahindra-border w-full max-w-md h-full flex flex-col shadow-2xl overflow-y-auto">
        {/* Drawer Header */}
        <div className="p-4 border-b border-mahindra-border flex items-center justify-between sticky top-0 bg-mahindra-card z-10">
          <div className="flex items-center gap-2">
            <User className="w-5 h-5" style={{ color: brandColor }} />
            <div>
              <h2 className="text-sm font-bold text-white uppercase tracking-wider">
                {brand?.name ? `${brand.name} Profile` : "Persistent Customer Profile"}
              </h2>
              {brand?.id && (
                <span className="text-[10px] text-gray-400 font-mono">Brand Tenant: {brand.id}</span>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={onRefresh} className="p-1 text-gray-400 hover:text-white rounded">
              <RefreshCw className="w-4 h-4" />
            </button>
            <button onClick={onClose} className="p-1 text-gray-400 hover:text-white rounded">
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-5 space-y-5 text-xs">
          {/* Identity Card */}
          <div className="bg-mahindra-dark p-4 rounded-xl border border-mahindra-border space-y-3">
            <div className="flex items-center justify-between">
              <div className="font-bold text-white text-sm">{profile.name}</div>
              <span className="font-mono text-[10px] text-gray-400">{profile.customer_id}</span>
            </div>

            <div className="space-y-1.5 text-gray-300">
              <div className="flex items-center gap-2">
                <Phone className="w-3.5 h-3.5 text-gray-400" />
                <span>{profile.phone}</span>
              </div>
              <div className="flex items-center gap-2">
                <Mail className="w-3.5 h-3.5 text-gray-400" />
                <span>{profile.email}</span>
              </div>
              <div className="flex items-center gap-2">
                <MapPin className="w-3.5 h-3.5 text-gray-400" />
                <span>{profile.city}</span>
              </div>
            </div>
          </div>

          {/* Lifecycle State Simulator Buttons */}
          <div className="space-y-2">
            <label className="text-gray-400 font-semibold uppercase text-[10px] tracking-wider block">
              Simulate Customer Lifecycle Phase
            </label>
            <div className="grid grid-cols-2 gap-2">
              <button
                onClick={() => onSetPhase("PRE_SALES")}
                className={`p-2.5 rounded-xl border text-left transition-all ${
                  profile.current_phase === "PRE_SALES"
                    ? "bg-mahindra-red/20 border-mahindra-red text-white font-bold"
                    : "bg-mahindra-dark border-mahindra-border text-gray-400"
                }`}
              >
                1. Pre-Sales Discovery
              </button>

              <button
                onClick={() => onSetPhase("FINANCING")}
                className={`p-2.5 rounded-xl border text-left transition-all ${
                  profile.current_phase === "FINANCING"
                    ? "bg-mahindra-red/20 border-mahindra-red text-white font-bold"
                    : "bg-mahindra-dark border-mahindra-border text-gray-400"
                }`}
              >
                2. Test Ride Completed
              </button>

              <button
                onClick={() => onSetPhase("POST_SALES")}
                className={`p-2.5 rounded-xl border text-left transition-all col-span-2 ${
                  profile.current_phase === "POST_SALES"
                    ? "bg-mahindra-red/20 border-mahindra-red text-white font-bold"
                    : "bg-mahindra-dark border-mahindra-border text-gray-400"
                }`}
              >
                3. Post-Ride Feedback Call
              </button>
            </div>
          </div>



          {/* Owned Vehicle Record */}
          <div className="bg-mahindra-dark p-4 rounded-xl border border-mahindra-border space-y-2.5">
            <div className="font-bold text-white flex items-center gap-1.5">
              <Car className="w-4 h-4 text-mahindra-red" />
              Allocated Vehicle Details
            </div>
            <div className="text-gray-300 space-y-1">
              <div>{profile.owned_vehicle_name}</div>
              <div className="font-mono text-gray-400 text-[10px]">VIN: {profile.owned_vin}</div>
              <div className="font-mono text-gray-400 text-[10px]">Reg: {profile.registration_number}</div>
              <div className="text-emerald-400 text-[10px]">Odometer: {profile.odometer_km.toLocaleString()} km</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
