"use client";

import React from "react";
import { Mic, MicOff, Sparkles, Video, Volume2, ShieldCheck, Activity } from "lucide-react";

interface VoiceVisualizerProps {
  isRecording: boolean;
  rmsLevel: number;
  onToggleRecording: () => void;
  language: string;
}

export function VoiceVisualizer({
  isRecording,
  rmsLevel,
  onToggleRecording,
  language
}: VoiceVisualizerProps) {
  const scale = Math.max(1, Math.min(1.4, 1 + rmsLevel * 1.2));
  const glowOpacity = Math.min(1, 0.4 + rmsLevel * 1.5);

  return (
    <div className="flex flex-col items-center justify-center p-6 bg-gradient-to-b from-slate-900 via-slate-900 to-slate-950 rounded-3xl border border-slate-800 shadow-2xl relative overflow-hidden w-full text-white">
      {/* Background ambient lighting */}
      <div
        className="absolute w-72 h-72 rounded-full bg-red-600/20 filter blur-3xl pointer-events-none transition-opacity duration-300"
        style={{ opacity: isRecording ? glowOpacity : 0.2 }}
      />

      {/* Top Model & Audio Stream Badges */}
      <div className="flex items-center justify-between w-full z-10 mb-3 px-1">
        <div className="flex items-center gap-1.5 bg-slate-800/90 backdrop-blur-md px-3 py-1 rounded-full border border-slate-700 text-[10px] font-mono text-cyan-400">
          <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse"></span>
          <span>gemini-live-2.5-flash-native-audio</span>
        </div>

        <div className="flex items-center gap-1.5 bg-slate-800/90 backdrop-blur-md px-2.5 py-1 rounded-full border border-slate-700 text-[10px] font-bold text-red-400">
          <Activity className="w-3 h-3 text-red-400 animate-pulse" />
          <span>Kabir (Native Live Audio)</span>
        </div>
      </div>

      {/* Main Visualizer Stage with Live Audio Waveform Simulation */}
      <div className="relative my-3 flex flex-col items-center justify-center">
        {/* Live Audio Visualizer Box */}
        <div className="relative w-32 h-32 rounded-3xl bg-slate-800 border-2 border-red-500/60 flex items-center justify-center overflow-hidden shadow-2xl group">
          {/* Animated Glow */}
          <div
            className="absolute inset-0 bg-gradient-to-tr from-red-600/40 via-red-500/10 to-transparent transition-opacity duration-200"
            style={{ opacity: isRecording ? glowOpacity : 0.3 }}
          />

          {/* Kabir Persona Avatar Representation */}
          <div className="relative flex flex-col items-center justify-center space-y-1">
            <div className="w-16 h-16 rounded-full bg-gradient-to-tr from-red-700 to-red-500 flex items-center justify-center text-white font-black text-2xl shadow-lg border-2 border-white/40">
              K
            </div>
            <div className="text-[11px] font-black uppercase tracking-wider text-slate-200">
              Kabir • AI Specialist
            </div>
          </div>

          {/* Live Waveform Overlay when Speaking */}
          {isRecording && (
            <div className="absolute bottom-2 left-0 right-0 flex items-center justify-center gap-0.5 px-2">
              {[0.4, 0.9, 1.4, 0.7, 1.2, 0.5, 1.1, 0.6].map((multiplier, idx) => {
                const h = Math.max(3, Math.min(18, rmsLevel * 40 * multiplier));
                return (
                  <span
                    key={idx}
                    className="w-1 bg-red-400 rounded-full transition-all duration-75"
                    style={{ height: `${h}px` }}
                  />
                );
              })}
            </div>
          )}
        </div>

        {/* Floating Mic Trigger Button */}
        <button
          onClick={onToggleRecording}
          aria-label="Toggle Gemini Live Stream"
          className={`absolute -bottom-3 w-10 h-10 rounded-full flex items-center justify-center transition-all duration-200 focus:outline-none shadow-xl border-2 border-slate-900 ${
            isRecording
              ? "bg-red-600 text-white shadow-red-600/50 hover:scale-110"
              : "bg-slate-800 hover:bg-slate-700 text-slate-300 border-slate-700"
          }`}
          style={{ transform: isRecording ? `scale(${scale})` : "scale(1)" }}
        >
          {isRecording ? (
            <Mic className="w-4 h-4 text-white animate-pulse" />
          ) : (
            <MicOff className="w-4 h-4 text-slate-400" />
          )}
        </button>
      </div>

      {/* Status & Multilingual Stream Info */}
      <div className="text-center mt-3 z-10 space-y-1">
        <div className="text-xs font-black text-slate-200 flex items-center justify-center gap-1.5">
          <Sparkles className="w-3.5 h-3.5 text-red-500" />
          <span>
            {isRecording
              ? `Live Audio Active (${language} • Gemini 2.5)`
              : `Tap Mic to Start Gemini Live Stream`}
          </span>
        </div>
        <p className="text-[11px] text-slate-400 max-w-sm">
          Vertex AI Gemini 2.5 real-time bidirectional audio consultation with Kabir showroom persona
        </p>
      </div>
    </div>
  );
}
