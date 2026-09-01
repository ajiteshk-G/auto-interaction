"use client";

import { useState, useEffect, useCallback } from "react";
import { CustomerProfile } from "@/types";
import { fetchCustomerProfile, updateCustomerPhase } from "@/lib/api";

export function useCustomerProfile(initialCustomerId?: string) {
  const [profile, setProfile] = useState<CustomerProfile | null>(null);
  const [loading, setLoading] = useState(false);

  const loadProfile = useCallback(async (idOrPhone: string) => {
    try {
      setLoading(true);
      const data = await fetchCustomerProfile(idOrPhone);
      setProfile(data);
    } catch (e) {
      console.error("Error loading customer profile:", e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // Only load if explicit customerId is provided
    if (initialCustomerId) {
      loadProfile(initialCustomerId);
    }
  }, [initialCustomerId, loadProfile]);

  const setPhase = async (phase: "PRE_SALES" | "FINANCING" | "PURCHASED" | "POST_SALES") => {
    if (profile?.customer_id) {
      await updateCustomerPhase(phase, profile.customer_id);
      await loadProfile(profile.customer_id);
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
