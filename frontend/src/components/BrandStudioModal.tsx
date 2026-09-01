"use client";

import React, { useState, useEffect, useRef } from "react";
import { BrandSummary, BrandCatalog, VehicleItem, VehicleVariant } from "@/types";
import {
  fetchBrands,
  fetchActiveBrand,
  setActiveBrand,
  onboardBrand,
  uploadVehicleImage,
  uploadBrandLogo,
  updateVehicleDetails,
  addCustomVehicle,
  deleteCustomVehicle
} from "@/lib/api";
import {
  X,
  Plus,
  Trash2,
  Upload,
  CheckCircle2,
  Sparkles,
  Layers,
  Car,
  Globe,
  Palette,
  Loader2,
  AlertCircle,
  ExternalLink,
  ShieldCheck,
  RefreshCw,
  Image as ImageIcon
} from "lucide-react";

interface BrandStudioModalProps {
  isOpen: boolean;
  onClose: () => void;
  onBrandChanged: (brand: BrandCatalog) => void;
  activeBrand?: BrandCatalog | null;
}

export function BrandStudioModal({
  isOpen,
  onClose,
  onBrandChanged,
  activeBrand: externalActiveBrand
}: BrandStudioModalProps) {
  const [activeTab, setActiveTab] = useState<"switch" | "onboard" | "editor">("switch");
  const [brands, setBrands] = useState<BrandSummary[]>([]);
  const [activeBrand, setActiveBrandState] = useState<BrandCatalog | null>(externalActiveBrand || null);
  const [isLoading, setIsLoading] = useState(false);
  const [statusMessage, setStatusMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // Onboard form state
  const [newBrandName, setNewBrandName] = useState("");
  const [newUrls, setNewUrls] = useState<string[]>([""]);
  const [isOnboarding, setIsOnboarding] = useState(false);

  // File upload refs
  const fileInputRef = useRef<HTMLInputElement>(null);
  const logoInputRef = useRef<HTMLInputElement>(null);
  const [uploadingVehicleId, setUploadingVehicleId] = useState<string | null>(null);

  // Load brands on open
  useEffect(() => {
    if (isOpen) {
      if (externalActiveBrand) {
        setActiveBrandState(externalActiveBrand);
      }
      loadData();
    }
  }, [isOpen, externalActiveBrand]);

  const loadData = async () => {
    setIsLoading(true);
    try {
      const [allBrands, currentActive] = await Promise.all([
        fetchBrands(),
        fetchActiveBrand()
      ]);
      setBrands(allBrands);
      setActiveBrandState(currentActive);
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  };

  if (!isOpen) return null;

  const handleSelectBrand = async (brandId: string) => {
    setIsLoading(true);
    setStatusMessage(null);
    try {
      const updated = await setActiveBrand(brandId);
      if (updated) {
        setActiveBrandState(updated);
        onBrandChanged(updated);
        setStatusMessage({ type: "success", text: `Active brand switched to ${updated.name}!` });
        const allBrands = await fetchBrands();
        setBrands(allBrands);
      }
    } catch (e: any) {
      setStatusMessage({ type: "error", text: e.message || "Failed to switch brand" });
    } finally {
      setIsLoading(false);
    }
  };

  const handleAddUrlField = () => {
    setNewUrls((prev) => [...prev, ""]);
  };

  const handleUrlChange = (index: number, val: string) => {
    setNewUrls((prev) => {
      const copy = [...prev];
      copy[index] = val;
      return copy;
    });
  };

  const handleRemoveUrlField = (index: number) => {
    if (newUrls.length > 1) {
      setNewUrls((prev) => prev.filter((_, i) => i !== index));
    }
  };

  const handleOnboardSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const validUrls = newUrls.map((u) => u.trim()).filter(Boolean);
    if (!newBrandName.trim()) {
      setStatusMessage({ type: "error", text: "Please provide a brand name" });
      return;
    }
    if (validUrls.length === 0) {
      setStatusMessage({ type: "error", text: "Please provide at least one valid URL" });
      return;
    }

    setIsOnboarding(true);
    setStatusMessage(null);
    try {
      const onboarded = await onboardBrand(newBrandName.trim(), validUrls);
      if (onboarded) {
        setActiveBrandState(onboarded);
        onBrandChanged(onboarded);
        setStatusMessage({
          type: "success",
          text: `Successfully extracted ${onboarded.vehicles.length} vehicles for ${onboarded.name}!`
        });
        const allBrands = await fetchBrands();
        setBrands(allBrands);
        setActiveTab("editor");
      }
    } catch (e: any) {
      setStatusMessage({
        type: "error",
        text: `Extraction failed: ${e.message || "Could not crawl URLs"}`
      });
    } finally {
      setIsOnboarding(false);
    }
  };

  const triggerVehicleImageUpload = (vehicleId: string) => {
    setUploadingVehicleId(vehicleId);
    if (fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  const handleVehicleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !uploadingVehicleId || !activeBrand) return;

    setIsLoading(true);
    setStatusMessage(null);
    try {
      const updatedVehicle = await uploadVehicleImage(activeBrand.id, uploadingVehicleId, file);
      if (updatedVehicle) {
        const refreshedBrand = await fetchActiveBrand();
        if (refreshedBrand) {
          setActiveBrandState(refreshedBrand);
          onBrandChanged(refreshedBrand);
        }
        setStatusMessage({
          type: "success",
          text: `Image updated for ${updatedVehicle.name}! Now set as Source of Truth.`
        });
      }
    } catch (err: any) {
      setStatusMessage({ type: "error", text: "Failed to upload vehicle image." });
    } finally {
      setIsLoading(false);
      setUploadingVehicleId(null);
      if (e.target) e.target.value = "";
    }
  };

  const handleLogoFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !activeBrand) return;

    setIsLoading(true);
    setStatusMessage(null);
    try {
      const updated = await uploadBrandLogo(activeBrand.id, file);
      if (updated) {
        setActiveBrandState(updated);
        onBrandChanged(updated);
        setStatusMessage({ type: "success", text: "Brand logo updated successfully!" });
      }
    } catch (err) {
      setStatusMessage({ type: "error", text: "Failed to upload brand logo." });
    } finally {
      setIsLoading(false);
      if (e.target) e.target.value = "";
    }
  };

  const handleDeleteVehicle = async (vehicleId: string) => {
    if (!activeBrand) return;
    if (!confirm("Are you sure you want to remove this vehicle?")) return;
    const ok = await deleteCustomVehicle(activeBrand.id, vehicleId);
    if (ok) {
      const refreshedBrand = await fetchActiveBrand();
      if (refreshedBrand) {
        setActiveBrandState(refreshedBrand);
        onBrandChanged(refreshedBrand);
      }
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/70 backdrop-blur-md animate-in fade-in">
      <div className="bg-white rounded-3xl shadow-2xl border border-slate-200 w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden">
        {/* Modal Header */}
        <div className="p-6 border-b border-slate-100 flex items-center justify-between bg-gradient-to-r from-slate-50 to-white">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-indigo-50 border border-indigo-200 flex items-center justify-center text-indigo-600 shadow-xs">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-xl font-black text-slate-900 flex items-center gap-2">
                Brand Studio & Catalog Engine
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 font-bold border border-emerald-200">
                  Generic Mode
                </span>
              </h2>
              <p className="text-xs text-slate-500">
                Switch brands on the fly, onboard new brands via multiple URLs, and upload custom images as Source of Truth.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-full bg-slate-100 hover:bg-slate-200 text-slate-500 hover:text-slate-900 flex items-center justify-center transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="flex items-center gap-2 px-6 pt-4 border-b border-slate-100 bg-slate-50/50">
          <button
            onClick={() => { setActiveTab("switch"); setStatusMessage(null); }}
            className={`px-4 py-2.5 rounded-t-xl text-xs font-bold transition-all border-b-2 flex items-center gap-2 ${
              activeTab === "switch"
                ? "border-indigo-600 text-indigo-600 bg-white shadow-xs"
                : "border-transparent text-slate-600 hover:text-slate-900"
            }`}
          >
            <Layers className="w-4 h-4" />
            1. Switch Brand ({brands.length})
          </button>
          <button
            onClick={() => { setActiveTab("onboard"); setStatusMessage(null); }}
            className={`px-4 py-2.5 rounded-t-xl text-xs font-bold transition-all border-b-2 flex items-center gap-2 ${
              activeTab === "onboard"
                ? "border-indigo-600 text-indigo-600 bg-white shadow-xs"
                : "border-transparent text-slate-600 hover:text-slate-900"
            }`}
          >
            <Globe className="w-4 h-4" />
            2. Onboard New Brand (URLs)
          </button>
          <button
            onClick={() => { setActiveTab("editor"); setStatusMessage(null); }}
            className={`px-4 py-2.5 rounded-t-xl text-xs font-bold transition-all border-b-2 flex items-center gap-2 ${
              activeTab === "editor"
                ? "border-indigo-600 text-indigo-600 bg-white shadow-xs"
                : "border-transparent text-slate-600 hover:text-slate-900"
            }`}
          >
            <ShieldCheck className="w-4 h-4" />
            3. Source of Truth Editor ({activeBrand?.vehicles?.length || 0} Vehicles)
          </button>
        </div>

        {/* Alert Notifications */}
        {statusMessage && (
          <div className={`mx-6 mt-4 p-3 rounded-xl text-xs font-medium flex items-center gap-2 ${
            statusMessage.type === "success"
              ? "bg-emerald-50 text-emerald-800 border border-emerald-200"
              : "bg-red-50 text-red-800 border border-red-200"
          }`}>
            {statusMessage.type === "success" ? <CheckCircle2 className="w-4 h-4 shrink-0" /> : <AlertCircle className="w-4 h-4 shrink-0" />}
            <span>{statusMessage.text}</span>
          </div>
        )}

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto flex-1">
          {/* TAB 1: SWITCH BRAND */}
          {activeTab === "switch" && (
            <div className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
                {brands.map((b) => {
                  const isSelected = activeBrand?.id === b.id;
                  return (
                    <div
                      key={b.id}
                      onClick={() => handleSelectBrand(b.id)}
                      className={`p-4 rounded-2xl border-2 cursor-pointer transition-all flex flex-col justify-between hover:shadow-md ${
                        isSelected
                          ? "border-indigo-600 bg-indigo-50/40 shadow-sm"
                          : "border-slate-200 bg-white hover:border-slate-300"
                      }`}
                    >
                      <div>
                        <div className="flex items-center justify-between gap-2 mb-2">
                          <span
                            className="w-3 h-3 rounded-full shrink-0"
                            style={{ backgroundColor: b.primary_color }}
                          />
                          {isSelected && (
                            <span className="text-[10px] bg-indigo-600 text-white font-bold px-2 py-0.5 rounded-full">
                              ACTIVE
                            </span>
                          )}
                        </div>
                        <h4 className="text-sm font-black text-slate-900">{b.name}</h4>
                        <p className="text-xs text-slate-500 line-clamp-2 mt-1">{b.tagline}</p>
                      </div>
                      <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-[11px] font-bold text-slate-600">
                        <span>{b.vehicle_count} Models</span>
                        <span className="text-indigo-600 hover:underline">
                          {isSelected ? "Selected ✓" : "Activate →"}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>

              <div className="pt-4 border-t border-slate-100 flex items-center justify-between">
                <p className="text-xs text-slate-500">
                  Want to add another brand? Click the "Onboard New Brand" tab above to scrape from official URLs.
                </p>
                <button
                  onClick={() => setActiveTab("onboard")}
                  className="px-4 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-white text-xs font-bold transition-all flex items-center gap-1.5 shadow-xs"
                >
                  <Plus className="w-3.5 h-3.5" />
                  Onboard Brand via URLs
                </button>
              </div>
            </div>
          )}

          {/* TAB 2: ONBOARD NEW BRAND VIA MULTIPLE URLS */}
          {activeTab === "onboard" && (
            <form onSubmit={handleOnboardSubmit} className="space-y-5">
              <div className="bg-slate-50 p-4 rounded-2xl border border-slate-200 text-xs text-slate-600 space-y-1">
                <p className="font-bold text-slate-900 flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
                  Automated Multi-URL Ingestion & Extraction Engine
                </p>
                <p>
                  Provide the brand name and one or more official URLs (e.g. homepage, SUV lineup, EV showcase, or model spec pages).
                  Gemini will crawl the pages, extract logo assets, vehicle photos, powertrains, and prices, and build the catalog automatically.
                </p>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1.5">
                  Brand Name *
                </label>
                <input
                  type="text"
                  placeholder="e.g. BMW, Tata Motors, Rivian, Porsche, Kia"
                  value={newBrandName}
                  onChange={(e) => setNewBrandName(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 text-xs text-slate-900 focus:outline-none focus:border-indigo-600 focus:ring-1 focus:ring-indigo-600 shadow-xs"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1.5">
                  Brand URLs to Scrape (Multiple URLs Supported) *
                </label>
                <div className="space-y-2">
                  {newUrls.map((url, idx) => (
                    <div key={idx} className="flex items-center gap-2">
                      <input
                        type="url"
                        placeholder="https://brand.com/vehicles or https://brand.com/suvs"
                        value={url}
                        onChange={(e) => handleUrlChange(idx, e.target.value)}
                        className="flex-1 px-3.5 py-2 rounded-xl border border-slate-300 text-xs text-slate-900 focus:outline-none focus:border-indigo-600 shadow-xs"
                        required={idx === 0}
                      />
                      {newUrls.length > 1 && (
                        <button
                          type="button"
                          onClick={() => handleRemoveUrlField(idx)}
                          className="p-2 rounded-xl text-red-500 hover:bg-red-50 transition-colors"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                  ))}
                </div>
                <button
                  type="button"
                  onClick={handleAddUrlField}
                  className="mt-2 text-xs text-indigo-600 font-bold hover:underline flex items-center gap-1"
                >
                  <Plus className="w-3.5 h-3.5" />
                  + Add another URL
                </button>
              </div>

              <div className="pt-4 border-t border-slate-100 flex items-center justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setActiveTab("switch")}
                  className="px-4 py-2.5 rounded-xl border border-slate-300 text-slate-700 text-xs font-bold hover:bg-slate-50 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isOnboarding}
                  className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold transition-all shadow-md flex items-center gap-2 disabled:opacity-50"
                >
                  {isOnboarding ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Crawling URLs & Extracting with AI...
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-4 h-4" />
                      Analyze & Extract Brand Catalog
                    </>
                  )}
                </button>
              </div>
            </form>
          )}

          {/* TAB 3: SOURCE OF TRUTH CATALOG EDITOR & IMAGE UPLOAD */}
          {activeTab === "editor" && activeBrand && (
            <div className="space-y-6">
              {/* Brand Meta Header */}
              <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 flex flex-wrap items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                  <div
                    className="w-12 h-12 rounded-2xl flex items-center justify-center border font-black text-lg shadow-xs"
                    style={{
                      backgroundColor: `${activeBrand.primary_color}15`,
                      borderColor: activeBrand.primary_color,
                      color: activeBrand.primary_color
                    }}
                  >
                    {activeBrand.name.slice(0, 2).toUpperCase()}
                  </div>
                  <div>
                    <h3 className="text-base font-black text-slate-900">{activeBrand.name}</h3>
                    <p className="text-xs text-slate-500">{activeBrand.tagline}</p>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => logoInputRef.current?.click()}
                    className="px-3 py-1.5 rounded-xl bg-white border border-slate-200 text-xs font-bold text-slate-700 hover:bg-slate-50 transition-colors shadow-xs flex items-center gap-1.5"
                  >
                    <Upload className="w-3.5 h-3.5" />
                    Upload Brand Logo
                  </button>
                  <input
                    ref={logoInputRef}
                    type="file"
                    accept="image/*"
                    className="hidden"
                    onChange={handleLogoFileChange}
                  />
                </div>
              </div>

              {/* Source of Truth Disclaimer */}
              <div className="p-3.5 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-900 text-xs flex items-start gap-2.5">
                <ShieldCheck className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                <div>
                  <span className="font-bold">Source of Truth Priority:</span> If any vehicle image from the web is incorrect or missing, upload your verified photo directly below. User-uploaded images permanently override web-scraped images and become the official source of truth for the entire application.
                </div>
              </div>

              {/* Hidden file input for vehicle uploads */}
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                className="hidden"
                onChange={handleVehicleFileChange}
              />

              {/* Vehicle Cards Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {activeBrand.vehicles.map((v) => (
                  <div
                    key={v.id}
                    className="p-4 rounded-2xl border border-slate-200 bg-white hover:border-slate-300 transition-all flex flex-col justify-between shadow-xs"
                  >
                    <div>
                      {/* Vehicle Image with Upload Overlay */}
                      <div className="relative w-full h-40 rounded-xl bg-slate-100 overflow-hidden mb-3 border border-slate-200 group">
                        {v.hero_image ? (
                          <img
                            src={v.hero_image}
                            alt={v.name}
                            className="w-full h-full object-contain p-2"
                          />
                        ) : (
                          <div className="w-full h-full flex flex-col items-center justify-center text-slate-400">
                            <Car className="w-8 h-8 mb-1" />
                            <span className="text-[10px]">No image uploaded</span>
                          </div>
                        )}

                        {/* Source of Truth Badge */}
                        <div className="absolute top-2 left-2">
                          {v.is_custom_source_of_truth ? (
                            <span className="px-2 py-0.5 rounded-full bg-emerald-600 text-white text-[10px] font-bold shadow-xs flex items-center gap-1">
                              <CheckCircle2 className="w-3 h-3" />
                              Source of Truth
                            </span>
                          ) : (
                            <span className="px-2 py-0.5 rounded-full bg-slate-800/80 text-white text-[10px] font-medium backdrop-blur-xs">
                              Scraped from Web
                            </span>
                          )}
                        </div>

                        {/* Hover upload button */}
                        <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
                          <button
                            type="button"
                            onClick={() => triggerVehicleImageUpload(v.id)}
                            className="px-3 py-1.5 rounded-xl bg-white text-slate-900 text-xs font-bold shadow-lg flex items-center gap-1 hover:bg-slate-100 transition-colors"
                          >
                            <Upload className="w-3.5 h-3.5 text-indigo-600" />
                            Upload Image (Source of Truth)
                          </button>
                        </div>
                      </div>

                      {/* Vehicle Details */}
                      <div className="space-y-1">
                        <div className="flex items-center justify-between gap-2">
                          <h4 className="text-sm font-black text-slate-900">{v.name}</h4>
                          <button
                            type="button"
                            onClick={() => handleDeleteVehicle(v.id)}
                            className="p-1 rounded-lg text-slate-400 hover:text-red-500 hover:bg-red-50 transition-colors"
                            title="Remove Vehicle"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                        <p className="text-xs text-slate-500">{v.tagline}</p>
                        <div className="pt-2 flex flex-wrap items-center gap-1.5 text-[10px]">
                          <span className="px-2 py-0.5 rounded-md bg-slate-100 text-slate-700 font-bold">
                            {v.category}
                          </span>
                          <span className="px-2 py-0.5 rounded-md bg-emerald-50 text-emerald-700 font-bold">
                            {v.price_range}
                          </span>
                          {v.range_or_mileage && (
                            <span className="px-2 py-0.5 rounded-md bg-blue-50 text-blue-700 font-medium">
                              {v.range_or_mileage}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>

                    <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between">
                      <button
                        type="button"
                        onClick={() => triggerVehicleImageUpload(v.id)}
                        className="text-xs font-bold text-indigo-600 hover:underline flex items-center gap-1"
                      >
                        <ImageIcon className="w-3.5 h-3.5" />
                        Replace Image
                      </button>
                      <span className="text-[10px] text-slate-400 font-mono">
                        ID: {v.id}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="p-4 border-t border-slate-100 flex items-center justify-between bg-slate-50/50">
          <div className="text-xs text-slate-500">
            Active: <span className="font-bold text-slate-900">{activeBrand?.name}</span>
          </div>
          <button
            onClick={onClose}
            className="px-5 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-white text-xs font-bold transition-all shadow-xs"
          >
            Done & Return to Showroom
          </button>
        </div>
      </div>
    </div>
  );
}
