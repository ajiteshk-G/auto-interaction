import { DEFAULT_VEHICLES } from "./defaultCatalog";

function getApiBase() {
  if (typeof window !== "undefined") {
    // In browser, relative /api is proxied by Next.js rewrites to local backend
    return "/api";
  }
  return process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api";
}

const API_BASE = getApiBase();

import { BrandSummary, BrandCatalog, VehicleItem } from "@/types";

// In-memory Fast Client-Side Cache
let cachedCatalog: any = null;
let cachedDealerships: any = null;
let cachedActiveBrand: BrandCatalog | null = null;
const cachedLeadsByDealership = new Map<string, { data: any; expiresAt: number }>();

export function invalidateCatalogCache() {
  cachedCatalog = null;
  cachedDealerships = null;
  cachedActiveBrand = null;
  cachedLeadsByDealership.clear();
}

export function invalidateLeadsCache() {
  cachedLeadsByDealership.clear();
}

// Brand Management APIs
export async function fetchBrands(): Promise<BrandSummary[]> {
  try {
    const res = await fetch(`${API_BASE}/brands`);
    if (!res.ok) throw new Error("Failed to fetch brands");
    return await res.json();
  } catch (e) {
    console.error("fetchBrands error:", e);
    return [];
  }
}

export async function fetchActiveBrand(): Promise<BrandCatalog | null> {
  if (cachedActiveBrand) return cachedActiveBrand;
  try {
    const res = await fetch(`${API_BASE}/brands/active`);
    if (!res.ok) throw new Error("Failed to fetch active brand");
    cachedActiveBrand = await res.json();
    return cachedActiveBrand;
  } catch (e) {
    console.error("fetchActiveBrand error:", e);
    return null;
  }
}

export async function setActiveBrand(brandId: string): Promise<BrandCatalog | null> {
  try {
    const res = await fetch(`${API_BASE}/brands/active`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ brand_id: brandId })
    });
    if (!res.ok) throw new Error("Failed to switch brand");
    invalidateCatalogCache();
    cachedActiveBrand = await res.json();
    return cachedActiveBrand;
  } catch (e) {
    console.error("setActiveBrand error:", e);
    return null;
  }
}

export async function onboardBrand(brandName: string, urls: string[]): Promise<BrandCatalog | null> {
  try {
    const res = await fetch(`${API_BASE}/brands/onboard`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ brand_name: brandName, urls })
    });
    if (!res.ok) throw new Error("Failed to onboard brand");
    invalidateCatalogCache();
    cachedActiveBrand = await res.json();
    return cachedActiveBrand;
  } catch (e) {
    console.error("onboardBrand error:", e);
    throw e;
  }
}

export async function uploadVehicleImage(brandId: string, vehicleId: string, file: File): Promise<VehicleItem | null> {
  try {
    const formData = new FormData();
    formData.append("vehicle_id", vehicleId);
    formData.append("image", file);

    const res = await fetch(`${API_BASE}/brands/${brandId}/upload-vehicle-image`, {
      method: "POST",
      body: formData
    });
    if (!res.ok) throw new Error("Failed to upload vehicle image");
    invalidateCatalogCache();
    return await res.json();
  } catch (e) {
    console.error("uploadVehicleImage error:", e);
    throw e;
  }
}

export async function uploadBrandLogo(brandId: string, file: File): Promise<BrandCatalog | null> {
  try {
    const formData = new FormData();
    formData.append("logo", file);

    const res = await fetch(`${API_BASE}/brands/${brandId}/upload-logo`, {
      method: "POST",
      body: formData
    });
    if (!res.ok) throw new Error("Failed to upload brand logo");
    invalidateCatalogCache();
    cachedActiveBrand = await res.json();
    return cachedActiveBrand;
  } catch (e) {
    console.error("uploadBrandLogo error:", e);
    throw e;
  }
}

export async function updateVehicleDetails(brandId: string, vehicleId: string, updates: any): Promise<VehicleItem | null> {
  try {
    const res = await fetch(`${API_BASE}/brands/${brandId}/vehicles/${vehicleId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(updates)
    });
    if (!res.ok) throw new Error("Failed to update vehicle");
    invalidateCatalogCache();
    return await res.json();
  } catch (e) {
    console.error("updateVehicleDetails error:", e);
    throw e;
  }
}

export async function addCustomVehicle(brandId: string, vehicle: VehicleItem): Promise<VehicleItem | null> {
  try {
    const res = await fetch(`${API_BASE}/brands/${brandId}/vehicles`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(vehicle)
    });
    if (!res.ok) throw new Error("Failed to add vehicle");
    invalidateCatalogCache();
    return await res.json();
  } catch (e) {
    console.error("addCustomVehicle error:", e);
    throw e;
  }
}

export async function deleteCustomVehicle(brandId: string, vehicleId: string): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/brands/${brandId}/vehicles/${vehicleId}`, {
      method: "DELETE"
    });
    invalidateCatalogCache();
    return res.ok;
  } catch (e) {
    console.error("deleteCustomVehicle error:", e);
    return false;
  }
}

// Catalog & Dealerships with Instant Cache Return
export async function fetchCatalog() {
  if (cachedCatalog) return cachedCatalog;
  try {
    const res = await fetch(`${API_BASE}/catalog`);
    if (!res.ok) throw new Error("Catalog fetch failed");
    const data = await res.json();
    cachedCatalog = Array.isArray(data) && data.length > 0 ? data : DEFAULT_VEHICLES;
    return cachedCatalog;
  } catch (err) {
    console.warn("fetchCatalog fallback to default catalog:", err);
    return DEFAULT_VEHICLES;
  }
}

export async function fetchDealerships() {
  if (cachedDealerships) return cachedDealerships;
  try {
    const res = await fetch(`${API_BASE}/catalog/dealerships`);
    const data = await res.json();
    if (Array.isArray(data) && data.length > 0) {
      cachedDealerships = data;
      return data;
    }
    return data;
  } catch (err) {
    return [
      {
        id: "bayview_bandra",
        name: "Bayview Mahindra, Bandra West",
        address: "Plot 14, Linking Road, Mumbai",
        city: "Mumbai",
        phone: "+91 22 2640 8899",
        rating: 4.9,
        available_advisors: ["Rajesh Varma (Senior Specialist)", "Pooja Mehta"],
        has_test_drive_home_pickup: true
      }
    ];
  }
}

// Customer Profile & PreSales Identification Gate
export async function identifyCustomer(payload: {
  name: string;
  phone: string;
  session_type?: string;
  vehicle_id?: string;
}) {
  const res = await fetch(`${API_BASE}/customer/identify`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  if (!res.ok) {
    const errorData = await res.json();
    throw new Error(errorData.detail?.[0]?.msg || errorData.detail || "Validation failed");
  }
  return res.json();
}

export async function saveTranscriptTurn(payload: {
  session_id: string;
  customer_id: string;
  channel?: string;
  speaker: string;
  message: string;
  extracted_intent?: string;
  tool_triggered?: string;
}) {
  const res = await fetch(`${API_BASE}/customer/transcript-turn`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  return res.json();
}

export async function fetchCustomerSessions(customerIdOrPhone: string) {
  const res = await fetch(`${API_BASE}/customer/sessions?customer_id=${encodeURIComponent(customerIdOrPhone)}`);
  return res.json();
}

export async function fetchCustomerProfile(customerId = "CUST-9820155432") {
  try {
    const res = await fetch(`${API_BASE}/customer/profile?customer_id=${customerId}`);
    return await res.json();
  } catch (err) {
    return null;
  }
}

export async function updateCustomerPhase(phase: string, customerId = "CUST-9820155432") {
  const res = await fetch(`${API_BASE}/customer/update-phase?customer_id=${customerId}&phase=${phase}`, {
    method: "POST"
  });
  return res.json();
}

export async function bookTestDrive(payload: any) {
  const res = await fetch(`${API_BASE}/bookings`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  return res.json();
}

// Stage 2: Sales Mobile App & Test Ride Recording (with SWR Cache)
export async function fetchSalesLeads(dealershipId?: string) {
  const key = dealershipId && dealershipId !== "ALL" ? dealershipId : "ALL";
  const now = Date.now();
  const existing = cachedLeadsByDealership.get(key);

  if (existing && now < existing.expiresAt) {
    return existing.data;
  }

  try {
    const url = dealershipId && dealershipId !== "ALL"
      ? `${API_BASE}/sales/leads?dealership_id=${encodeURIComponent(dealershipId)}`
      : `${API_BASE}/sales/leads`;
    const res = await fetch(url);
    const data = await res.json();
    if (Array.isArray(data)) {
      cachedLeadsByDealership.set(key, {
        data,
        expiresAt: now + 30000 // Cache for 30 seconds
      });
    }
    return data;
  } catch (err) {
    if (existing) return existing.data;
    return [];
  }
}

export async function uploadTestRideRecording(payload: any) {
  invalidateLeadsCache();
  const res = await fetch(`${API_BASE}/sales/test-ride/upload-recording`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  return res.json();
}

export async function fetchTestRideInsights(sessionId: string) {
  const res = await fetch(`${API_BASE}/sales/test-ride/insights/${sessionId}`);
  return res.json();
}

export async function fetchLatestTestRideInsights(params?: { customer_id?: string; booking_reference?: string; phone?: string }) {
  try {
    const q = new URLSearchParams();
    if (params?.customer_id) q.set("customer_id", params.customer_id);
    if (params?.booking_reference) q.set("booking_reference", params.booking_reference);
    if (params?.phone) q.set("phone", params.phone);
    const res = await fetch(`${API_BASE}/sales/test-ride/latest?${q.toString()}`);
    if (res.ok) {
      return await res.json();
    }
    return null;
  } catch (err) {
    return null;
  }
}

export async function fetchAllTestRides() {
  const res = await fetch(`${API_BASE}/sales/test-ride/all`);
  return res.json();
}

// Stage 3: Outbound Proactive Post-Ride Voice Call
export async function triggerOutboundCall(payload: any) {
  const res = await fetch(`${API_BASE}/outbound/trigger-call`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  return res.json();
}

export async function sendOutboundDialogueTurn(payload: any) {
  const res = await fetch(`${API_BASE}/outbound/dialogue-turn`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  return res.json();
}

export async function fetchOutboundCallInsights(callReference: string) {
  const res = await fetch(`${API_BASE}/outbound/call-insights/${callReference}`);
  return res.json();
}

// Diagnostics & Claims
export async function assessDamage(payload: any) {
  const res = await fetch(`${API_BASE}/diagnostics/assess-damage`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  return res.json();
}

export async function fileInsuranceClaim(payload: any) {
  const res = await fetch(`${API_BASE}/diagnostics/claims`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  return res.json();
}



export async function saveFullSessionTranscript(payload: {
  session_id: string;
  customer_id?: string;
  customer_name?: string;
  customer_phone?: string;
  vehicle_id?: string;
  channel?: string;
  messages: Array<{
    speaker: string;
    text: string;
    timestamp?: string;
    toolCall?: string;
    language?: string;
  }>;
}) {
  try {
    const res = await fetch(`${API_BASE}/customer/save-full-transcript`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    return await res.json();
  } catch (err) {
    console.debug("Failed to flush session transcript to database:", err);
    return null;
  }
}


export async function fetchAdminBookings(params?: { city?: string; vehicle_id?: string; status?: string; search?: string }) {
  try {
    const q = new URLSearchParams();
    if (params?.city) q.set("city", params.city);
    if (params?.vehicle_id) q.set("vehicle_id", params.vehicle_id);
    if (params?.status) q.set("status", params.status);
    if (params?.search) q.set("search", params.search);
    const res = await fetch(`${API_BASE}/admin/bookings?${q.toString()}`);
    if (!res.ok) return [];
    return await res.json();
  } catch (err) {
    return [];
  }
}

export async function saveOutboundCallTranscript(payload: {
  call_reference: string;
  booking_reference?: string;
  customer_id?: string;
  phone_number?: string;
  customer_name?: string;
  vehicle_name?: string;
  duration_seconds?: number;
  turns: Array<{
    speaker: string;
    role?: string;
    text?: string;
    message?: string;
    time?: string;
  }>;
}) {
  try {
    const res = await fetch(`${API_BASE}/outbound/save-call-transcript`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    return await res.json();
  } catch (err) {
    console.debug("Failed to save outbound transcript:", err);
    return null;
  }
}
