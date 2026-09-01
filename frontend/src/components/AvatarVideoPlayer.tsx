"use client";

import React, { useEffect, useRef, useState } from "react";
import { Sparkles, Volume2 } from "lucide-react";

interface AvatarVideoPlayerProps {
  isRecording: boolean;
  rmsLevel: number;
  isSpeaking: boolean;
}

export function AvatarVideoPlayer({ isRecording, rmsLevel, isSpeaking }: AvatarVideoPlayerProps) {
  const [hasVideoStream, setHasVideoStream] = useState(false);
  const videoRef = useRef<HTMLVideoElement | null>(null);

  useEffect(() => {
    const video = document.getElementById("video_player") as HTMLVideoElement | null;
    if (!video) return;
    videoRef.current = video;

    const handlePlaying = () => setHasVideoStream(true);
    const handlePause = () => setHasVideoStream(false);
    const handleEnded = () => setHasVideoStream(false);

    video.addEventListener("playing", handlePlaying);
    video.addEventListener("pause", handlePause);
    video.addEventListener("ended", handleEnded);

    return () => {
      video.removeEventListener("playing", handlePlaying);
      video.removeEventListener("pause", handlePause);
      video.removeEventListener("ended", handleEnded);
    };
  }, []);

  return (
    <div className="relative w-full h-full flex items-center justify-center overflow-hidden rounded-2xl bg-[#020408]">
      {/* HTML5 Live Video Element (only rendered when video stream exists) */}
      <video
        id="video_player"
        autoPlay
        playsInline
        muted={false}
        className={`w-full h-full object-cover rounded-2xl z-10 transition-opacity duration-300 ${
          hasVideoStream ? "opacity-100 block" : "opacity-0 pointer-events-none hidden"
        }`}
      />

      {/* Standby / Active Audio Stage with Ambient Ripple */}
      <div
        className={`absolute inset-0 z-0 bg-gradient-to-b from-[#0F172A] to-[#060912] flex flex-col items-center justify-center p-4 transition-opacity duration-300 ${
          hasVideoStream ? "opacity-0 pointer-events-none" : "opacity-100"
        }`}
      >
        <div className="relative flex flex-col items-center justify-center">
          {/* Ambient Glow */}
          <div
            className={`absolute w-36 h-36 rounded-full bg-cyan-500/20 filter blur-2xl transition-all duration-300 ${
              isSpeaking ? "scale-125 opacity-100" : isRecording ? "scale-105 opacity-60" : "scale-90 opacity-20"
            }`}
          />

          {/* Avatar Portrait */}
          <div className="relative mb-3">
            <div
              className={`w-20 h-20 rounded-full overflow-hidden border-2 transition-all duration-300 p-0.5 bg-[#0B0F17] flex items-center justify-center ${
                isSpeaking
                  ? "border-cyan-400 shadow-[0_0_20px_rgba(0,229,255,0.6)] scale-105"
                  : isRecording
                  ? "border-emerald-400 shadow-[0_0_15px_rgba(16,185,129,0.4)]"
                  : "border-white/20"
              }`}
            >
              <img
                src="/avatars/jay.png"
                alt="Kabir Avatar"
                className="w-full h-full object-cover object-[50%_15%] rounded-full"
              />
            </div>
            {isSpeaking && (
              <span className="absolute -bottom-1 -right-1 bg-cyan-500 text-white p-1 rounded-full shadow-md">
                <Volume2 className="w-3 h-3 animate-pulse" />
              </span>
            )}
          </div>

          <div className="text-center space-y-1">
            <div className="flex items-center justify-center gap-1.5 text-xs font-bold text-white">
              <span>Kabir</span>
              <span className="text-[10px] text-cyan-400 font-mono font-medium">Mahindra AI Specialist</span>
            </div>
            <p className="text-[11px] text-slate-300 max-w-[220px]">
              {isRecording ? "Listening to you..." : "Click Start Live Session to talk with Kabir"}
            </p>
          </div>
        </div>
      </div>

      {/* Top-Left Live Audio HUD Badge */}
      <div className="absolute top-2.5 left-2.5 z-20 flex items-center gap-1.5 bg-black/80 backdrop-blur-md px-2.5 py-0.5 rounded-full border border-white/10 text-[9.5px] font-bold text-white shadow-md">
        <span
          className={`w-2 h-2 rounded-full ${
            isSpeaking
              ? "bg-cyan-400 shadow-[0_0_8px_#00e5ff] animate-ping"
              : isRecording
              ? "bg-emerald-400 shadow-[0_0_8px_#34d399] animate-pulse"
              : "bg-slate-400"
          }`}
        />
        <span>
          {isSpeaking ? "SPEAKING" : isRecording ? "LISTENING" : "STANDBY"}
        </span>
      </div>

      {/* Top-Right Modality Badge */}
      <div className="absolute top-2.5 right-2.5 z-20 flex items-center gap-1 bg-black/80 backdrop-blur-md px-2 py-0.5 rounded-full border border-white/10 text-[8.5px] font-mono text-cyan-300 shadow-md">
        <Sparkles className="w-2.5 h-2.5 text-cyan-400" />
        <span>GEMINI LIVE 2.5</span>
      </div>
    </div>
  );
}
