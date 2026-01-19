// Lightweight WebSocket client for streaming deltas.
// Exposes window.StreamClient.
(function(global) {
  class StreamClient {
    constructor(url, options = {}) {
      this.url = url;
      this.reconnectDelay = options.reconnectDelay || 1000;
      this.subTypes = new Set();
      this.ws = null;
      this.onMessage = options.onMessage || (() => {});
      this._shouldRun = false;
    }

    subscribe(types, handler) {
      this.subTypes = new Set(types || []);
      if (handler) {
        this.onMessage = handler;
      }
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this._sendSub();
      } else {
        this.start();
      }
    }

    start() {
      if (this._shouldRun) return;
      this._shouldRun = true;
      this._connect();
    }

    stop() {
      this._shouldRun = false;
      if (this.ws) {
        this.ws.close();
      }
    }

    _connect() {
      if (!this._shouldRun) return;
      this.ws = new WebSocket(this.url);
      this.ws.onopen = () => this._sendSub();
      this.ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data);
          if (msg.type && msg.data !== undefined) {
            this.onMessage(msg.type, msg.data);
          }
        } catch (err) {
          console.warn('Bad stream message', err);
        }
      };
      this.ws.onclose = () => {
        if (this._shouldRun) {
          setTimeout(() => this._connect(), this.reconnectDelay);
        }
      };
      this.ws.onerror = () => {
        this.ws.close();
      };
    }

    _sendSub() {
      if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;
      this.ws.send(JSON.stringify({
        action: "subscribe",
        types: Array.from(this.subTypes)
      }));
    }
  }

  global.StreamClient = StreamClient;
})(window);
