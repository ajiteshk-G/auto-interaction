export class LiveAudioOutputManager {
  private audioContext: AudioContext | null = null;
  private initialized = false;
  private nextPlayTime = 0;
  private activeSources: AudioBufferSourceNode[] = [];
  public onPlaybackStateChange?: (isPlaying: boolean) => void;

  async initializeAudioContext(): Promise<void> {
    try {
      if (!this.audioContext || this.audioContext.state === "closed") {
        const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
        this.audioContext = new AudioCtx({ sampleRate: 24000 });
      }
      if (this.audioContext.state === "suspended") {
        await this.audioContext.resume();
      }
      this.nextPlayTime = this.audioContext.currentTime;
      this.initialized = true;
    } catch (e) {
      console.error("[LiveAudioOutputManager] Failed to init AudioContext:", e);
    }
  }

  async playAudioChunk(base64AudioChunk: string, sampleRate = 24000): Promise<void> {
    if (!base64AudioChunk || base64AudioChunk.length <= 8) return;

    try {
      if (!this.audioContext || this.audioContext.state === "closed") {
        await this.initializeAudioContext();
      }
      if (this.audioContext && this.audioContext.state === "suspended") {
        await this.audioContext.resume();
      }
      if (!this.audioContext) return;

      const arrayBuffer = LiveAudioOutputManager.base64ToArrayBuffer(base64AudioChunk);
      const float32Data = LiveAudioOutputManager.convertPCM16LEToFloat32(arrayBuffer);

      if (float32Data.length === 0) return;

      const audioBuffer = this.audioContext.createBuffer(1, float32Data.length, sampleRate);
      audioBuffer.getChannelData(0).set(float32Data);

      const source = this.audioContext.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(this.audioContext.destination);

      const now = this.audioContext.currentTime;
      // If queue fell behind current time (underrun) or no audio sources are actively scheduled, start fresh at now.
      // Crucial: Never reset nextPlayTime to now while chunks are actively playing/queued, as Gemini streams faster than real time.
      if (this.activeSources.length === 0 || this.nextPlayTime < now || this.nextPlayTime > now + 30.0) {
        this.nextPlayTime = now;
      }
      const startTime = this.nextPlayTime;
      source.start(startTime);
      this.nextPlayTime = startTime + audioBuffer.duration;

      this.activeSources.push(source);
      if (this.onPlaybackStateChange) {
        this.onPlaybackStateChange(true);
      }

      source.onended = () => {
        const idx = this.activeSources.indexOf(source);
        if (idx > -1) this.activeSources.splice(idx, 1);
        if (this.activeSources.length === 0 && this.onPlaybackStateChange) {
          this.onPlaybackStateChange(false);
        }
      };
    } catch (error) {
      console.error("[LiveAudioOutputManager] Error playing chunk:", error);
    }
  }

  interrupt(): void {
    try {
      for (const src of this.activeSources) {
        try {
          src.stop();
          src.disconnect();
        } catch (e) {}
      }
      this.activeSources = [];
      if (this.audioContext) {
        this.nextPlayTime = this.audioContext.currentTime;
      }
      if (this.onPlaybackStateChange) {
        this.onPlaybackStateChange(false);
      }
    } catch (e) {
      console.warn("[LiveAudioOutputManager] Error interrupting audio:", e);
    }
  }

  static base64ToArrayBuffer(base64: string): ArrayBuffer {
    const binaryString = window.atob(base64);
    const len = binaryString.length;
    const bytes = new Uint8Array(len);
    for (let i = 0; i < len; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }
    return bytes.buffer;
  }

  static convertPCM16LEToFloat32(pcmData: ArrayBuffer): Float32Array {
    if (!pcmData || pcmData.byteLength < 2) {
      return new Float32Array(0);
    }
    const safeBytes = pcmData.byteLength - (pcmData.byteLength % 2);
    const numSamples = safeBytes / 2;
    const inputArray = new Int16Array(pcmData, 0, numSamples);
    const float32Array = new Float32Array(numSamples);
    for (let i = 0; i < numSamples; i++) {
      float32Array[i] = inputArray[i] / 32768.0;
    }
    return float32Array;
  }
}

export class LiveVideoOutputManager {
  private mediaSource: MediaSource | null = null;
  private sourceBuffer: SourceBuffer | null = null;
  private chunkQueue: ArrayBuffer[] = [];
  private initialized = false;
  private codec = 'video/mp4; codecs="avc1.42c020, mp4a.40.2"';

  constructor(videoElementId = "video_player") {
    if (typeof window !== "undefined") {
      this.initMediaSource(videoElementId);
    }
  }

  initMediaSource(videoElementId = "video_player"): boolean {
    if (typeof window === "undefined") return false;
    const video = document.getElementById(videoElementId) as HTMLVideoElement;
    if (!video) return false;

    if (this.initialized && this.mediaSource) return true;

    video.muted = false;

    if ("MediaSource" in window) {
      const candidateCodecs = [
        'video/mp4; codecs="avc1.42c020, mp4a.40.2"',
        'video/mp4; codecs="avc1.42E01E, mp4a.40.2"',
        'video/mp4; codecs="avc1.4D401F"',
        'video/mp4; codecs="avc1.64001E"',
        'video/mp4',
        'video/webm; codecs="vp8, opus"',
        'video/webm; codecs="vp9, opus"',
        'video/webm'
      ];
      let supportedCodec = this.codec;
      for (const c of candidateCodecs) {
        if (MediaSource.isTypeSupported(c)) {
          supportedCodec = c;
          break;
        }
      }
      this.codec = supportedCodec;

      this.mediaSource = new MediaSource();
      video.src = URL.createObjectURL(this.mediaSource);

      this.mediaSource.addEventListener("sourceopen", () => {
        try {
          if (!this.mediaSource) return;
          this.sourceBuffer = this.mediaSource.addSourceBuffer(this.codec);
          this.sourceBuffer.mode = "sequence";
          this.sourceBuffer.addEventListener("updateend", () => {
            this.processQueue();
          });
          this.initialized = true;
          this.processQueue();
        } catch (e) {
          console.error("Error initializing MediaSource buffer:", e);
        }
      });
      return true;
    }
    return false;
  }

  playVideoChunk(base64Chunk: string): void {
    if (!this.initialized) {
      this.initMediaSource("video_player");
    }

    const arrayBuffer = LiveAudioOutputManager.base64ToArrayBuffer(base64Chunk);
    this.chunkQueue.push(arrayBuffer);
    this.processQueue();

    const video = document.getElementById("video_player") as HTMLVideoElement;
    if (video && video.paused) {
      video.play().catch(() => {});
    }
  }

  private processQueue(): void {
    if (!this.sourceBuffer || this.sourceBuffer.updating || this.chunkQueue.length === 0) {
      return;
    }

    try {
      const chunk = this.chunkQueue.shift();
      if (chunk) {
        this.sourceBuffer.appendBuffer(chunk);
      }
    } catch (e) {
      console.error("Error appending video buffer chunk:", e);
    }
  }
}
