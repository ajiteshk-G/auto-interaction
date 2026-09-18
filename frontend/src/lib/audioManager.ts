export class LiveAudioOutputManager {
  private audioContext: AudioContext | null = null;
  private initialized = false;
  private nextPlayTime = 0;
  private activeSources: AudioBufferSourceNode[] = [];
  public onPlaybackStateChange?: (isPlaying: boolean) => void;

  async initializeAudioContext(): Promise<void> {
    try {
      let createdFreshContext = false;
      if (!this.audioContext || this.audioContext.state === "closed") {
        const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
        this.audioContext = new AudioCtx({ sampleRate: 24000 });
        createdFreshContext = true;
      }
      if (this.audioContext.state === "suspended") {
        await this.audioContext.resume();
      }
      // Only rewind the cursor for a brand new context. This method is also
      // called on user gestures (mic toggle, sending a message) that can land
      // while a reply is still scheduled; rewinding then would stack buffers
      // on top of playing audio and double the voice.
      if (createdFreshContext) {
        this.nextPlayTime = this.audioContext.currentTime;
      }
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
      // The playback cursor must only ever move FORWARD.
      //
      // Gemini Live streams native audio roughly 3x faster than real time, so
      // `nextPlayTime` legitimately runs well ahead of `currentTime` -- that is
      // just the jitter buffer doing its job. A previous version also reset the
      // cursor whenever it got more than 1.0s ahead; that yanked it backwards
      // mid-reply and scheduled fresh buffers on top of audio that was still
      // playing, which is heard as two overlapping voices. Barge-in is handled
      // by interrupt(), which stops the sources properly -- never by rewinding
      // the cursor here.
      if (this.nextPlayTime < now) {
        this.nextPlayTime = now + 0.02; // small lead-in avoids clipping the attack
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
