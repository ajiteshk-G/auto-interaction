"use client";

import React, { useState } from "react";
import { CustomerProfile } from "@/types";
import { assessDamage, fileInsuranceClaim } from "@/lib/api";
import { X, Camera, ShieldAlert, CheckCircle2, Wrench, FileCheck2, AlertCircle } from "lucide-react";

interface DiagnosticsClaimsModalProps {
  isOpen: boolean;
  onClose: () => void;
  profile: CustomerProfile | null;
  onClaimFiled: () => void;
}

export function DiagnosticsClaimsModal({
  isOpen,
  onClose,
  profile,
  onClaimFiled
}: DiagnosticsClaimsModalProps) {
  const [damagePreset, setDamagePreset] = useState("bumper_foglamp");
  const [assessmentResult, setAssessmentResult] = useState<any>(null);
  const [evaluating, setEvaluating] = useState(false);
  const [filingClaim, setFilingClaim] = useState(false);
  const [claimResult, setClaimResult] = useState<any>(null);

  if (!isOpen) return null;

  const handleRunAssessment = async () => {
    setEvaluating(true);
    try {
      const res = await assessDamage({
        customer_id: profile?.customer_id || "CUST-AARAV-001",
        vehicle_vin: profile?.owned_vin || "MAH1THARROXX2026MUM01",
        mock_damage_type: damagePreset,
        video_feed_enabled: true
      });
      setAssessmentResult(res);
    } catch (e) {
      console.error("Assessment error:", e);
    } finally {
      setEvaluating(false);
    }
  };

  const handleFileClaim = async () => {
    if (!assessmentResult) return;
    setFilingClaim(true);
    try {
      const res = await fileInsuranceClaim({
        customer_id: profile?.customer_id || "CUST-AARAV-001",
        vin: profile?.owned_vin || "MAH1THARROXX2026MUM01",
        vehicle_model: profile?.owned_vehicle_name || "Mahindra Thar ROXX AX7L Diesel AT",
        incident_description: "Loose road debris impacted front bumper and fog lamp on highway.",
        detected_damages: assessmentResult.detected_parts,
        oem_part_number: assessmentResult.oem_part_number,
        workshop_name: assessmentResult.recommended_workshop
      });
      setClaimResult(res);
      onClaimFiled();
    } catch (e) {
      console.error("Claim error:", e);
    } finally {
      setFilingClaim(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-mahindra-card border border-mahindra-border rounded-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto shadow-2xl">
        {/* Header */}
        <div className="p-4 border-b border-mahindra-border flex items-center justify-between sticky top-0 bg-mahindra-card z-10">
          <div className="flex items-center gap-2">
            <ShieldAlert className="w-5 h-5 text-mahindra-red" />
            <div>
              <h2 className="text-sm font-bold text-white uppercase tracking-wider">AI Computer Vision Damage Assessment</h2>
              <p className="text-xs text-gray-400">Gemini Vision Automated Parts Requisition & Zero-Dep Claim</p>
            </div>
          </div>
          <button onClick={onClose} className="p-1 text-gray-400 hover:text-white rounded-lg">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 space-y-4 text-xs">
          {claimResult ? (
            <div className="text-center space-y-4 py-3">
              <div className="w-14 h-14 bg-emerald-500/20 border border-emerald-500 rounded-full flex items-center justify-center mx-auto text-emerald-400">
                <FileCheck2 className="w-8 h-8" />
              </div>
              <h3 className="text-lg font-bold text-white">Instant Insurance Claim Approved!</h3>
              <p className="text-gray-300">
                Claim ID: <span className="font-mono text-emerald-400 font-bold">{claimResult.claim_id}</span> with {claimResult.insurer_name}
              </p>

              <div className="bg-mahindra-dark p-4 rounded-xl text-left space-y-2 border border-mahindra-border">
                <div className="flex justify-between">
                  <span className="text-gray-400">Policy:</span>
                  <span className="text-white">{claimResult.policy_number} (Zero-Dep)</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Ordered OEM Part:</span>
                  <span className="text-amber-400 font-mono font-bold">{claimResult.oem_part_number}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Workshop & ETA:</span>
                  <span className="text-white">{claimResult.workshop_name} ({claimResult.parts_delivery_estimate})</span>
                </div>
                <div className="flex justify-between text-emerald-400 font-bold pt-1 border-t border-mahindra-border">
                  <span>Customer Out-of-Pocket:</span>
                  <span>₹0.00 (100% Covered)</span>
                </div>
              </div>

              <button
                onClick={onClose}
                className="w-full bg-mahindra-red hover:bg-red-600 text-white font-bold py-2.5 rounded-xl transition-all"
              >
                Close & Return
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              {/* Camera Simulation Viewport */}
              <div className="relative h-48 bg-black/80 rounded-xl overflow-hidden border border-mahindra-border flex flex-col items-center justify-center">
                <img
                  src="/assets/thar-roxx.png"
                  alt="Vehicle Bumper Live Feed"
                  className="absolute inset-0 w-full h-full object-cover opacity-40"
                />
                {/* HUD Overlay */}
                <div className="absolute inset-4 border border-dashed border-mahindra-red/60 rounded-lg flex flex-col justify-between p-2 pointer-events-none">
                  <div className="flex justify-between text-[10px] text-mahindra-red font-mono">
                    <span>[GEMINI_VISION_LIVE]</span>
                    <span>1080P_60FPS</span>
                  </div>
                  <div className="text-center text-xs font-semibold text-white/90">
                    Live Video Feed: Aiming at Front Bumper & Fog Lamp
                  </div>
                  <div className="text-right text-[10px] text-emerald-400 font-mono">
                    CHASSIS_ALIGNMENT: NORMAL
                  </div>
                </div>
              </div>

              {/* Scenario Preset Selector */}
              <div>
                <label className="block text-gray-300 font-semibold mb-1">Select Damage Scenario</label>
                <select
                  value={damagePreset}
                  onChange={(e) => setDamagePreset(e.target.value)}
                  className="w-full bg-mahindra-dark border border-mahindra-border rounded-xl px-3 py-2 text-white focus:outline-none focus:border-mahindra-red"
                >
                  <option value="bumper_foglamp">Front Lower Bumper Scratch & Cracked Fog Lamp Assembly (#TH-88301)</option>
                  <option value="windshield_chip">Front Windshield Rock Chip (#TH-44102)</option>
                  <option value="door_scratch">Rear Wheel Arch Cladding Scuff (#TH-22904)</option>
                </select>
              </div>

              <button
                onClick={handleRunAssessment}
                disabled={evaluating}
                className="w-full bg-mahindra-charcoal hover:bg-mahindra-border text-white border border-mahindra-border font-bold py-2.5 rounded-xl flex items-center justify-center gap-2 transition-all"
              >
                <Camera className="w-4 h-4 text-mahindra-red" />
                {evaluating ? "Analyzing Video Frames with Gemini Vision..." : "Run Multimodal AI Damage Scan"}
              </button>

              {/* Assessment Results Card */}
              {assessmentResult && (
                <div className="bg-mahindra-dark p-4 rounded-xl border border-mahindra-border space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-white flex items-center gap-1.5">
                      <Wrench className="w-4 h-4 text-mahindra-red" />
                      Damage Diagnosis & Parts Requisition
                    </span>
                    <span className="px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/40 text-[10px] font-bold">
                      {assessmentResult.severity}
                    </span>
                  </div>

                  <p className="text-gray-300 leading-relaxed bg-black/40 p-2.5 rounded-lg border border-mahindra-border/60">
                    {assessmentResult.gemini_vision_summary}
                  </p>

                  <div className="grid grid-cols-2 gap-2 text-[11px]">
                    <div className="bg-mahindra-card p-2.5 rounded-lg border border-mahindra-border">
                      <div className="text-gray-400">Required OEM Part:</div>
                      <div className="font-bold text-white">{assessmentResult.recommended_oem_part}</div>
                      <div className="font-mono text-mahindra-red text-[10px]">{assessmentResult.oem_part_number}</div>
                    </div>
                    <div className="bg-mahindra-card p-2.5 rounded-lg border border-mahindra-border">
                      <div className="text-gray-400">Parts Delivery ETA:</div>
                      <div className="font-bold text-emerald-400">{assessmentResult.parts_dispatch_eta}</div>
                      <div className="text-gray-400 text-[10px]">Bayview Workshop</div>
                    </div>
                  </div>

                  <button
                    onClick={handleFileClaim}
                    disabled={filingClaim}
                    className="w-full bg-mahindra-red hover:bg-red-600 disabled:opacity-50 text-white font-bold py-2.5 rounded-xl flex items-center justify-center gap-2 shadow-lg transition-all"
                  >
                    <CheckCircle2 className="w-4 h-4" />
                    {filingClaim ? "Submitting to ICICI Lombard..." : "Instant File Zero-Dep Insurance Claim (₹0 Cost)"}
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
