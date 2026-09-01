"use client";

import React, { useState } from "react";
import { VehicleItem, DealershipItem } from "@/types";
import { bookTestDrive } from "@/lib/api";
import { X, Calendar, MapPin, CheckCircle2, Clock, Car } from "lucide-react";

interface TestDriveModalProps {
  isOpen: boolean;
  onClose: () => void;
  vehicle: VehicleItem | null;
  dealerships: DealershipItem[];
  customerId: string;
  onBookingSuccess: (booking: any) => void;
}

export function TestDriveModal({
  isOpen,
  onClose,
  vehicle,
  dealerships,
  customerId,
  onBookingSuccess
}: TestDriveModalProps) {
  const [selectedVariant, setSelectedVariant] = useState(vehicle?.variants[0]?.name || "");
  const [selectedColor, setSelectedColor] = useState("Stealth Black");
  const [bookingType, setBookingType] = useState<"HOME_DOORSTEP" | "SHOWROOM_VISIT">("HOME_DOORSTEP");
  const [selectedDealership, setSelectedDealership] = useState(dealerships[0]?.id || "bayview_bandra");
  const [date, setDate] = useState("Tomorrow");
  const [timeSlot, setTimeSlot] = useState("5:00 PM");
  const [notes, setNotes] = useState("Please focus on suspension comfort along Bandra-Worli Sea Link.");
  const [loading, setLoading] = useState(false);
  const [bookingResult, setBookingResult] = useState<any>(null);

  if (!isOpen || !vehicle) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const payload = {
        customer_id: customerId,
        vehicle_id: vehicle.id,
        variant: selectedVariant || vehicle.variants[0]?.name,
        color: selectedColor,
        dealership_id: selectedDealership,
        booking_type: bookingType,
        delivery_address: "Linking Road Office, Bandra West, Mumbai",
        scheduled_date: date,
        scheduled_time_slot: timeSlot,
        notes: notes
      };
      const res = await bookTestDrive(payload);
      setBookingResult(res);
      onBookingSuccess(res);
    } catch (err) {
      console.error("Booking error:", err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-mahindra-card border border-mahindra-border rounded-2xl w-full max-w-xl max-h-[90vh] overflow-y-auto shadow-2xl">
        {/* Header */}
        <div className="p-4 border-b border-mahindra-border flex items-center justify-between sticky top-0 bg-mahindra-card z-10">
          <div className="flex items-center gap-2">
            <Calendar className="w-5 h-5 text-mahindra-red" />
            <div>
              <h2 className="text-sm font-bold text-white uppercase tracking-wider">Book Test Drive</h2>
              <p className="text-xs text-gray-400">{vehicle.name}</p>
            </div>
          </div>
          <button onClick={onClose} className="p-1 text-gray-400 hover:text-white rounded-lg">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content / Form */}
        {bookingResult ? (
          <div className="p-6 text-center space-y-4">
            <div className="w-14 h-14 bg-emerald-500/20 border border-emerald-500 rounded-full flex items-center justify-center mx-auto text-emerald-400">
              <CheckCircle2 className="w-8 h-8" />
            </div>
            <h3 className="text-lg font-bold text-white">Test Drive Confirmed!</h3>
            <p className="text-xs text-gray-300">
              Booking Ref: <span className="font-mono text-mahindra-red font-bold">{bookingResult.booking_reference}</span>
            </p>
            <div className="bg-mahindra-dark p-4 rounded-xl text-left text-xs space-y-2 border border-mahindra-border">
              <div className="flex justify-between">
                <span className="text-gray-400">Vehicle:</span>
                <span className="text-white font-semibold">{bookingResult.variant}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Dealership:</span>
                <span className="text-white">{bookingResult.dealership_name}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Assigned Specialist:</span>
                <span className="text-emerald-400 font-semibold">{bookingResult.sales_advisor_name}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Time & Location:</span>
                <span className="text-white">{bookingResult.scheduled_date} at {bookingResult.scheduled_time_slot} ({bookingResult.booking_type === "HOME_DOORSTEP" ? "Doorstep" : "Showroom"})</span>
              </div>
            </div>
            <button
              onClick={onClose}
              className="w-full bg-mahindra-red hover:bg-red-600 text-white font-bold py-2 rounded-xl text-xs transition-all"
            >
              Done & Return to Showcase
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="p-6 space-y-4 text-xs">
            {/* Step 1: Variant Selection */}
            <div>
              <label className="block text-gray-300 font-semibold mb-1.5">Select Variant</label>
              <select
                value={selectedVariant || vehicle.variants[0]?.name}
                onChange={(e) => setSelectedVariant(e.target.value)}
                className="w-full bg-mahindra-dark border border-mahindra-border rounded-xl px-3 py-2 text-white focus:outline-none focus:border-mahindra-red"
              >
                {vehicle.variants.map((v, i) => (
                  <option key={i} value={v.name}>
                    {v.name} — {v.price_ex_showroom} ({v.engine_or_battery})
                  </option>
                ))}
              </select>
            </div>

            {/* Step 2: Drive Location Type */}
            <div>
              <label className="block text-gray-300 font-semibold mb-1.5">Test Drive Mode</label>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => setBookingType("HOME_DOORSTEP")}
                  className={`p-3 rounded-xl border flex items-center gap-2 ${
                    bookingType === "HOME_DOORSTEP"
                      ? "border-mahindra-red bg-mahindra-red/10 text-white"
                      : "border-mahindra-border bg-mahindra-dark text-gray-400"
                  }`}
                >
                  <Car className="w-4 h-4 text-mahindra-red" />
                  <div className="text-left">
                    <div className="font-semibold">Home / Office Pickup</div>
                    <div className="text-[10px] text-gray-400">Advisor brings SUV to you</div>
                  </div>
                </button>

                <button
                  type="button"
                  onClick={() => setBookingType("SHOWROOM_VISIT")}
                  className={`p-3 rounded-xl border flex items-center gap-2 ${
                    bookingType === "SHOWROOM_VISIT"
                      ? "border-mahindra-red bg-mahindra-red/10 text-white"
                      : "border-mahindra-border bg-mahindra-dark text-gray-400"
                  }`}
                >
                  <MapPin className="w-4 h-4 text-mahindra-red" />
                  <div className="text-left">
                    <div className="font-semibold">Showroom Experience</div>
                    <div className="text-[10px] text-gray-400">Visit Dealership</div>
                  </div>
                </button>
              </div>
            </div>

            {/* Step 3: Dealership Assignment */}
            <div>
              <label className="block text-gray-300 font-semibold mb-1.5">Assigned Dealership</label>
              <select
                value={selectedDealership}
                onChange={(e) => setSelectedDealership(e.target.value)}
                className="w-full bg-mahindra-dark border border-mahindra-border rounded-xl px-3 py-2 text-white focus:outline-none focus:border-mahindra-red"
              >
                {dealerships.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name} (Rating: {d.rating}★)
                  </option>
                ))}
              </select>
            </div>

            {/* Step 4: Date & Slot */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-gray-300 font-semibold mb-1.5">Date</label>
                <input
                  type="text"
                  value={date}
                  onChange={(e) => setDate(e.target.value)}
                  className="w-full bg-mahindra-dark border border-mahindra-border rounded-xl px-3 py-2 text-white focus:outline-none focus:border-mahindra-red"
                />
              </div>
              <div>
                <label className="block text-gray-300 font-semibold mb-1.5">Time Slot</label>
                <select
                  value={timeSlot}
                  onChange={(e) => setTimeSlot(e.target.value)}
                  className="w-full bg-mahindra-dark border border-mahindra-border rounded-xl px-3 py-2 text-white focus:outline-none focus:border-mahindra-red"
                >
                  <option value="11:00 AM">11:00 AM</option>
                  <option value="2:00 PM">2:00 PM</option>
                  <option value="5:00 PM">5:00 PM (Recommended)</option>
                  <option value="6:30 PM">6:30 PM</option>
                </select>
              </div>
            </div>

            {/* Step 5: Special Note / Focus */}
            <div>
              <label className="block text-gray-300 font-semibold mb-1.5">Test Drive Notes for Advisor</label>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={2}
                className="w-full bg-mahindra-dark border border-mahindra-border rounded-xl px-3 py-2 text-white focus:outline-none focus:border-mahindra-red resize-none"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-mahindra-red hover:bg-red-600 disabled:opacity-50 text-white font-bold py-2.5 rounded-xl transition-all shadow-lg"
            >
              {loading ? "Reserving Slot with DMS..." : "Confirm Test Drive Booking"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
