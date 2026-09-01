"use client";

import React from "react";
import Link from "next/link";
import { AdminBookingsTable } from "@/components/AdminBookingsTable";
import { ShieldCheck, ArrowLeft } from "lucide-react";

export default function AdminPage() {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col font-sans selection:bg-red-600 selection:text-white">
      {/* Top Admin Header */}
      <header className="sticky top-0 z-40 bg-white/95 backdrop-blur-md border-b border-slate-200 px-4 lg:px-8 py-3.5 flex items-center justify-between shadow-xs">
        <div className="flex items-center gap-3">
          <Link
            href="/"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-100 hover:bg-slate-200 border border-slate-200 text-slate-700 hover:text-slate-900 text-xs font-bold transition-all group cursor-pointer"
          >
            <ArrowLeft className="w-3.5 h-3.5 group-hover:-translate-x-0.5 transition-transform text-slate-600" />
            <span>Virtual Showroom</span>
          </Link>

          <div className="h-5 w-[1px] bg-slate-200 mx-1 hidden sm:block"></div>

          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-red-600 to-amber-600 flex items-center justify-center text-white shadow-md shadow-red-600/20">
              <ShieldCheck className="w-4 h-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-sm font-black tracking-tight text-slate-900 uppercase">
                  Omnichannel Multi-Brand Admin Portal
                </h1>
                <span className="px-1.5 py-0.5 rounded bg-red-100 text-red-700 font-mono text-[9.5px] font-bold border border-red-200">
                  Live Operations
                </span>
              </div>
              <p className="text-[11px] text-slate-500">
                Booked Test Rides • Dual Transcripts (Pre-Sales &amp; Test Ride) • Multi-Tenant Brand Registry
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-[11px] font-mono text-emerald-700 bg-emerald-50 border border-emerald-200 px-3 py-1 rounded-full flex items-center gap-1.5 font-bold shadow-xs">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            Database Connected
          </span>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-[1600px] w-full mx-auto p-4 lg:p-8 space-y-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-2">
          <div>
            <h2 className="text-xl font-black text-slate-900 tracking-tight flex items-center gap-2">
              <span>Test Ride Bookings &amp; Transcripts Registry</span>
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Real-time audit log of all reserved customer slots across Maharashtra, Delhi, Bangalore, and Chennai showrooms.
            </p>
          </div>
        </div>

        <AdminBookingsTable />
      </main>
    </div>
  );
}
