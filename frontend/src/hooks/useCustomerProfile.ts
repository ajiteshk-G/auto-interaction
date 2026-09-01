"use client";

import { useState, useEffect, useCallback } from "react";
import { CustomerProfile } from "@/types";
import { fetchCustomerProfile, updateCustomerPhase } from "@/lib/api";

export function useCustomerProfile(initialCustomerId?: string, brandId?: string) {
  const [profile, setProfile] = useState<CustomerProfile | null>(null);
  const [loading, setLoading] = useState(false);

  const loadProfile = useCallback(async (idOrPhone: string, explicitBrandId?: string) => {
    try {
      setLoading(true);
      const activeBrand = explicitBrandId || brandId;
      const isCustId = idOrPhone?.startsWith("CUST-");
      const data = isCustId
        ? await fetchCustomerProfile(idOrPhone, undefined, activeBrand)
        : await fetchCustomerProfile(undefined, idOrPhone, activeBrand);
      setProfile(data);
    } catch (e) {
      console.error("Error loading customer profile:", e);
    } finally {
      setLoading(false);
    }
  }, [brandId]);

  useEffect(() => {
    // Only load if explicit customerId is provided
    if (initialCustomerId) {
      loadProfile(initialCustomerId, brandId);
    }
  }, [initialCustomerId, brandId, loadProfile]);

  const setPhase = async (phase: "PRE_SALES" | "FINANCING" | "PURCHASED" | "POST_SALES") => {
    if (profile?.customer_id) {
      await updateCustomerPhase(phase, profile.customer_id, brandId);
      await loadProfile(profile.customer_id, brandId);
    }
  };

  const setIdentifiedProfile = (identifiedData: any) => {
    setProfile(identifiedData);
  };

  return {
    profile,
    loading,
    setProfile,
    loadProfile,
    setIdentifiedProfile,
    setPhase
  };
}
