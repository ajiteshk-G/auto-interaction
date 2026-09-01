/**
 * AudioWorkletProcessor for 16kHz PCM audio recording with 100ms chunking
 */
class AudioRecorderProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.bufferSize = 1600; // 100ms at 16kHz
    this.buffer = new Int16Array(this.bufferSize);
    this.bytesWritten = 0;
  }

  process(inputs, outputs, parameters) {
    const input = inputs[0];
    if (input && input.length > 0 && input[0]) {
      const inputData = input[0];
      
      for (let i = 0; i < inputData.length; i++) {
        const s = Math.max(-1, Math.min(1, inputData[i]));
        this.buffer[this.bytesWritten++] = s < 0 ? s * 0x8000 : s * 0x7fff;
        
        if (this.bytesWritten >= this.bufferSize) {
          // Calculate RMS
          let sumSquares = 0;
          for (let j = 0; j < this.bufferSize; j++) {
            const norm = this.buffer[j] / 32768;
            sumSquares += norm * norm;
          }
          const rms = Math.sqrt(sumSquares / this.bufferSize);
          
          this.port.postMessage({
            pcm16: this.buffer.slice().buffer,
            rms: rms
          }, [this.buffer.slice().buffer]);
          
          this.bytesWritten = 0;
        }
      }
    }
    return true;
  }
}

registerProcessor("audio-recorder-processor", AudioRecorderProcessor);
