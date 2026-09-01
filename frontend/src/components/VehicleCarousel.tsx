"use client";

import React, { useState } from "react";
import { VehicleItem } from "@/types";
import { Zap, Shield, Compass, Calendar, Layers, ChevronRight, CheckCircle } from "lucide-react";

interface VehicleCarouselProps {
  vehicles: VehicleItem[];
  selectedVehicleId: string;
  onSelectVehicle: (id: string) => void;
  onOpenTestDrive: (vehicle: VehicleItem) => void;
  onOpenCompare: (vehicle: VehicleItem) => void;
}

export function VehicleCarousel({
  vehicles,
  selectedVehicleId,
  onSelectVehicle,
  onOpenTestDrive,
  onOpenCompare,
}: VehicleCarouselProps) {
  const [filterCategory, setFilterCategory] = useState<string>("ALL");

  const categories = ["ALL", "Authentic SUV", "Born Electric SUV", "Tech SUV"];

  const filtered = filterCategory === "ALL"
    ? vehicles
    : vehicles.filter((v) => v.category === filterCategory);

  const selectedVehicle = vehicles.find((v) => v.id === selectedVehicleId) || vehicles[0];

  return (
    <div className="space-y-6">
      {/* Category Tabs */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-lg font-black tracking-wide text-white flex items-center gap-2">
            <span className="w-2.5 h-2.5 bg-mahindra-red rounded-xs"></span>
            MAHINDRA SUV SHOWCASE
          </h2>
          <p className="text-xs text-gray-400">Authentic ICE & Born Electric Origins Lineup</p>
        </div>

        <div className="flex items-center gap-1.5 bg-mahindra-charcoal p-1 rounded-xl border border-mahindra-border">
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setFilterCategory(cat)}
              className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                filterCategory === cat
                  ? "bg-mahindra-red text-white shadow-md"
                  : "text-gray-400 hover:text-white"
              }`}
            >
              {cat === "ALL" ? "All Lineup" : cat}
            </button>
          ))}
        </div>
      </div>

      {/* Vehicles Grid Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {filtered.map((vehicle) => {
          const isSelected = vehicle.id === selectedVehicleId;
          const isElectric = vehicle.category === "Born Electric SUV";

          return (
            <div
              key={vehicle.id}
              onClick={() => onSelectVehicle(vehicle.id)}
              className={`rounded-2xl transition-all duration-300 cursor-pointer overflow-hidden border flex flex-col justify-between ${
                isSelected
                  ? isElectric
                    ? "border-mahindra-electric bg-gradient-to-b from-mahindra-electricBg to-mahindra-card shadow-xl shadow-cyan-950/40 scale-[1.02]"
                    : "border-mahindra-red bg-gradient-to-b from-mahindra-charcoal to-mahindra-card shadow-xl shadow-red-950/40 scale-[1.02]"
                  : "border-mahindra-border/80 bg-mahindra-card hover:border-gray-600 hover:shadow-lg"
              }`}
            >
              {/* Card Image & Badge */}
              <div className="relative h-44 w-full bg-black/40 overflow-hidden">
                <img
                  src={vehicle.hero_image}
                  alt={vehicle.name}
                  className="w-full h-full object-cover opacity-85 hover:scale-105 transition-transform duration-500"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-mahindra-card via-transparent to-black/60" />

                {/* Category Pill */}
                <div className="absolute top-3 left-3">
                  <span
                    className={`text-[10px] font-bold px-2.5 py-1 rounded-full uppercase tracking-wider flex items-center gap-1 backdrop-blur-md ${
                      isElectric
                        ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/40"
                        : "bg-red-500/20 text-red-300 border border-red-500/40"
                    }`}
                  >
                    {isElectric ? <Zap className="w-3 h-3 text-cyan-400" /> : <Shield className="w-3 h-3 text-red-400" />}
                    {vehicle.category}
                  </span>
                </div>

                {/* Price Pill */}
                <div className="absolute bottom-3 right-3 bg-black/70 backdrop-blur-md px-2.5 py-1 rounded-lg border border-white/10 text-[11px] font-bold text-white">
                  {vehicle.price_range.split(" (")[0]}
                </div>
              </div>

              {/* Card Details */}
              <div className="p-4 flex-1 flex flex-col justify-between space-y-3">
                <div>
                  <h3 className="text-base font-bold text-white leading-snug flex items-center justify-between">
                    {vehicle.name}
                    {isSelected && <CheckCircle className="w-4 h-4 text-emerald-400" />}
                  </h3>
                  <p className="text-xs text-gray-400 mt-0.5 line-clamp-1">{vehicle.tagline}</p>
                </div>

                {/* Highlights List */}
                <div className="space-y-1 bg-mahindra-dark/60 p-2.5 rounded-xl border border-mahindra-border/50 text-[11px]">
                  {vehicle.key_highlights.slice(0, 2).map((h, i) => (
                    <div key={i} className="text-gray-300 flex items-center gap-1.5 truncate">
                      <span className="w-1 h-1 rounded-full bg-mahindra-red"></span>
                      {h}
                    </div>
                  ))}
                </div>

                {/* Action Buttons */}
                <div className="grid grid-cols-3 gap-2 pt-2 border-t border-mahindra-border/60 text-xs">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onOpenTestDrive(vehicle);
                    }}
                    className="bg-mahindra-red hover:bg-red-600 text-white font-semibold py-1.5 rounded-lg flex items-center justify-center gap-1 transition-all"
                  >
                    <Calendar className="w-3.5 h-3.5" />
                    Book Drive
                  </button>

                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onOpenCompare(vehicle);
                    }}
                    className="bg-mahindra-charcoal hover:bg-mahindra-border text-gray-300 font-medium py-1.5 rounded-lg border border-mahindra-border flex items-center justify-center gap-1 transition-all"
                  >
                    <Layers className="w-3.5 h-3.5" />
                    Compare
                  </button>


                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
