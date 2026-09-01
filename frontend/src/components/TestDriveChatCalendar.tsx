"use client";

import React, { useState, useEffect } from "react";
import {
  Calendar as CalendarIcon,
  Clock,
  MapPin,
  CheckCircle2,
  AlertCircle,
  Building2,
  Home,
  Loader2,
  Search,
  ShieldCheck,
  Star,
  Sparkles,
  Car,
  Layers,
  ChevronDown
} from "lucide-react";

interface SlotItem {
  id?: number | null;
  slot_date: string;
  slot_time: string;
  status: string;
  is_available: boolean;
  display_time: string;
  customer_name?: string | null;
}

interface DateSlotsResponse {
  date: string;
  is_blocked: boolean;
  blocked_reason?: string | null;
  is_sunday: boolean;
  is_holiday: boolean;
  holiday_name?: string | null;
  dealership_id: string;
  dealership_name: string;
  slots: SlotItem[];
}

interface DealershipData {
  id: string;
  name: string;
  address: string;
  city: string;
  phone: string;
  rating: number;
  available_advisors: string[];
}

interface VehicleVariantOption {
  name: string;
  price_ex_showroom: string;
  engine_or_battery: string;
  transmission: string;
  key_features?: string[];
}

interface VehicleCatalogItem {
  id: string;
  name: string;
  category: string;
  price_range: string;
  variants: VehicleVariantOption[];
}

const FALLBACK_VEHICLES: VehicleCatalogItem[] = [
  {
    id: "thar_roxx",
    name: "Mahindra Thar ROXX (5-Door)",
    category: "Authentic SUV",
    price_range: "₹12.52L - ₹23.52L",
    variants: [
      { name: "AX7L Diesel AT 4x4", price_ex_showroom: "₹22.49 Lakh", engine_or_battery: "2.2L mHawk Diesel (175 PS)", transmission: "6-Speed Automatic 4x4" },
      { name: "AX5L Diesel AT 4x2", price_ex_showroom: "₹18.99 Lakh", engine_or_battery: "2.2L mHawk Diesel (152 PS)", transmission: "6-Speed Automatic RWD" },
      { name: "MX5 Petrol MT 4x2", price_ex_showroom: "₹16.49 Lakh", engine_or_battery: "2.0L mStallion Turbo (177 PS)", transmission: "6-Speed Manual" },
      { name: "AX7L Petrol AT 4x2", price_ex_showroom: "₹20.99 Lakh", engine_or_battery: "2.0L mStallion Turbo (177 PS)", transmission: "6-Speed Automatic" }
    ]
  },
  {
    id: "scorpio_n",
    name: "Mahindra Scorpio-N",
    category: "Authentic SUV",
    price_range: "₹13.69L - ₹25.49L",
    variants: [
      { name: "Z8L Diesel 4WD AT", price_ex_showroom: "₹24.54 Lakh", engine_or_battery: "2.2L mHawk Diesel (175 PS / 400 Nm)", transmission: "6-Speed Automatic 4WD" },
      { name: "Z8L Petrol AT 2WD", price_ex_showroom: "₹21.98 Lakh", engine_or_battery: "2.0L mStallion Turbo (203 PS)", transmission: "6-Speed Automatic" },
      { name: "Z8 Diesel MT 4WD", price_ex_showroom: "₹21.49 Lakh", engine_or_battery: "2.2L mHawk Diesel (175 PS)", transmission: "6-Speed Manual 4WD" },
      { name: "Z6 Diesel AT 2WD", price_ex_showroom: "₹17.99 Lakh", engine_or_battery: "2.2L mHawk Diesel (175 PS)", transmission: "6-Speed Automatic" }
    ]
  },
  {
    id: "xuv700",
    name: "Mahindra XUV700",
    category: "Luxury Tech SUV",
    price_range: "₹13.99L - ₹26.04L",
    variants: [
      { name: "AX7 Luxury Diesel AT AWD", price_ex_showroom: "₹25.49 Lakh", engine_or_battery: "2.2L mHawk Diesel (185 PS)", transmission: "6-Speed Automatic AWD" },
      { name: "AX7 Diesel AT 7-Str", price_ex_showroom: "₹21.99 Lakh", engine_or_battery: "2.2L mHawk Diesel (185 PS)", transmission: "6-Speed Automatic" },
      { name: "AX5 Petrol AT 5-Str", price_ex_showroom: "₹18.49 Lakh", engine_or_battery: "2.0L mStallion Turbo (200 PS)", transmission: "6-Speed Automatic" }
    ]
  },
  {
    id: "be_6e",
    name: "Mahindra BE 6e (Born Electric)",
    category: "Electric Origin SUV",
    price_range: "₹18.90L - ₹26.90L",
    variants: [
      { name: "Pack Two (79 kWh, 682km Range)", price_ex_showroom: "₹21.90 Lakh", engine_or_battery: "79 kWh LFP Blade (285 PS)", transmission: "Single-Speed EV Direct" },
      { name: "Pack One (59 kWh, 535km Range)", price_ex_showroom: "₹18.90 Lakh", engine_or_battery: "59 kWh LFP Blade (231 PS)", transmission: "Single-Speed EV Direct" }
    ]
  },
  {
    id: "xev_9e",
    name: "Mahindra XEV 9e (Electric Luxury Coupe)",
    category: "Electric Origin SUV",
    price_range: "₹21.90L - ₹30.50L",
    variants: [
      { name: "Pack Two (79 kWh, 656km Range)", price_ex_showroom: "₹24.90 Lakh", engine_or_battery: "79 kWh LFP Battery (285 PS)", transmission: "Single-Speed EV Direct" },
      { name: "Pack One (59 kWh, 512km Range)", price_ex_showroom: "₹21.90 Lakh", engine_or_battery: "59 kWh LFP Battery (231 PS)", transmission: "Single-Speed EV Direct" }
    ]
  },
  {
    id: "xuv_3xo",
    name: "Mahindra XUV 3XO",
    category: "Compact SUV",
    price_range: "₹7.49L - ₹15.49L",
    variants: [
      { name: "AX7L TGDi Petrol AT (Level 2 ADAS)", price_ex_showroom: "₹13.99 Lakh", engine_or_battery: "1.2L mStallion TGDi (130 PS)", transmission: "6-Speed AISIN AT" },
      { name: "AX5 Diesel MT", price_ex_showroom: "₹11.49 Lakh", engine_or_battery: "1.5L Turbo Diesel (117 PS)", transmission: "6-Speed Manual" }
    ]
  },
  {
    id: "thar_3door",
    name: "Mahindra Thar (3-Door)",
    category: "Authentic Off-Roader",
    price_range: "₹11.35L - ₹17.60L",
    variants: [
      { name: "LX Hard Top Diesel 4x4 AT", price_ex_showroom: "₹17.60 Lakh", engine_or_battery: "2.2L mHawk Diesel (130 PS)", transmission: "6-Speed Automatic 4x4" },
      { name: "LX Hard Top Diesel 4x4 MT", price_ex_showroom: "₹16.20 Lakh", engine_or_battery: "2.2L mHawk Diesel (130 PS)", transmission: "6-Speed Manual 4x4" }
    ]
  },
  {
    id: "scorpio_classic",
    name: "Mahindra Scorpio Classic",
    category: "Authentic SUV",
    price_range: "₹13.62L - ₹17.49L",
    variants: [
      { name: "S11 Diesel MT 7-Str", price_ex_showroom: "₹17.49 Lakh", engine_or_battery: "2.2L mHawk Gen-2 Diesel (132 PS)", transmission: "6-Speed Manual" },
      { name: "S Diesel MT 9-Str", price_ex_showroom: "₹13.62 Lakh", engine_or_battery: "2.2L mHawk Gen-2 Diesel (132 PS)", transmission: "6-Speed Manual" }
    ]
  }
];

const CITIES = [
  { name: "Mumbai", samplePin: "400050" },
  { name: "Pune", samplePin: "411001" },
  { name: "Delhi", samplePin: "110044" },
  { name: "Bangalore", samplePin: "560068" },
  { name: "Chennai", samplePin: "600035" }
];

interface TestDriveChatCalendarProps {
  vehicleId?: string;
  vehicleName?: string;
  initialVariant?: string;
  customerName?: string;
  customerPhone?: string;
  onSlotBooked?: (bookingData: any) => void;
  onClose?: () => void;
}

export function TestDriveChatCalendar({
  vehicleId = "thar_roxx",
  vehicleName = "Mahindra Thar ROXX",
  initialVariant = "AX7L Diesel AT 4x4",
  customerName = "Aarav Sharma",
  customerPhone = "+91 98196 57034",
  onSlotBooked,
  onClose
}: TestDriveChatCalendarProps) {
  // Vehicle & Variant State
  const [vehiclesList, setVehiclesList] = useState<VehicleCatalogItem[]>(FALLBACK_VEHICLES);
  const [selectedVehId, setSelectedVehId] = useState<string>(vehicleId);
  const [selectedVariantName, setSelectedVariantName] = useState<string>(initialVariant);

  // Confirmation state: Slot options open ONLY if user confirms
  const [isConfirmedByUser, setIsConfirmedByUser] = useState<boolean>(false);

  // Pin code & Showroom resolution
  const [pinCode, setPinCode] = useState<string>("400050");
  const [selectedCity, setSelectedCity] = useState<string>("Mumbai");
  const [dealershipsInCity, setDealershipsInCity] = useState<DealershipData[]>([]);
  const [activeDealership, setActiveDealership] = useState<DealershipData | null>(null);

  // Dates state
  const [datesList, setDatesList] = useState<
    Array<{
      dateStr: string;
      dayOfWeek: string;
      dayNum: string;
      monthStr: string;
      isSunday: boolean;
    }>
  >([]);

  const [selectedDate, setSelectedDate] = useState<string>("");
  const [slotsData, setSlotsData] = useState<DateSlotsResponse | null>(null);
  const [selectedSlot, setSelectedSlot] = useState<string>("");
  const [bookingType, setBookingType] = useState<"HOME_DOORSTEP" | "SHOWROOM_VISIT">("HOME_DOORSTEP");
  const [deliveryAddress, setDeliveryAddress] = useState<string>("");
  const [isLoadingSlots, setIsLoadingSlots] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [confirmedBooking, setConfirmedBooking] = useState<any>(null);

  // Load catalog from API on mount
  useEffect(() => {
    async function loadCatalog() {
      try {
        const res = await fetch("/api/catalog");
        if (res.ok) {
          const data = await res.json();
          if (Array.isArray(data) && data.length > 0) {
            setVehiclesList(data);
          }
        }
      } catch (e) {
        console.debug("Using fallback vehicles catalog:", e);
      }
    }
    loadCatalog();
  }, []);

  // Update selected vehicle & variant if props change
  useEffect(() => {
    if (vehicleId) {
      setSelectedVehId(vehicleId);
      const vObj = vehiclesList.find((v) => v.id === vehicleId);
      if (vObj && vObj.variants && vObj.variants.length > 0) {
        const matchingVar = vObj.variants.find((vr) => vr.name === initialVariant);
        setSelectedVariantName(matchingVar ? matchingVar.name : vObj.variants[0].name);
      }
    }
  }, [vehicleId, initialVariant, vehiclesList]);

  // Current active vehicle object and its variants
  const activeVehicle = vehiclesList.find((v) => v.id === selectedVehId) || vehiclesList[0];
  const currentVariants = activeVehicle?.variants || [];
  const activeVariantObj =
    currentVariants.find((v) => v.name === selectedVariantName) || currentVariants[0];

  // Initialize dates list (next 14 days)
  useEffect(() => {
    const list: typeof datesList = [];
    const today = new Date();
    for (let i = 1; i <= 14; i++) {
      const d = new Date(today);
      d.setDate(today.getDate() + i);
      const year = d.getFullYear();
      const month = String(d.getMonth() + 1).padStart(2, "0");
      const day = String(d.getDate()).padStart(2, "0");
      const dateStr = `${year}-${month}-${day}`;
      const isSunday = d.getDay() === 0;

      list.push({
        dateStr,
        dayOfWeek: d.toLocaleDateString("en-IN", { weekday: "short" }),
        dayNum: String(d.getDate()),
        monthStr: d.toLocaleDateString("en-IN", { month: "short" }),
        isSunday
      });
    }
    setDatesList(list);

    const firstValid = list.find((d) => !d.isSunday);
    if (firstValid) {
      setSelectedDate(firstValid.dateStr);
    }
  }, []);

  // Fetch dealerships for selected city
  const fetchDealershipsForCity = async (cityName: string) => {
    try {
      const res = await fetch(`/api/catalog/dealerships?city=${cityName}`);
      if (res.ok) {
        const data: DealershipData[] = await res.json();
        setDealershipsInCity(data);
        if (data.length > 0) {
          setActiveDealership(data[0]);
        }
      }
    } catch (err) {
      console.error("Error fetching dealerships:", err);
    }
  };

  useEffect(() => {
    fetchDealershipsForCity(selectedCity);
  }, [selectedCity]);

  // Handle PIN Code change
  const handlePinCodeChange = (pin: string) => {
    setPinCode(pin);
    const cleanPin = pin.trim();
    if (cleanPin.length === 6) {
      let detectedCity = "Mumbai";
      if (cleanPin.startsWith("400") || cleanPin.startsWith("401")) detectedCity = "Mumbai";
      else if (cleanPin.startsWith("411") || cleanPin.startsWith("412")) detectedCity = "Pune";
      else if (cleanPin.startsWith("110") || cleanPin.startsWith("122") || cleanPin.startsWith("201")) detectedCity = "Delhi";
      else if (cleanPin.startsWith("560")) detectedCity = "Bangalore";
      else if (cleanPin.startsWith("600")) detectedCity = "Chennai";

      setSelectedCity(detectedCity);
      fetchDealershipsForCity(detectedCity);
    }
  };

  // Fetch slots from DB ONLY when user confirms booking and selects date
  useEffect(() => {
    if (!isConfirmedByUser || !selectedDate) return;

    const fetchSlots = async () => {
      setIsLoadingSlots(true);
      setErrorMsg(null);
      setSelectedSlot("");
      try {
        const dId = activeDealership?.id || "";
        const queryParams = new URLSearchParams({
          date: selectedDate,
          vehicle_id: selectedVehId,
          pin_code: pinCode,
          ...(dId ? { dealership_id: dId } : {})
        });

        const res = await fetch(`/api/bookings/available-slots?${queryParams.toString()}`);
        if (res.ok) {
          const data: DateSlotsResponse = await res.json();
          setSlotsData(data);
          const firstAvail = data.slots?.find((s) => s.is_available);
          if (firstAvail) {
            setSelectedSlot(firstAvail.slot_time);
          }
        } else {
          let msg = "Failed to load slots from database.";
          try {
            const err = await res.json();
            msg = err.detail || msg;
          } catch (e) {}
          setErrorMsg(msg);
        }
      } catch (err: any) {
        console.debug("Error fetching slots:", err);
        setErrorMsg("Could not connect to database slots API.");
      } finally {
        setIsLoadingSlots(false);
      }
    };

    fetchSlots();
  }, [isConfirmedByUser, selectedDate, activeDealership, pinCode, selectedVehId]);

  // Handle slot reservation
  const handleReserveSlot = async () => {
    if (!selectedDate || !selectedSlot) {
      setErrorMsg("Please select a date and an available time slot.");
      return;
    }

    if (bookingType === "HOME_DOORSTEP" && !deliveryAddress.trim()) {
      setErrorMsg("Please enter your doorstep delivery address.");
      return;
    }

    setIsSubmitting(true);
    setErrorMsg(null);
    try {
      const deliveryLocation =
        bookingType === "HOME_DOORSTEP"
          ? deliveryAddress.trim()
          : `Showroom Visit (${activeDealership?.name || "Mahindra Showroom"})`;

      const res = await fetch("/api/bookings/reserve-slot", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          slot_date: selectedDate,
          slot_time: selectedSlot,
          customer_name: customerName,
          customer_phone: customerPhone,
          vehicle_id: selectedVehId,
          variant: activeVariantObj?.name || selectedVariantName,
          dealership_id: activeDealership?.id,
          pin_code: pinCode,
          booking_type: bookingType,
          delivery_address: deliveryLocation
        })
      });

      if (res.ok) {
        const data = await res.json();
        setConfirmedBooking(data);
        if (onSlotBooked) {
          onSlotBooked(data);
        }
      } else {
        let msg = "Slot could not be reserved. Please try another.";
        try {
          const err = await res.json();
          msg = err.detail || msg;
        } catch (e) {}
        setErrorMsg(msg);
      }
    } catch (err: any) {
      setErrorMsg("Connection error while reserving slot in database.");
    } finally {
      setIsSubmitting(false);
    }
  };

  if (confirmedBooking) {
    return (
      <div className="my-2 p-3.5 rounded-2xl bg-gradient-to-b from-slate-900 via-slate-900 to-emerald-950/40 border border-emerald-500/40 text-white shadow-xl animate-in fade-in zoom-in-95 duration-200">
        <div className="flex items-center gap-2 text-emerald-400 font-bold text-xs mb-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          <span>Test Ride Reserved in Database</span>
        </div>

        <div className="bg-black/40 border border-emerald-500/30 rounded-xl p-3 space-y-2 text-[11px]">
          <div className="flex justify-between items-center pb-1.5 border-b border-white/10">
            <span className="text-slate-400">Booking Reference:</span>
            <span className="font-mono font-black text-amber-400 text-xs">
              {confirmedBooking.booking_reference}
            </span>
          </div>

          <div className="flex justify-between items-center">
            <span className="text-slate-400">Vehicle:</span>
            <span className="font-bold text-white">{confirmedBooking.vehicle_name}</span>
          </div>

          <div className="flex justify-between items-center">
            <span className="text-slate-400">Variant Chosen:</span>
            <span className="font-bold text-red-300">{activeVariantObj?.name || selectedVariantName}</span>
          </div>

          <div className="flex justify-between items-center">
            <span className="text-slate-400">Showroom (DB):</span>
            <span className="font-bold text-slate-200 text-right">{confirmedBooking.dealership_name}</span>
          </div>

          <div className="flex justify-between items-center">
            <span className="text-slate-400">Date &amp; Slot:</span>
            <span className="font-bold text-cyan-300">
              {confirmedBooking.slot_date} at {confirmedBooking.slot_time}
            </span>
          </div>

          <div className="flex justify-between items-center">
            <span className="text-slate-400">Type &amp; Address:</span>
            <span className="font-medium text-slate-200 text-right max-w-[200px] truncate">
              {confirmedBooking.booking_type === "HOME_DOORSTEP"
                ? `Doorstep: ${confirmedBooking.delivery_address}`
                : "Showroom Visit"}
            </span>
          </div>

          <div className="flex justify-between items-center">
            <span className="text-slate-400">Assigned Specialist:</span>
            <span className="text-slate-200">{confirmedBooking.sales_advisor_name}</span>
          </div>
        </div>

        <div className="mt-2.5 p-2 rounded-lg bg-emerald-950/30 border border-emerald-500/20 text-[10px] text-emerald-300 flex items-center gap-2">
          <ShieldCheck className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
          <span>Status saved as <strong>RESERVED</strong> in DB &amp; WhatsApp dispatched.</span>
        </div>
      </div>
    );
  }

  return (
    <div className="my-2 p-3.5 rounded-2xl bg-gradient-to-b from-slate-900 to-slate-950 border border-cyan-500/30 text-white shadow-2xl text-left w-full max-w-full">
      {/* Header */}
      <div className="flex items-center justify-between pb-2.5 border-b border-white/10 mb-3">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-red-600/20 border border-red-500/40 text-red-400">
            <CalendarIcon className="w-3.5 h-3.5" />
          </div>
          <div>
            <h4 className="text-xs font-black text-white tracking-tight flex items-center gap-1.5">
              <span>Book Test Ride</span>
              <span className="text-[9px] px-1.5 py-0.2 rounded bg-cyan-950 text-cyan-400 border border-cyan-500/30 font-mono">
                9 AM - 6 PM
              </span>
            </h4>
            <p className="text-[10px] text-slate-400">{activeVehicle?.name}</p>
          </div>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white text-xs px-2 py-0.5 rounded bg-white/5"
          >
            ✕
          </button>
        )}
      </div>

      {/* Step 1: Vehicle Model & Specific Variant Selection */}
      <div className="mb-3 space-y-2 p-2.5 rounded-xl bg-black/40 border border-white/10">
        <label className="text-[10.5px] font-bold text-slate-300 flex items-center justify-between">
          <span className="flex items-center gap-1">
            <Car className="w-3 h-3 text-red-400" />
            <span>1. Choose Vehicle &amp; Variant</span>
          </span>
          <span className="text-[9px] text-red-400 font-mono font-bold">
            {activeVehicle?.price_range}
          </span>
        </label>

        {/* Vehicle Model Selector */}
        <select
          value={selectedVehId}
          onChange={(e) => {
            const newVehId = e.target.value;
            setSelectedVehId(newVehId);
            const vObj = vehiclesList.find((v) => v.id === newVehId);
            if (vObj && vObj.variants && vObj.variants.length > 0) {
              setSelectedVariantName(vObj.variants[0].name);
            }
          }}
          className="w-full text-xs font-bold px-2.5 py-1.5 rounded-lg bg-slate-900 border border-white/20 focus:border-cyan-400 text-white outline-none"
        >
          {vehiclesList.map((v) => (
            <option key={v.id} value={v.id} className="bg-slate-900 text-white">
              {v.name} ({v.category})
            </option>
          ))}
        </select>

        {/* Variant Selector */}
        {currentVariants.length > 0 && (
          <div className="space-y-1 pt-1">
            <div className="flex items-center justify-between text-[9.5px] text-slate-400">
              <span className="flex items-center gap-1">
                <Layers className="w-2.5 h-2.5 text-cyan-400" /> Specific Variant:
              </span>
              <span className="text-amber-400 font-mono font-bold">
                {activeVariantObj?.price_ex_showroom}
              </span>
            </div>

            <select
              value={activeVariantObj?.name || selectedVariantName}
              onChange={(e) => setSelectedVariantName(e.target.value)}
              className="w-full text-[11px] font-bold px-2 py-1.5 rounded-lg bg-black/60 border border-cyan-500/40 text-cyan-200 outline-none"
            >
              {currentVariants.map((vr) => (
                <option key={vr.name} value={vr.name} className="bg-slate-900 text-white">
                  {vr.name} — {vr.price_ex_showroom} ({vr.transmission})
                </option>
              ))}
            </select>

            {activeVariantObj && (
              <p className="text-[9px] text-slate-400 pt-0.5">
                ⚙️ {activeVariantObj.engine_or_battery} • {activeVariantObj.transmission}
              </p>
            )}
          </div>
        )}
      </div>

      {/* Step 2: Area PIN Code & Showroom Locator */}
      <div className="mb-3 space-y-2">
        <label className="text-[10.5px] font-bold text-slate-300 flex items-center justify-between">
          <span className="flex items-center gap-1">
            <MapPin className="w-3 h-3 text-red-400" />
            <span>2. Showroom &amp; Area PIN Code</span>
          </span>
          <span className="text-[9px] text-cyan-400 font-mono">
            {dealershipsInCity.length} Showrooms Found
          </span>
        </label>

        {/* PIN Code Input and City Chips */}
        <div className="flex items-center gap-1.5">
          <div className="relative flex-1">
            <input
              type="text"
              maxLength={6}
              value={pinCode}
              onChange={(e) => handlePinCodeChange(e.target.value)}
              placeholder="e.g. 400050"
              className="w-full text-xs font-mono font-bold px-2.5 py-1.5 rounded-lg bg-black/60 border border-white/20 focus:border-cyan-400 text-white placeholder-slate-500 outline-none"
            />
            <Search className="w-3.5 h-3.5 text-slate-400 absolute right-2.5 top-2.5 pointer-events-none" />
          </div>

          <div className="flex gap-1 overflow-x-auto scrollbar-thin">
            {CITIES.map((c) => (
              <button
                key={c.name}
                type="button"
                onClick={() => {
                  setSelectedCity(c.name);
                  setPinCode(c.samplePin);
                  fetchDealershipsForCity(c.name);
                }}
                className={`px-2 py-1 rounded-lg text-[10px] font-bold transition-all shrink-0 ${
                  selectedCity === c.name
                    ? "bg-red-600 text-white shadow-xs"
                    : "bg-white/5 text-slate-400 hover:text-white"
                }`}
              >
                {c.name}
              </button>
            ))}
          </div>
        </div>

        {/* Showroom Selector / Card */}
        {dealershipsInCity.length > 0 && (
          <div className="p-2 rounded-xl bg-black/40 border border-white/10 space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="text-[10px] text-slate-400 flex items-center gap-1">
                <Building2 className="w-3 h-3 text-cyan-400" /> Assigned Showroom:
              </span>
              {activeDealership && (
                <span className="text-[9.5px] text-amber-400 font-bold flex items-center gap-0.5">
                  <Star className="w-2.5 h-2.5 fill-amber-400" /> {activeDealership.rating}
                </span>
              )}
            </div>

            <select
              value={activeDealership?.id || ""}
              onChange={(e) => {
                const match = dealershipsInCity.find((d) => d.id === e.target.value);
                if (match) setActiveDealership(match);
              }}
              className="w-full text-[11px] font-bold px-2 py-1.5 rounded-lg bg-slate-900 border border-white/15 focus:border-cyan-400 text-white outline-none"
            >
              {dealershipsInCity.map((d) => (
                <option key={d.id} value={d.id} className="bg-slate-900 text-white">
                  {d.name} ({d.city})
                </option>
              ))}
            </select>

            {activeDealership && (
              <p className="text-[9.5px] text-slate-400 leading-tight">
                📍 {activeDealership.address}
              </p>
            )}
          </div>
        )}
      </div>

      {/* CONFIRMATION GATE: Only if User confirms Test ride booking, then only Open the slot options */}
      {!isConfirmedByUser ? (
        <div className="mt-3 p-3 rounded-xl bg-gradient-to-r from-red-950/40 via-black to-slate-900 border border-red-500/30 text-center space-y-2.5">
          <div className="flex items-center justify-center gap-1.5 text-amber-300 text-[11px] font-bold">
            <Sparkles className="w-3.5 h-3.5 text-amber-400" />
            <span>Confirm Test Ride Request</span>
          </div>

          <p className="text-[11px] text-slate-200">
            Would you like to book a test drive for <strong>{activeVehicle?.name}</strong> (
            <span className="text-red-400">{activeVariantObj?.name || selectedVariantName}</span>) at{" "}
            <strong>{activeDealership?.name || "Mahindra Showroom"}</strong>?
          </p>

          <p className="text-[9.5px] text-slate-400">
            Click confirm to reveal live available database calendar slots (Mon-Sat, 9 AM - 6 PM).
          </p>

          <div className="flex gap-2 pt-1">
            {onClose && (
              <button
                type="button"
                onClick={onClose}
                className="flex-1 py-2 px-3 rounded-xl bg-white/5 hover:bg-white/10 text-slate-400 hover:text-white text-xs font-bold transition-all"
              >
                Cancel
              </button>
            )}
            <button
              type="button"
              onClick={() => setIsConfirmedByUser(true)}
              className="flex-2 py-2 px-3 rounded-xl bg-gradient-to-r from-red-600 to-red-700 hover:from-red-500 hover:to-red-600 text-white text-xs font-black transition-all shadow-md flex items-center justify-center gap-1.5 cursor-pointer"
            >
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
              <span>Yes, Book Test Ride (Open Slots)</span>
            </button>
          </div>
        </div>
      ) : (
        <div className="space-y-3 animate-in fade-in slide-in-from-top-2 duration-200">
          {/* Rules Notice */}
          <div className="px-2.5 py-1.5 rounded-lg bg-amber-950/20 border border-amber-500/20 text-[10px] text-amber-300/90 flex items-center gap-1.5">
            <AlertCircle className="w-3 h-3 text-amber-400 shrink-0" />
            <span>Sundays &amp; National Holidays closed. Allowed slots: <strong>9:00 AM - 6:00 PM</strong>.</span>
          </div>

          {/* Step 3: Select Date */}
          <div>
            <label className="text-[10.5px] font-bold text-slate-300 mb-1.5 flex items-center justify-between">
              <span>3. Select Date</span>
              <span className="text-[9px] text-slate-400 font-mono">Mon - Sat only</span>
            </label>

            <div className="flex gap-1.5 overflow-x-auto pb-1 scrollbar-thin scrollbar-thumb-slate-700">
              {datesList.map((d) => {
                const isSelected = selectedDate === d.dateStr;
                const isBlocked = d.isSunday;

                return (
                  <button
                    key={d.dateStr}
                    disabled={isBlocked}
                    onClick={() => setSelectedDate(d.dateStr)}
                    title={
                      d.isSunday
                        ? "Sundays are closed for test rides"
                        : `Select ${d.dayOfWeek}, ${d.dayNum} ${d.monthStr}`
                    }
                    className={`shrink-0 flex flex-col items-center justify-center p-2 rounded-xl border transition-all text-center min-w-[58px] ${
                      isSelected
                        ? "bg-gradient-to-b from-red-600 to-red-700 border-red-400 text-white shadow-[0_0_12px_rgba(227,24,55,0.4)] scale-102"
                        : isBlocked
                        ? "bg-white/3 border-white/5 opacity-40 cursor-not-allowed text-slate-500"
                        : "bg-white/5 border-white/10 hover:border-cyan-400/50 text-slate-300 hover:text-white"
                    }`}
                  >
                    <span className="text-[9px] font-bold uppercase">{d.dayOfWeek}</span>
                    <span className="text-sm font-black my-0.5">{d.dayNum}</span>
                    <span className="text-[9px] text-slate-400 font-mono">
                      {d.isSunday ? (
                        <span className="text-red-400 font-bold">Sun</span>
                      ) : (
                        d.monthStr
                      )}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Step 4: Available Slots from Database */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-[10.5px] font-bold text-slate-300 flex items-center gap-1.5">
                <Clock className="w-3 h-3 text-cyan-400" />
                <span>4. Available Slots (DB Verified)</span>
              </label>
              {isLoadingSlots && (
                <span className="text-[10px] text-cyan-400 flex items-center gap-1">
                  <Loader2 className="w-2.5 h-2.5 animate-spin" /> Querying DB...
                </span>
              )}
            </div>

            {slotsData?.is_blocked ? (
              <div className="p-3 rounded-xl bg-red-950/30 border border-red-500/30 text-center text-xs text-red-300">
                <p className="font-bold">{slotsData.blocked_reason}</p>
                <p className="text-[10px] text-slate-400 mt-1">
                  Please choose another working day (Mon-Sat).
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-3 gap-1.5">
                {slotsData?.slots?.map((slot) => {
                  const isSelected = selectedSlot === slot.slot_time;
                  const isAvailable = slot.is_available;

                  return (
                    <button
                      key={slot.slot_time}
                      disabled={!isAvailable}
                      onClick={() => setSelectedSlot(slot.slot_time)}
                      className={`p-2 rounded-xl border text-center transition-all ${
                        isSelected
                          ? "bg-cyan-500 text-slate-950 border-cyan-300 font-black shadow-[0_0_12px_rgba(0,229,255,0.4)]"
                          : isAvailable
                          ? "bg-white/5 border-white/10 hover:border-cyan-400/60 text-slate-200 hover:text-white"
                          : "bg-white/2 border-white/5 text-slate-600 line-through cursor-not-allowed opacity-40"
                      }`}
                    >
                      <div className="text-[11px] font-bold">{slot.slot_time}</div>
                      <div className="text-[8.5px] font-mono mt-0.5">
                        {isAvailable ? (
                          <span className={isSelected ? "text-slate-900 font-bold" : "text-emerald-400"}>
                            Available
                          </span>
                        ) : (
                          <span className="text-red-400">Reserved</span>
                        )}
                      </div>
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          {/* Step 5: Booking Option & Doorstep Address */}
          <div className="space-y-2">
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setBookingType("HOME_DOORSTEP")}
                className={`flex-1 py-1.5 px-2 rounded-lg text-[10px] font-bold flex items-center justify-center gap-1.5 border transition-all ${
                  bookingType === "HOME_DOORSTEP"
                    ? "bg-red-600/20 border-red-500 text-white"
                    : "bg-white/5 border-white/10 text-slate-400"
                }`}
              >
                <Home className="w-3 h-3" /> Doorstep Delivery
              </button>
              <button
                type="button"
                onClick={() => setBookingType("SHOWROOM_VISIT")}
                className={`flex-1 py-1.5 px-2 rounded-lg text-[10px] font-bold flex items-center justify-center gap-1.5 border transition-all ${
                  bookingType === "SHOWROOM_VISIT"
                    ? "bg-red-600/20 border-red-500 text-white"
                    : "bg-white/5 border-white/10 text-slate-400"
                }`}
              >
                <Building2 className="w-3 h-3" /> Showroom Visit
              </button>
            </div>

            {bookingType === "HOME_DOORSTEP" && (
              <div>
                <input
                  type="text"
                  value={deliveryAddress}
                  onChange={(e) => setDeliveryAddress(e.target.value)}
                  placeholder="Enter Doorstep Delivery Address (e.g. Flat 301, Koregaon Park)"
                  className="w-full text-xs px-2.5 py-1.5 rounded-lg bg-black/40 border border-white/10 focus:border-cyan-400 text-white placeholder-slate-500 outline-none"
                />
                {!deliveryAddress.trim() && (
                  <p className="text-[9.5px] text-amber-400/90 mt-1 flex items-center gap-1">
                    <span>⚠️ Address is required for Doorstep Test Drive booking.</span>
                  </p>
                )}
              </div>
            )}
          </div>

          {errorMsg && (
            <div className="p-2 rounded-lg bg-red-950/40 border border-red-500/40 text-[10px] text-red-300 flex items-center gap-1.5">
              <AlertCircle className="w-3 h-3 shrink-0" /> {errorMsg}
            </div>
          )}

          {/* Confirm & Reserve Button */}
          {(() => {
            const isAddressMissing = bookingType === "HOME_DOORSTEP" && !deliveryAddress.trim();
            const isButtonDisabled =
              isSubmitting || !selectedSlot || Boolean(slotsData?.is_blocked) || isAddressMissing;

            return (
              <button
                onClick={handleReserveSlot}
                disabled={isButtonDisabled}
                className={`w-full py-2.5 px-3 rounded-xl font-black text-xs flex items-center justify-center gap-2 transition-all shadow-lg ${
                  !isButtonDisabled
                    ? "bg-gradient-to-r from-red-600 to-red-700 hover:from-red-500 hover:to-red-600 text-white shadow-red-900/40 hover:scale-[1.01] active:scale-98 cursor-pointer"
                    : "bg-white/5 border border-white/5 text-slate-500 cursor-not-allowed opacity-50"
                }`}
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    <span>Reserving in Database...</span>
                  </>
                ) : isAddressMissing ? (
                  <span>Enter Address to Confirm Slot</span>
                ) : (
                  <>
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                    <span>
                      Confirm &amp; Reserve {activeVariantObj?.name ? `(${activeVariantObj.name})` : "Slot"}
                    </span>
                  </>
                )}
              </button>
            );
          })()}
        </div>
      )}
    </div>
  );
}
