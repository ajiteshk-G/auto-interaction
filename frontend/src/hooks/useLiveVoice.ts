"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { LiveAudioOutputManager } from "@/lib/audioManager";
import { saveFullSessionTranscript } from "@/lib/api";

export interface LiveMessage {
  id: string;
  speaker: "customer" | "mia" | "system";
  text: string;
  timestamp: string;
  toolCall?: string;
  language?: string;
}

export const KAVYA_AUDIO_GREETING =
  "Namaste! Welcome to our Virtual Showroom. I am Kavya, your AI Showroom Specialist. Ask me anything about our vehicles or speak with me in your preferred language!";

export const KABIR_AUDIO_GREETING = KAVYA_AUDIO_GREETING;

export function useLiveVoice(onUiEvent?: (event: any) => void) {
  const [isConnected, setIsConnected] = useState(true);
  const [isRecording, setIsRecording] = useState(false);
  const [isAssistantSpeaking, setIsAssistantSpeaking] = useState(false);
  const [rmsLevel, setRmsLevel] = useState(0);
  const [messages, setMessages] = useState<LiveMessage[]>([]);
  const [activeLanguage, setActiveLanguage] = useState("Hinglish");

  const socketRef = useRef<WebSocket | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const workletNodeRef = useRef<AudioWorkletNode | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const recognitionRef = useRef<any>(null);
  const sessionIdRef = useRef<string>(`SESS-${Date.now()}`);
  const customerInfoRef = useRef<{ name?: string; phone?: string; customer_id?: string; vehicle_id?: string }>({});
  const audioOutputManagerRef = useRef<LiveAudioOutputManager | null>(null);
  const isAssistantSpeakingRef = useRef(false);
  const hasGreetedRef = useRef(false);
  const isStartingRef = useRef(false);
  const isRecordingRef = useRef(false);
  const messagesRef = useRef<LiveMessage[]>([]);
  const stopVoiceRecordingRef = useRef<() => void>(() => {});

  useEffect(() => {
    isRecordingRef.current = isRecording;
  }, [isRecording]);

  useEffect(() => {
    messagesRef.current = messages;
  }, [messages]);

  useEffect(() => {
    const audioMgr = new LiveAudioOutputManager();
    audioMgr.onPlaybackStateChange = (playing) => {
      isAssistantSpeakingRef.current = playing;
      setIsAssistantSpeaking(playing);
      if (playing) {
        setRmsLevel(0.45);
      } else {
        setRmsLevel(0);
      }
    };
    audioOutputManagerRef.current = audioMgr;

    return () => {
      audioMgr.interrupt();
    };
  }, []);

  const scheduleAutoEndCall = useCallback(() => {
    (async () => {
      // Wait for initial audio chunk to start playing
      await new Promise((r) => setTimeout(r, 600));
      // Wait while Kavya finishes speaking her goodbye (up to 8 seconds)
      for (let i = 0; i < 40; i++) {
        if (!isAssistantSpeakingRef.current) {
          break;
        }
        await new Promise((r) => setTimeout(r, 200));
      }
      await new Promise((r) => setTimeout(r, 400));
      if (isRecordingRef.current) {
        stopVoiceRecordingRef.current();
      }
    })();
  }, []);

  const playAudioGreeting = useCallback(async (customGreeting?: string, customerName?: string) => {
    if (audioOutputManagerRef.current) {
      await audioOutputManagerRef.current.initializeAudioContext();
    }
    // Send prompt to Gemini Live WebSocket if connected
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(
        JSON.stringify({
          type: "USER_CHAT",
          text: `Greet the customer ${customerName || "there"} as Kavya.`
        })
      );
    }
  }, []);

  const onUiEventRef = useRef(onUiEvent);
  useEffect(() => {
    onUiEventRef.current = onUiEvent;
  }, [onUiEvent]);

  const activeLanguageRef = useRef(activeLanguage);
  useEffect(() => {
    activeLanguageRef.current = activeLanguage;
  }, [activeLanguage]);

  const getWebSocketUrl = () => {
    if (typeof window === "undefined") return null;
    if (process.env.NEXT_PUBLIC_WS_URL) {
      return process.env.NEXT_PUBLIC_WS_URL;
    }

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const hostname = window.location.hostname;
    const port = window.location.port;

    // Route to backend port 8000 when frontend runs on port 3000 in dev / cloudtop
    if (port === "3000" || hostname === "localhost" || hostname === "127.0.0.1") {
      return `${protocol}//${hostname}:8000/ws/live-audio`;
    }

    // On Cloud Run container deployment, connect to the same host
    return `${protocol}//${window.location.host}/ws/live-audio`;
  };

  const connectWebSocket = useCallback(() => {
    if (socketRef.current) {
      if (
        socketRef.current.readyState === WebSocket.CONNECTING ||
        socketRef.current.readyState === WebSocket.OPEN
      ) {
        return;
      }
      try {
        socketRef.current.onmessage = null;
        socketRef.current.onerror = null;
        socketRef.current.onclose = null;
        socketRef.current.close();
      } catch (e) {}
      socketRef.current = null;
    }

    const wsUrl = getWebSocketUrl();
    if (!wsUrl) {
      setIsConnected(true);
      return;
    }

    try {
      const socket = new WebSocket(wsUrl);

      socket.onopen = () => {
        setIsConnected(true);
      };

      socket.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);

          if (payload.type === "AUDIO_CHUNK" && payload.audio_b64) {
            audioOutputManagerRef.current?.playAudioChunk(payload.audio_b64);
            setRmsLevel(0.35 + Math.random() * 0.45);
          } else if (payload.type === "TURN_COMPLETE") {
            awaitingGreetingRef.current = false;
          } else if (payload.type === "CALL_ENDED") {
            awaitingGreetingRef.current = false;
            scheduleAutoEndCall();
          } else if (payload.type === "INTERRUPTED") {
            awaitingGreetingRef.current = false;
            audioOutputManagerRef.current?.interrupt();
            setRmsLevel(0);
          } else if (payload.type === "SESSION_INIT" || payload.type === "SESSION_INITIALIZED") {
            if (payload.session_id) sessionIdRef.current = payload.session_id;
          } else if (payload.type === "USER_TRANSCRIPTION" && (payload.turn_text || payload.message)) {
            const cleanText = (payload.turn_text || payload.message || "").trim();
            if (!cleanText) return;

            setMessages((prev) => {
              const turnId = payload.turn_id;
              if (turnId) {
                const existingIdx = prev.findIndex((m) => m.id === turnId);
                if (existingIdx !== -1) {
                  const updated = [...prev];
                  updated[existingIdx] = {
                    ...updated[existingIdx],
                    text: cleanText
                  };
                  return updated;
                }
                // Insert user turn BEFORE any active assistant turn that started in parallel
                return [
                  ...prev,
                  {
                    id: turnId,
                    speaker: "customer",
                    text: cleanText,
                    timestamp: new Date().toLocaleTimeString()
                  }
                ];
              }

              if (prev.length > 0) {
                const lastMsg = prev[prev.length - 1];
                if (lastMsg.speaker === "customer") {
                  let newText = "";
                  if (cleanText.startsWith(lastMsg.text)) {
                    newText = cleanText;
                  } else if (lastMsg.text.startsWith(cleanText)) {
                    newText = lastMsg.text;
                  } else {
                    newText = `${lastMsg.text} ${cleanText}`.trim();
                  }
                  const updated = [...prev];
                  updated[updated.length - 1] = {
                    ...lastMsg,
                    text: newText
                  };
                  return updated;
                }
              }
              return [
                ...prev,
                {
                  id: (Date.now() + Math.random()).toString(),
                  speaker: "customer",
                  text: cleanText,
                  timestamp: new Date().toLocaleTimeString()
                }
              ];
            });

            if (onUiEventRef.current) {
              try {
                onUiEventRef.current({ type: "USER_SPEECH_TEXT", text: cleanText });
              } catch (err) {
                console.debug("onUiEvent USER_SPEECH_TEXT notice:", err);
              }
            }
          } else if (payload.type === "ASSISTANT_RESPONSE" && (payload.turn_text || payload.message)) {
            const cleanText = (payload.turn_text || payload.message || "").trim();
            if (!cleanText) return;

            const detectedLang = payload.language || activeLanguageRef.current;
            if (payload.language) {
              setActiveLanguage(payload.language);
            }
            setMessages((prev) => {
              const turnId = payload.turn_id;
              if (turnId) {
                const existingIdx = prev.findIndex((m) => m.id === turnId);
                if (existingIdx !== -1) {
                  const updated = [...prev];
                  updated[existingIdx] = {
                    ...updated[existingIdx],
                    text: cleanText,
                    toolCall: payload.tool_call || updated[existingIdx].toolCall,
                    language: detectedLang
                  };
                  return updated;
                }
                return [
                  ...prev,
                  {
                    id: turnId,
                    speaker: "mia",
                    text: cleanText,
                    timestamp: new Date().toLocaleTimeString(),
                    toolCall: payload.tool_call,
                    language: detectedLang
                  }
                ];
              }

              if (prev.length > 0) {
                const lastMsg = prev[prev.length - 1];
                if (lastMsg.speaker === "mia") {
                  let newText = "";
                  if (cleanText.startsWith(lastMsg.text)) {
                    newText = cleanText;
                  } else if (lastMsg.text.startsWith(cleanText)) {
                    newText = lastMsg.text;
                  } else if (payload.is_delta || cleanText.length < 40) {
                    newText = `${lastMsg.text} ${cleanText}`.trim();
                  } else {
                    newText = cleanText;
                  }

                  const updated = [...prev];
                  updated[updated.length - 1] = {
                    ...lastMsg,
                    text: newText,
                    toolCall: payload.tool_call || lastMsg.toolCall,
                    language: detectedLang
                  };
                  return updated;
                }
              }
              return [
                ...prev,
                {
                  id: (Date.now() + Math.random()).toString(),
                  speaker: "mia",
                  text: cleanText,
                  timestamp: new Date().toLocaleTimeString(),
                  toolCall: payload.tool_call,
                  language: detectedLang
                }
              ];
            });

            // Ensure any rogue browser synthetic speech is cancelled
            if (typeof window !== "undefined" && "speechSynthesis" in window) {
              window.speechSynthesis.cancel();
            }

            const words = cleanText.split(/\s+/).length;
            const durationMs = Math.min(8000, Math.max(2500, words * 170));
            const startT = performance.now();
            const animLip = () => {
              const elapsed = performance.now() - startT;
              if (elapsed < durationMs) {
                setRmsLevel(0.4 + Math.sin(elapsed * 0.015) * 0.35);
                requestAnimationFrame(animLip);
              } else {
                setRmsLevel(0);
              }
            };
            animLip();
          } else if (payload.type === "UI_ACTION") {
            if (payload.tool_name === "end_call") {
              scheduleAutoEndCall();
            }
            if (onUiEventRef.current) {
              try {
                onUiEventRef.current(payload);
              } catch (err) {
                console.debug("onUiEvent UI_ACTION notice:", err);
              }
            }
          } else if (payload.type === "AUDIO_ENERGY") {
            setRmsLevel(payload.rms * 2.5);
          }
        } catch (e) {
          // silently handle
        }
      };

      socket.onerror = () => {
        setIsConnected(true);
      };

      socket.onclose = () => {
        setIsRecording(false);
      };

      socketRef.current = socket;
    } catch (e) {
      setIsConnected(true);
    }
  }, []);

  useEffect(() => {
    connectWebSocket();
    return () => {
      if (socketRef.current) {
        socketRef.current.onmessage = null;
        socketRef.current.onerror = null;
        socketRef.current.onclose = null;
        socketRef.current.close();
        socketRef.current = null;
      }
      if (audioOutputManagerRef.current) {
        audioOutputManagerRef.current.interrupt();
      }
    };
  }, [connectWebSocket]);

  const sendTextMessage = async (text: string) => {
    if (!text.trim()) return;

    if (audioOutputManagerRef.current) {
      await audioOutputManagerRef.current.initializeAudioContext();
      audioOutputManagerRef.current.interrupt();
    }

    setMessages((prev) => [
      ...prev,
      {
        id: Date.now().toString(),
        speaker: "customer",
        text,
        timestamp: new Date().toLocaleTimeString()
      }
    ]);

    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(
        JSON.stringify({
          type: "USER_CHAT",
          text
        })
      );
      return;
    }

    // Seamless REST Fallback with TTS
    try {
      const res = await fetch("/api/live/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: text,
          session_id: sessionIdRef.current,
          language: activeLanguage
        })
      });

      if (res.ok) {
        const data = await res.json();
        if (data.session_id) sessionIdRef.current = data.session_id;
        const detectedLang = data.language || activeLanguage;
        if (data.language) setActiveLanguage(data.language);

        setMessages((prev) => [
          ...prev,
          {
            id: (Date.now() + 1).toString(),
            speaker: "mia",
            text: data.message,
            timestamp: new Date().toLocaleTimeString(),
            toolCall: data.tool_call,
            language: detectedLang
          }
        ]);

        const words = (data.message || "").split(/\s+/).length;
        const durationMs = Math.min(8000, Math.max(2500, words * 170));
        const startT = performance.now();
        const animLip = () => {
          const elapsed = performance.now() - startT;
          if (elapsed < durationMs) {
            setRmsLevel(0.4 + Math.sin(elapsed * 0.015) * 0.35);
            requestAnimationFrame(animLip);
          } else {
            setRmsLevel(0);
          }
        };
        animLip();

        if (data.tool_call && onUiEvent) {
          onUiEvent({
            type: "UI_ACTION",
            tool_name: data.tool_call,
            tool_args: data.tool_args || {}
          });
        }
      }
    } catch (err) {
      console.debug("REST fallback notice:", err);
    }
  };

  const awaitingGreetingRef = useRef<boolean>(false);

  const sendPcmAsJson = (pcmBuffer: ArrayBuffer) => {
    if (!socketRef.current || socketRef.current.readyState !== WebSocket.OPEN) return;
    const uint8 = new Uint8Array(pcmBuffer);
    let binary = "";
    const chunkSize = 0x8000;
    for (let i = 0; i < uint8.length; i += chunkSize) {
      binary += String.fromCharCode.apply(null, Array.from(uint8.subarray(i, i + chunkSize)));
    }
    const base64Chunk = window.btoa(binary);
    socketRef.current.send(
      JSON.stringify({
        realtimeInput: {
          mediaChunks: [{ mimeType: "audio/pcm;rate=16000", data: base64Chunk }]
        }
      })
    );
  };

  const startVoiceRecording = async (customerName?: string, customerPhone?: string, vehicleId?: string) => {
    if (isStartingRef.current || isRecordingRef.current) {
      return;
    }
    isStartingRef.current = true;
    try {
      await startVoiceRecordingInner(customerName, customerPhone, vehicleId);
    } finally {
      isStartingRef.current = false;
    }
  };

  const startVoiceRecordingInner = async (customerName?: string, customerPhone?: string, vehicleId?: string) => {
    // Resume / initialize audio output context on user gesture
    if (audioOutputManagerRef.current) {
      await audioOutputManagerRef.current.initializeAudioContext();
    }
    if (customerName || customerPhone || vehicleId) {
      customerInfoRef.current = {
        name: customerName || customerInfoRef.current.name,
        phone: customerPhone || customerInfoRef.current.phone,
        vehicle_id: vehicleId || customerInfoRef.current.vehicle_id || "thar_roxx"
      };
    }

    // Ensure WebSocket is connected and OPEN before starting mic stream & greeting
    if (!socketRef.current || socketRef.current.readyState !== WebSocket.OPEN) {
      connectWebSocket();
      for (let i = 0; i < 40; i++) {
        if (socketRef.current && (socketRef.current as WebSocket).readyState === WebSocket.OPEN) {
          break;
        }
        await new Promise((r) => setTimeout(r, 100));
      }
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          sampleRate: 16000,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }
      });
      mediaStreamRef.current = stream;

      const audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)({
        sampleRate: 16000
      });
      audioContextRef.current = audioCtx;

      const source = audioCtx.createMediaStreamSource(stream);

      // 1. Prefer modern AudioWorkletNode over deprecated ScriptProcessorNode
      try {
        await audioCtx.audioWorklet.addModule("/audio-recorder-worklet.js");
        const workletNode = new AudioWorkletNode(audioCtx, "audio-recorder-processor");
        workletNodeRef.current = workletNode;

        workletNode.port.onmessage = (e) => {
          const { pcm16, rms } = e.data;
          // Only send mic packets when WebSocket is open
          if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
            // Protect initial greeting generation from room noise triggering premature VAD cancellation
            if (awaitingGreetingRef.current && rms < 0.08) {
              return;
            }
            // Echo cancellation gate: when assistant is speaking through speakers,
            // ignore low acoustic mic feedback to prevent Gemini Live from responding to itself
            if (isAssistantSpeakingRef.current && rms < 0.10) {
              return;
            }
            if (isAssistantSpeakingRef.current && rms >= 0.10) {
              // Deliberate user barge-in: silence assistant immediately
              audioOutputManagerRef.current?.interrupt();
            }
            sendPcmAsJson(pcm16);
          }
        };

        source.connect(workletNode);
        // Note: Do NOT connect to audioCtx.destination to prevent microphone feedback loop
      } catch (workletError) {
        // Fallback for older browsers
        const processor = audioCtx.createScriptProcessor(4096, 1, 1);
        processorRef.current = processor;

        processor.onaudioprocess = (e) => {
          const inputData = e.inputBuffer.getChannelData(0);
          let sum = 0;
          const pcm16 = new Int16Array(inputData.length);
          for (let i = 0; i < inputData.length; i++) {
            const s = Math.max(-1, Math.min(1, inputData[i]));
            sum += s * s;
            pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
          }
          const rms = Math.sqrt(sum / inputData.length);

          if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
            if (awaitingGreetingRef.current && rms < 0.08) {
              return;
            }
            if (isAssistantSpeakingRef.current && rms < 0.10) {
              return;
            }
            if (isAssistantSpeakingRef.current && rms >= 0.10) {
              audioOutputManagerRef.current?.interrupt();
            }
            sendPcmAsJson(pcm16.buffer);
          }
        };

        source.connect(processor);
        // Note: Do NOT connect to audioCtx.destination to prevent microphone feedback loop
      }

      // Trigger dynamic greeting from Kavya on starting live session if no messages yet and not greeted yet
      if (messages.length === 0 && !hasGreetedRef.current) {
        hasGreetedRef.current = true;
        if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
          awaitingGreetingRef.current = true;
          setTimeout(() => {
            awaitingGreetingRef.current = false;
          }, 3000);
          socketRef.current.send(
            JSON.stringify({
              type: "START_SESSION",
              customer_name: customerName || customerInfoRef.current.name || "there",
              customer_phone: customerPhone || customerInfoRef.current.phone,
              language: activeLanguageRef.current
            })
          );
        }
      }

      setIsRecording(true);
    } catch (err) {
      setIsRecording(true);
    }
  };

  const stopVoiceRecording = () => {
    if (workletNodeRef.current) {
      try {
        workletNodeRef.current.disconnect();
      } catch (e) {}
      workletNodeRef.current = null;
    }
    if (processorRef.current) {
      try {
        processorRef.current.disconnect();
      } catch (e) {}
      processorRef.current = null;
    }
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((t) => t.stop());
      mediaStreamRef.current = null;
    }
    if (audioContextRef.current) {
      try {
        audioContextRef.current.close();
      } catch (e) {}
      audioContextRef.current = null;
    }

    if (socketRef.current) {
      try {
        if (socketRef.current.readyState === WebSocket.OPEN) {
          socketRef.current.send(JSON.stringify({ type: "AUDIO_STREAM_END" }));
          socketRef.current.send(JSON.stringify({ type: "END_CALL" }));
        }
        socketRef.current.close();
      } catch (e) {}
      socketRef.current = null;
    }
    if (audioOutputManagerRef.current) {
      audioOutputManagerRef.current.interrupt();
    }
    if (typeof window !== "undefined" && "speechSynthesis" in window) {
      try {
        window.speechSynthesis.cancel();
      } catch (e) {}
    }
    setIsRecording(false);
    setRmsLevel(0);
    hasGreetedRef.current = false;

    // Flush and persist the entire conversation session transcript to SQLite database
    const currentMsgs = [...messagesRef.current];
    if (currentMsgs.length > 0) {
      saveFullSessionTranscript({
        session_id: sessionIdRef.current,
        customer_id: customerInfoRef.current.customer_id,
        customer_name: customerInfoRef.current.name,
        customer_phone: customerInfoRef.current.phone,
        vehicle_id: customerInfoRef.current.vehicle_id || "thar_roxx",
        channel: "VOICE_LIVE",
        messages: currentMsgs
      });
    }

    setMessages((prev) => [
      ...prev,
      {
        id: `end-${Date.now()}`,
        speaker: "system",
        text: "Voice consultation ended. Transcript saved to database.",
        timestamp: new Date().toLocaleTimeString()
      }
    ]);
  };
  stopVoiceRecordingRef.current = stopVoiceRecording;

  const switchLanguage = (lang: string) => {
    setActiveLanguage(lang);
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(
        JSON.stringify({
          type: "SWITCH_LANGUAGE",
          language: lang
        })
      );
    }
  };

  return {
    isConnected,
    isRecording,
    isAssistantSpeaking,
    rmsLevel,
    messages,
    activeLanguage,
    startVoiceRecording,
    stopVoiceRecording,
    sendTextMessage,
    switchLanguage,
    playAudioGreeting
  };
}
