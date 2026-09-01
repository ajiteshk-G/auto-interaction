"use client";

import React, { useState, useEffect } from "react";
import { SalesMobileApp } from "@/components/SalesMobileApp";
import { fetchCatalog } from "@/lib/api";
import { DEFAULT_VEHICLES } from "@/lib/defaultCatalog";
import { useCustomerProfile } from "@/hooks/useCustomerProfile";
import { VehicleItem, TestRideInsightResponse } from "@/types";

export default function SalesMobilePage() {
  const { profile } = useCustomerProfile();
  const [vehicles, setVehicles] = useState<VehicleItem[]>(DEFAULT_VEHICLES);
  const [completedInsights, setCompletedInsights] = useState<TestRideInsightResponse | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        const cat = await fetchCatalog();
        if (Array.isArray(cat) && cat.length > 0) {
          setVehicles(cat);
        }
      } catch (e) {
        console.error("Failed to load catalog for Sales Mobile Page:", e);
      }
    }
    loadData();
  }, []);

  const handleProceedToOutboundCall = (insights: TestRideInsightResponse) => {
    setCompletedInsights(insights);
    if (typeof window !== "undefined") {
      window.location.href = "/?stage=outbound_call";
    }
  };

  return (
    <div className="min-h-dvh bg-slate-900 flex justify-center items-center sm:p-4 selection:bg-red-600 selection:text-white">
      <div className="w-full max-w-md h-dvh sm:h-[844px] bg-slate-50 overflow-hidden sm:rounded-[36px] sm:border-[6px] sm:border-slate-700 sm:shadow-2xl flex flex-col relative">
        <SalesMobileApp
          vehicles={vehicles}
          profile={profile}
          selectedVehicleId="thar_roxx"
          onProceedToOutboundCall={handleProceedToOutboundCall}
          isStandalone={true}
        />
      </div>
    </div>
  );
}
