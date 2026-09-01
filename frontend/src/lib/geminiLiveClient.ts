"use client";

import { LiveAudioOutputManager } from "./audioManager";

export interface OutboundTurnEvent {
  speaker: string;
  role: "ai" | "customer";
  text: string;
  time: string;
}

export interface GeminiLiveClientOptions {
  leadRef: string;
  customerName: string;
  customerPhone: string;
  vehicleName: string;
  salesAdvisorName: string;
  brandId?: string;
  onTranscript: (turn: OutboundTurnEvent) => void;
  onCustomerSpeaking: (isSpeaking: boolean, level: number) => void;
  onAiSpeaking: (isSpeaking: boolean, level: number) => void;
  onBargeIn: () => void;
  onError?: (err: any) => void;
  onClose?: () => void;
}

export class GeminiLiveClient {
  private socket: WebSocket | null = null;
  private audioContext: AudioContext | null = null;
  private mediaStream: MediaStream | null = null;
  private processor: ScriptProcessorNode | null = null;
  private audioOutput: LiveAudioOutputManager;
  private options: GeminiLiveClientOptions;
  private isConnected: boolean = false;
  private isRecording: boolean = false;

  constructor(options: GeminiLiveClientOptions) {
    this.options = options;
    this.audioOutput = new LiveAudioOutputManager();
  }

  async start(): Promise<void> {
    // 1. Initialize browser AudioContext immediately on user gesture
    await this.audioOutput.initializeAudioContext();

    // 2. Determine WebSocket URL (direct to backend port 8000 on localhost)
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const hostname = window.location.hostname;
    const port = window.location.port;
    const isDev = port === "3000" || hostname === "localhost" || hostname === "127.0.0.1";
    const host = isDev ? `${hostname}:8000` : window.location.host;

    const queryParams = new URLSearchParams({
      mode: "outbound_call",
      role: "outbound_feedback",
      lead_ref: this.options.leadRef,
      customer_name: this.options.customerName,
      phone: this.options.customerPhone,
      vehicle_name: this.options.vehicleName,
      advisor_name: this.options.salesAdvisorName,
      ...(this.options.brandId ? { brand_id: this.options.brandId } : {})
    });

    const wsUrl = `${protocol}//${host}/ws/live-audio?${queryParams.toString()}`;
    console.log("Connecting GeminiLiveClient to:", wsUrl);

    try {
      this.socket = new WebSocket(wsUrl);

      this.socket.onopen = async () => {
        this.isConnected = true;
        console.log("Gemini Live WebSocket open. Starting microphone capture...");
        await this.startMicrophoneCapture();
      };

      this.socket.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);

          // Audio chunk from Gemini Live
          if (payload.type === "AUDIO_CHUNK" && payload.audio_b64) {
            this.audioOutput.playAudioChunk(payload.audio_b64, 24000);
            this.options.onAiSpeaking(true, 0.4 + Math.random() * 0.5);
          } else if (payload.type === "SESSION_INITIALIZED") {
            console.log("Gemini Live session initialized:", payload.session_id);
          } else if (payload.type === "USER_TRANSCRIPTION" && payload.message) {
            this.options.onTranscript({
              speaker: this.options.customerName,
              role: "customer",
              text: payload.message,
              time: new Date().toLocaleTimeString().slice(3, 8)
            });
          } else if (payload.type === "ASSISTANT_RESPONSE" && payload.message) {
            this.options.onTranscript({
              speaker: "Kavya AI",
              role: "ai",
              text: payload.message,
              time: new Date().toLocaleTimeString().slice(3, 8)
            });
            setTimeout(() => this.options.onAiSpeaking(false, 0), 1000);
          } else if (payload.type === "INTERRUPTED" || payload.serverContent?.interrupted) {
            this.audioOutput.interrupt();
            this.options.onBargeIn();
            this.options.onAiSpeaking(false, 0);
          }
        } catch (e) {
          console.warn("WebSocket message parse notice:", e);
        }
      };

      this.socket.onerror = (err) => {
        console.warn("Gemini Live WebSocket notice:", err);
        this.options.onError?.(err);
      };

      this.socket.onclose = () => {
        this.isConnected = false;
        this.stop();
        this.options.onClose?.();
      };
    } catch (err) {
      console.warn("Failed to connect Gemini Live WebSocket:", err);
      this.options.onError?.(err);
    }
  }

  private async startMicrophoneCapture(): Promise<void> {
    try {
      this.mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          sampleRate: 16000,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }
      });

      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      this.audioContext = new AudioCtx({ sampleRate: 16000 });
      if (this.audioContext.state === "suspended") {
        await this.audioContext.resume();
      }

      const source = this.audioContext.createMediaStreamSource(this.mediaStream);
      this.processor = this.audioContext.createScriptProcessor(4096, 1, 1);

      this.processor.onaudioprocess = (e) => {
        if (!this.isRecording || !this.isConnected) return;

        const inputData = e.inputBuffer.getChannelData(0);

        // Compute RMS level
        let sum = 0;
        for (let i = 0; i < inputData.length; i++) {
          sum += inputData[i] * inputData[i];
        }
        const rms = Math.sqrt(sum / inputData.length);

        if (rms > 0.015) {
          this.options.onCustomerSpeaking(true, Math.min(1.0, rms * 8));
        } else {
          this.options.onCustomerSpeaking(false, 0);
        }

        // Convert Float32Array to 16-bit PCM Linear
        const pcm16 = new Int16Array(inputData.length);
        for (let i = 0; i < inputData.length; i++) {
          const s = Math.max(-1, Math.min(1, inputData[i]));
          pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
        }

        // Base64 encode PCM bytes
        const uint8 = new Uint8Array(pcm16.buffer);
        let binary = "";
        for (let i = 0; i < uint8.length; i++) {
          binary += String.fromCharCode(uint8[i]);
        }
        const base64Chunk = window.btoa(binary);

        // Stream real-time media chunk to Gemini Live WebSocket
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
          this.socket.send(
            JSON.stringify({
              realtimeInput: {
                mediaChunks: [
                  {
                    mimeType: "audio/pcm;rate=16000",
                    data: base64Chunk
                  }
                ]
              }
            })
          );
        }
      };

      source.connect(this.processor);
      this.processor.connect(this.audioContext.destination);
      this.isRecording = true;
      console.log("Microphone streaming active at 16kHz PCM");
    } catch (err) {
      console.warn("Microphone access notice (User can type or speak):", err);
    }
  }

  sendTextMessage(text: string): void {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(
        JSON.stringify({
          type: "USER_CHAT",
          text: text
        })
      );
    }
  }

  stop(): void {
    this.isRecording = false;
    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach((t) => t.stop());
      this.mediaStream = null;
    }
    if (this.processor) {
      try {
        this.processor.disconnect();
      } catch (e) {}
      this.processor = null;
    }
    if (this.audioContext && this.audioContext.state !== "closed") {
      try {
        this.audioContext.close();
      } catch (e) {}
      this.audioContext = null;
    }
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      try {
        this.socket.close();
      } catch (e) {}
      this.socket = null;
    }
    this.audioOutput.interrupt();
  }
}
