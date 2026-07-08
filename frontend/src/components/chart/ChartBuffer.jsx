// Buffer circular de candles para renderização eficiente
// Mantém apenas a janela visível em memória de trabalho

export class ChartBuffer {
  constructor(maxSize = 500) {
    this.maxSize = maxSize;
    this.data = [];
    this.viewStart = 0; // índice no array data
    this.viewCount = 80; // quantas velas mostrar
  }

  load(candles) {
    this.data = [...candles].sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
    if (this.data.length > this.maxSize) {
      this.data = this.data.slice(-this.maxSize);
    }
    this.viewStart = Math.max(0, this.data.length - this.viewCount);
  }

  updateLast(candle) {
    if (this.data.length === 0) { this.data.push(candle); return; }
    const last = this.data[this.data.length - 1];
    if (last.timestamp === candle.timestamp) {
      this.data[this.data.length - 1] = candle;
    } else {
      this.data.push(candle);
      if (this.data.length > this.maxSize) this.data.shift();
      // Avança view se estávamos no final
      if (this.viewStart >= this.data.length - this.viewCount - 1) {
        this.viewStart = Math.max(0, this.data.length - this.viewCount);
      }
    }
  }

  getVisible() {
    return this.data.slice(this.viewStart, this.viewStart + this.viewCount);
  }

  getAll() { return this.data; }

  getLast() { return this.data[this.data.length - 1] || null; }

  zoom(delta, pivotRatio = 0.7) {
    const prev = this.viewCount;
    this.viewCount = Math.max(20, Math.min(300, this.viewCount + delta));
    // Mantém o ponto de pivô fixo
    const shift = Math.round((this.viewCount - prev) * pivotRatio);
    this.viewStart = Math.max(0, Math.min(this.data.length - this.viewCount, this.viewStart - shift));
  }

  pan(candlesDelta) {
    this.viewStart = Math.max(0, Math.min(this.data.length - this.viewCount, this.viewStart + candlesDelta));
  }

  isAtEnd() {
    return this.viewStart + this.viewCount >= this.data.length;
  }
}