"use client";

import React, { useState, useEffect } from "react";
import { VehicleItem } from "@/types";
import { X, Layers, Check, Shield, Zap, ArrowLeftRight, ChevronDown } from "lucide-react";

interface ComparisonMatrixProps {
  isOpen: boolean;
  onClose: () => void;
  allVehicles?: VehicleItem[];
  vehicle1: VehicleItem | null;
  vehicle2: VehicleItem | null;
  onSelectVehicle1?: (v: VehicleItem) => void;
  onSelectVehicle2?: (v: VehicleItem) => void;
  onBookTestDrive?: (v: VehicleItem) => void;
}

export function ComparisonMatrix({
  isOpen,
  onClose,
  allVehicles = [],
  vehicle1,
  vehicle2,
  onSelectVehicle1,
  onSelectVehicle2
}: ComparisonMatrixProps) {
  const [selectedV1, setSelectedV1] = useState<VehicleItem | null>(vehicle1);
  const [selectedV2, setSelectedV2] = useState<VehicleItem | null>(vehicle2);

  useEffect(() => {
    if (vehicle1) setSelectedV1(vehicle1);
  }, [vehicle1]);

  useEffect(() => {
    if (vehicle2) setSelectedV2(vehicle2);
  }, [vehicle2]);

  if (!isOpen || !selectedV1 || !selectedV2) return null;

  const handleV1Change = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const found = allVehicles.find((v) => v.id === e.target.value);
    if (found) {
      setSelectedV1(found);
      if (onSelectVehicle1) onSelectVehicle1(found);
    }
  };

  const handleV2Change = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const found = allVehicles.find((v) => v.id === e.target.value);
    if (found) {
      setSelectedV2(found);
      if (onSelectVehicle2) onSelectVehicle2(found);
    }
  };

  const isV1Electric = selectedV1.category === "Born Electric SUV";
  const isV2Electric = selectedV2.category === "Born Electric SUV";

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/80 backdrop-blur-md flex items-center justify-center p-3 sm:p-6 animate-in fade-in duration-200">
      <div className="bg-white border border-slate-200 rounded-3xl w-full max-w-5xl max-h-[92vh] overflow-y-auto shadow-2xl flex flex-col">
        {/* Header */}
        <div className="p-5 border-b border-slate-200 flex items-center justify-between sticky top-0 bg-white/95 backdrop-blur-md z-20">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-red-50 border border-red-200 flex items-center justify-center text-red-600 shadow-xs">
              <Layers className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-black text-slate-900 tracking-tight">Side-by-Side Spec Comparison</h2>
              <p className="text-xs text-slate-500">Compare pricing, powertrain, real-world mileage, and ADAS technology</p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-2 rounded-xl text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Matrix Vehicle Selectors & Visual Cards Header */}
        <div className="p-6 sm:p-8 space-y-6 flex-1">
          <div className="grid grid-cols-1 md:grid-cols-12 gap-4 items-center bg-slate-50 p-5 rounded-3xl border border-slate-200">
            {/* Vehicle 1 Column */}
            <div className="md:col-span-5 bg-white p-5 rounded-2xl border border-slate-200 shadow-xs space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-extrabold uppercase tracking-wider text-slate-400">Vehicle 1</span>
                {allVehicles.length > 0 && (
                  <select
                    value={selectedV1.id}
                    onChange={handleV1Change}
                    className="text-xs font-bold text-slate-800 bg-slate-100 border border-slate-200 rounded-lg px-2.5 py-1 focus:outline-none focus:ring-2 focus:ring-red-500 cursor-pointer"
                  >
                    {allVehicles.map((v) => (
                      <option key={v.id} value={v.id}>
                        {v.name}
                      </option>
                    ))}
                  </select>
                )}
              </div>

              <div className="h-36 w-full bg-slate-50 rounded-xl flex items-center justify-center p-2 border border-slate-100">
                <img
                  src={selectedV1.hero_image}
                  alt={selectedV1.name}
                  className="w-full h-full object-contain filter drop-shadow-md"
                />
              </div>

              <div className="text-center space-y-1">
                <div className="font-black text-slate-900 text-sm">{selectedV1.name}</div>
                <div className="text-xs text-red-600 font-extrabold">{selectedV1.price_range.split(" (")[0]}</div>
                <div className="text-[10px] text-slate-500">{selectedV1.category}</div>
              </div>
            </div>

            {/* VS Divider */}
            <div className="md:col-span-2 flex flex-col items-center justify-center text-center py-2">
              <div className="w-10 h-10 rounded-full bg-slate-200 border border-slate-300 flex items-center justify-center text-slate-700 font-black text-xs shadow-xs">
                VS
              </div>
              <span className="text-[10px] text-slate-400 font-bold uppercase tracking-widest mt-1">Compare</span>
            </div>

            {/* Vehicle 2 Column */}
            <div className="md:col-span-5 bg-white p-5 rounded-2xl border border-slate-200 shadow-xs space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-extrabold uppercase tracking-wider text-slate-400">Vehicle 2</span>
                {allVehicles.length > 0 && (
                  <select
                    value={selectedV2.id}
                    onChange={handleV2Change}
                    className="text-xs font-bold text-slate-800 bg-slate-100 border border-slate-200 rounded-lg px-2.5 py-1 focus:outline-none focus:ring-2 focus:ring-red-500 cursor-pointer"
                  >
                    {allVehicles.map((v) => (
                      <option key={v.id} value={v.id}>
                        {v.name}
                      </option>
                    ))}
                  </select>
                )}
              </div>

              <div className="h-36 w-full bg-slate-50 rounded-xl flex items-center justify-center p-2 border border-slate-100">
                <img
                  src={selectedV2.hero_image}
                  alt={selectedV2.name}
                  className="w-full h-full object-contain filter drop-shadow-md"
                />
              </div>

              <div className="text-center space-y-1">
                <div className="font-black text-slate-900 text-sm">{selectedV2.name}</div>
                <div className="text-xs text-red-600 font-extrabold">{selectedV2.price_range.split(" (")[0]}</div>
                <div className="text-[10px] text-slate-500">{selectedV2.category}</div>
              </div>
            </div>
          </div>

          {/* Side-by-Side Comparison Specs Table */}
          <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-xs divide-y divide-slate-100 text-xs">
            {/* Powertrain Row */}
            <div className="grid grid-cols-12 p-4 items-center gap-4 bg-slate-50/50">
              <div className="col-span-3 font-extrabold text-slate-500 uppercase tracking-wider text-[11px]">
                Powertrain & Engine
              </div>
              <div className="col-span-4 font-bold text-slate-900 leading-relaxed">
                {selectedV1.engine_specs}
              </div>
              <div className="col-span-1 text-center text-slate-300 font-bold">|</div>
              <div className="col-span-4 font-bold text-slate-900 leading-relaxed">
                {selectedV2.engine_specs}
              </div>
            </div>

            {/* Range / Mileage Row */}
            <div className="grid grid-cols-12 p-4 items-center gap-4">
              <div className="col-span-3 font-extrabold text-slate-500 uppercase tracking-wider text-[11px]">
                Certified Range / Economy
              </div>
              <div className="col-span-4 font-black text-emerald-600">
                {selectedV1.range_or_mileage}
              </div>
              <div className="col-span-1 text-center text-slate-300 font-bold">|</div>
              <div className="col-span-4 font-black text-emerald-600">
                {selectedV2.range_or_mileage}
              </div>
            </div>

            {/* Seating Row */}
            <div className="grid grid-cols-12 p-4 items-center gap-4 bg-slate-50/50">
              <div className="col-span-3 font-extrabold text-slate-500 uppercase tracking-wider text-[11px]">
                Seating & Layout
              </div>
              <div className="col-span-4 font-medium text-slate-700">
                {selectedV1.seating_capacity}
              </div>
              <div className="col-span-1 text-center text-slate-300 font-bold">|</div>
              <div className="col-span-4 font-medium text-slate-700">
                {selectedV2.seating_capacity}
              </div>
            </div>

            {/* Fuel / Battery Row */}
            <div className="grid grid-cols-12 p-4 items-center gap-4">
              <div className="col-span-3 font-extrabold text-slate-500 uppercase tracking-wider text-[11px]">
                Fuel / Battery System
              </div>
              <div className="col-span-4 font-bold text-slate-800">
                {selectedV1.fuel_or_battery}
              </div>
              <div className="col-span-1 text-center text-slate-300 font-bold">|</div>
              <div className="col-span-4 font-bold text-slate-800">
                {selectedV2.fuel_or_battery}
              </div>
            </div>

            {/* USP Row */}
            <div className="grid grid-cols-12 p-4 items-start gap-4 bg-slate-50/50">
              <div className="col-span-3 font-extrabold text-slate-500 uppercase tracking-wider text-[11px] pt-1">
                Value Proposition (USP)
              </div>
              <div className="col-span-4 text-slate-600 leading-relaxed font-medium">
                {selectedV1.usp}
              </div>
              <div className="col-span-1 text-center text-slate-300 font-bold pt-1">|</div>
              <div className="col-span-4 text-slate-600 leading-relaxed font-medium">
                {selectedV2.usp}
              </div>
            </div>

            {/* Key Technology Highlights Row */}
            <div className="grid grid-cols-12 p-4 items-start gap-4">
              <div className="col-span-3 font-extrabold text-slate-500 uppercase tracking-wider text-[11px] pt-1">
                Key Tech Highlights
              </div>
              <div className="col-span-4 space-y-1.5">
                {selectedV1.key_highlights.map((h, i) => (
                  <div key={i} className="flex items-start gap-2 text-slate-700 font-medium">
                    <Check className="w-3.5 h-3.5 text-red-600 shrink-0 mt-0.5" />
                    <span>{h}</span>
                  </div>
                ))}
              </div>
              <div className="col-span-1 text-center text-slate-300 font-bold pt-1">|</div>
              <div className="col-span-4 space-y-1.5">
                {selectedV2.key_highlights.map((h, i) => (
                  <div key={i} className="flex items-start gap-2 text-slate-700 font-medium">
                    <Check className="w-3.5 h-3.5 text-red-600 shrink-0 mt-0.5" />
                    <span>{h}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
