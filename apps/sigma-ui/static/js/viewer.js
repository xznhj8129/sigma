// /static/js/viewer.js (Complete File)

export class Viewer {
    constructor({ container, media, id, onMark, webrtc = false }) {
      // container is the element managed by GoldenLayout (e.g., the component's root element)
      this.container = container;
      this.media = media; // The actual <img> or <video> element
      this.id = id;
      this.onMark = onMark;
      this.zoom = 1.0;
      this.panX = 0.5;
      this.panY = 0.5;
      this.lastClick = null;
      this.isWebRTC = webrtc;

      // Internal elements managed by this class
      this.wrapper = null; // Internal div for positioning canvas etc.
      this.canvas = null;
      this.ctx = null;

      // Flag to prevent resize/draw calls before DOM setup is complete
      this.isInitialized = false;

      // Start initialization
      this.init();
    }

    async init() {
      this.setupDOM(); // Creates wrapper, canvas, appends to container
      if (this.isWebRTC) {
          try {
              await this.startWebRTC(this.media, this.id);
          } catch (error) {
              console.error(`Viewer ${this.id}: WebRTC initialization failed:`, error);
              // Optionally display an error message on the canvas/wrapper
          }
      }
      this.attachEvents(); // Setup mouse/touch/wheel listeners

      // *** REMOVED internal resize observation ***
      // this.observeResize();

      this.isInitialized = true; // Mark setup as complete

      // Call resize once initially AFTER DOM is set up and flag is true,
      // using the initial container size. The external call will handle subsequent resizes.
      // Use a minimal timeout to ensure layout might be settled.
      setTimeout(() => this.resize(), 0);

      this.drawLoop(); // Start the rendering loop
    }

    async startWebRTC(video, streamId) {
      console.log(`Viewer ${this.id}: Starting WebRTC for ${streamId}`);
      const pc = new RTCPeerConnection({
          // Optional: Add ICE servers configuration here if needed
          // iceServers: [{ urls: 'stun:stun.l.google.com:19302' }]
      });

      pc.onicecandidate = event => {
          // Optional: Handle ICE candidates if needed by signaling server
          // console.log(`Viewer ${this.id}: ICE candidate`, event.candidate);
      };
      pc.onconnectionstatechange = event => {
          console.log(`Viewer ${this.id}: WebRTC connection state: ${pc.connectionState}`);
          if (pc.connectionState === 'failed' || pc.connectionState === 'disconnected' || pc.connectionState === 'closed') {
              // Handle connection failure/closure
          }
      };
      pc.ontrack = e => {
        console.log(`Viewer ${this.id}: Received remote track`);
        if (video.srcObject !== e.streams[0]) {
            video.srcObject = e.streams[0];
            video.play().catch(err => console.error(`Viewer ${this.id}: Video play failed:`, err));
        }
      };

      // Add transceiver for receiving video
      pc.addTransceiver("video", { direction: "recvonly" });

      try {
          const offer = await pc.createOffer();
          await pc.setLocalDescription(offer);

          console.log(`Viewer ${this.id}: Sending offer to signalling server...`);
          const res = await fetch(`http://localhost:8081/offer?path=${encodeURIComponent(streamId)}`, {
              method: "POST",
              body: JSON.stringify(pc.localDescription), // Send the full local description
              headers: { "Content-Type": "application/json" }
          });

          if (!res.ok) {
              throw new Error(`Signalling server responded with ${res.status}: ${await res.text()}`);
          }

          const answer = await res.json();
          console.log(`Viewer ${this.id}: Received answer from signalling server.`);
          await pc.setRemoteDescription(new RTCSessionDescription(answer)); // Ensure it's an RTCSessionDescription
          console.log(`Viewer ${this.id}: WebRTC setup complete.`);

      } catch (error) {
          console.error(`Viewer ${this.id}: WebRTC signalling error:`, error);
          // Handle signalling errors (e.g., display message)
          throw error; // Re-throw to be caught by caller if needed
      }
    }

    setupDOM() {
      // Internal wrapper div for positioning and event handling structure
      this.wrapper = document.createElement("div");
      this.wrapper.style.position = "relative"; // Needed for absolute canvas positioning
      this.wrapper.style.width = "100%";
      this.wrapper.style.height = "100%";
      this.wrapper.style.overflow = "hidden"; // Clip canvas content
      this.wrapper.style.touchAction = "none"; // Prevent default touch actions like scrolling
      this.wrapper.style.background = "black"; // Background shown behind media/canvas

      // The canvas where the media is actually drawn
      this.canvas = document.createElement("canvas");
      this.canvas.style.position = "absolute";
      this.canvas.style.top = '0';
      this.canvas.style.left = '0';
      // Let CSS handle the visual size initially; pixel size set in resize()
      this.canvas.style.width = "100%";
      this.canvas.style.height = "100%";
      this.canvas.style.pointerEvents = "auto"; // Allow canvas to receive events

      // Hide the original media element; we render it onto the canvas
      this.media.style.display = "none";

      // Append elements to the DOM structure
      this.wrapper.appendChild(this.media); // Keep media in DOM for drawing source
      this.wrapper.appendChild(this.canvas);
      // Append our internal wrapper to the container provided by GoldenLayout
      this.container.appendChild(this.wrapper);

      // Get the 2D rendering context
      this.ctx = this.canvas.getContext("2d");
    }

    // *** observeResize() method is REMOVED ***

    // This resize method is now intended to be CALLED EXTERNALLY (e.g., by GoldenLayout resize handler)
    resize() {
      // Allow resize even through transient zero/hidden states (e.g., devtools toggle)
      if (!this.isInitialized || !this.container || !this.canvas) {
        return;
      }

      const containerWidth = this.container.clientWidth;
      const containerHeight = this.container.clientHeight;

      if (this.canvas.width !== containerWidth || this.canvas.height !== containerHeight) {
        this.canvas.width = containerWidth;
        this.canvas.height = containerHeight;
        console.log(`Viewer ${this.id}: Canvas buffer resized to ${containerWidth}x${containerHeight}`);
      }
    }

    getImageSize() {
      // Return the native dimensions of the media source
      if (this.media instanceof HTMLImageElement) {
        // For images, use naturalWidth/Height
        return { iw: this.media.naturalWidth, ih: this.media.naturalHeight };
      } else if (this.media instanceof HTMLVideoElement) {
        // For videos, use videoWidth/Height
        return { iw: this.media.videoWidth, ih: this.media.videoHeight };
      } else {
        // Fallback or handle other media types if necessary
        return { iw: 0, ih: 0 };
      }
    }

    attachEvents() {
      let dragging = false, pinchStart = null;
      let startX, startY, originX, originY;
      let moved = false; // Flag to distinguish click from drag

      // --- Mouse Events ---
      this.canvas.addEventListener("mousedown", e => {
        moved = false;
        dragging = true;
        startX = e.clientX;
        startY = e.clientY;
        originX = this.panX;
        originY = this.panY;
        this.canvas.style.cursor = 'grabbing'; // Indicate dragging capability
      });

      // Use window for mousemove/mouseup to capture events even if cursor leaves canvas
      window.addEventListener("mousemove", e => {
        if (!dragging) return;
        // Check if the mouse button is still pressed (robustness)
        if (e.buttons !== 1) {
             dragging = false;
             this.canvas.style.cursor = 'grab';
             return;
        }
        moved = true; // It's a drag, not a click
        const bounds = this.canvas.getBoundingClientRect(); // Get current canvas size/pos
        // Prevent division by zero if bounds are invalid
        if (bounds.width === 0 || bounds.height === 0) return;
        const dx = (e.clientX - startX) / bounds.width;
        const dy = (e.clientY - startY) / bounds.height;
        // Adjust pan based on distance moved and current zoom level
        this.panX = originX - dx / this.zoom;
        this.panY = originY - dy / this.zoom;
      });

      window.addEventListener("mouseup", e => {
        if (dragging) {
            dragging = false;
            this.canvas.style.cursor = 'grab'; // Reset cursor
            // Click logic is handled separately by the 'click' event
        }
      });

       // Set initial cursor state
       this.canvas.style.cursor = 'grab';

      // --- Click Event (for Marking) ---
      this.canvas.addEventListener("click", e => {
        // Only process click if it wasn't part of a drag motion
        if (moved) {
            moved = false; // Reset moved flag for next interaction
            return;
        }

        const { iw, ih } = this.getImageSize();
        // Ensure media dimensions are valid
        if (!iw || !ih || iw === 0 || ih === 0) return;

        const rect = this.canvas.getBoundingClientRect();
        const cw = rect.width; // Use clientWidth? Check consistency
        const ch = rect.height; // Use clientHeight? Check consistency

        // Calculate scale factor including zoom
        const s = Math.min(cw / iw, ch / ih) * this.zoom;

        // Calculate the source crop rectangle based on pan and zoom
        const cropW = iw / this.zoom;
        const cropH = ih / this.zoom;
        let cropX = this.panX * iw - cropW / 2;
        let cropY = this.panY * ih - cropH / 2;
        cropX = Math.max(0, Math.min(cropX, iw - cropW)); // Clamp crop rect to bounds
        cropY = Math.max(0, Math.min(cropY, ih - cropH));

        // Calculate the dimensions and position where the cropped source is drawn on the canvas
        const drawW = iw * s; // Use natural dimensions here for calculation consistency
        const drawH = ih * s;
        const drawX = (cw - drawW) / 2; // Centering offset
        const drawY = (ch - drawH) / 2;

        // Mouse coordinates relative to the canvas
        const mx = e.clientX - rect.left;
        const my = e.clientY - rect.top;

        // Convert canvas click coordinates to coordinates relative to the *drawn image* (0 to 1)
        const relX = (mx - drawX) / drawW;
        const relY = (my - drawY) / drawH;

        // Check if the click was within the bounds of the drawn image
        if (relX < 0 || relX > 1 || relY < 0 || relY > 1) {
            this.lastClick = null; // Click was outside the image bounds
            return;
        }

        // Convert relative coordinates to coordinates within the *original full-size media*
        const imgX = cropX + relX * cropW;
        const imgY = cropY + relY * cropH;

        // Store the calculated click coordinates (on original image)
        this.lastClick = { x: imgX, y: imgY };
        console.log(`Viewer ${this.id}: Click registered at image coordinates: (${imgX.toFixed(2)}, ${imgY.toFixed(2)})`);


        // If an onMark callback is provided, call it with the mark data
        const payload = this.mark();
        if (payload && typeof this.onMark === 'function') {
            this.onMark(payload);
        }

         // Reset moved flag after click processing
         moved = false;
      });

      // --- Touch Events ---
      this.canvas.addEventListener("touchstart", e => {
        e.preventDefault(); // Prevent default actions like page scroll
        if (e.touches.length === 1) {
          // Single touch: Initiate potential drag
          moved = false;
          dragging = true;
          startX = e.touches[0].clientX;
          startY = e.touches[0].clientY;
          originX = this.panX;
          originY = this.panY;
        } else if (e.touches.length === 2) {
          // Two touches: Initiate pinch zoom
          dragging = false; // Stop dragging if it was happening
          pinchStart = this.getPinchDistance(e);
        }
      }, { passive: false }); // Need passive: false to call preventDefault

      this.canvas.addEventListener("touchmove", e => {
        e.preventDefault(); // Prevent scrolling during touch move on canvas
        const bounds = this.canvas.getBoundingClientRect();
        if (bounds.width === 0 || bounds.height === 0) return;

        if (e.touches.length === 1 && dragging) {
          // Single touch move: Panning
          moved = true; // It's a drag/pan
          const dx = (e.touches[0].clientX - startX) / bounds.width;
          const dy = (e.touches[0].clientY - startY) / bounds.height;
          this.panX = originX - dx / this.zoom;
          this.panY = originY - dy / this.zoom;
        } else if (e.touches.length === 2 && pinchStart !== null) {
          // Two touches move: Pinch Zooming
          moved = true; // Register movement
          const now = this.getPinchDistance(e);
          if (pinchStart > 0) { // Avoid division by zero
              const scaleFactor = now / pinchStart;
              const newZoom = Math.max(1.0, this.zoom * scaleFactor); // Ensure zoom doesn't go below 1.0

              // --- Adjust Pan based on Pinch Center (Advanced) ---
              // Calculate pinch center relative to canvas
              const pinchCenterX = (e.touches[0].clientX + e.touches[1].clientX) / 2 - bounds.left;
              const pinchCenterY = (e.touches[0].clientY + e.touches[1].clientY) / 2 - bounds.top;
              const cx = pinchCenterX / bounds.width;
              const cy = pinchCenterY / bounds.height;

              // Apply pan adjustment similar to wheel zoom
              this.panX += (cx - 0.5) * (1 / this.zoom - 1 / newZoom);
              this.panY += (cy - 0.5) * (1 / this.zoom - 1 / newZoom);
              // --- End Pan Adjustment ---

              this.zoom = newZoom;
              pinchStart = now; // Update pinch start distance for continuous zooming
          }
        }
      }, { passive: false });

      this.canvas.addEventListener("touchend", e => {
        // Reset interaction states when touches end
        if (!moved && e.touches.length === 0) {
            // If no movement occurred and all touches are up, consider it a tap (handled by 'click' event simulation or separate tap logic if needed)
             // Be cautious here, rely on the 'click' event triggered by browsers after touchend if possible.
        }

        if (e.touches.length < 2) {
            pinchStart = null; // Stop pinching if less than 2 touches
        }
        if (e.touches.length < 1) {
            dragging = false; // Stop dragging if no touches left
            // Reset moved after a short delay to allow click event to fire if it was a tap
            setTimeout(() => { moved = false; }, 50);
        }
      });

      // --- Wheel Event (for Zooming) ---
      this.canvas.addEventListener("wheel", e => {
        e.preventDefault(); // Prevent page scroll
        const rect = this.canvas.getBoundingClientRect();
        if (rect.width === 0 || rect.height === 0) return;

        // Calculate mouse position relative to canvas (0 to 1)
        const cx = (e.clientX - rect.left) / rect.width;
        const cy = (e.clientY - rect.top) / rect.height;

        // Determine zoom factor (increase or decrease)
        const factor = e.deltaY < 0 ? 1.1 : 1 / 1.1; // Smoother zoom steps
        const newZoom = Math.max(1.0, this.zoom * factor); // Clamp zoom at 1.0 minimum

        // Adjust pan position towards the mouse cursor during zoom
        // This makes zooming feel centered on the cursor position
        this.panX += (cx - 0.5) * (1 / this.zoom - 1 / newZoom);
        this.panY += (cy - 0.5) * (1 / this.zoom - 1 / newZoom);

        // Apply the new zoom level
        this.zoom = newZoom;
      }, { passive: false }); // Need passive: false for preventDefault
    } // End attachEvents

    getPinchDistance(e) {
      // Calculate distance between two touch points
      const dx = e.touches[0].clientX - e.touches[1].clientX;
      const dy = e.touches[0].clientY - e.touches[1].clientY;
      return Math.sqrt(dx * dx + dy * dy);
    }

    drawLoop() {
      const draw = () => {
        // Ensure initialization is complete and we have valid elements/context
        if (!this.isInitialized || !this.canvas || !this.ctx || this.canvas.width === 0 || this.canvas.height === 0) {
          requestAnimationFrame(draw); // Skip frame if not ready
          return;
        }

        // Get current media dimensions
        const { iw, ih } = this.getImageSize();
        // Skip frame if media dimensions aren't available yet (e.g., video loading)
        if (!iw || !ih || iw === 0 || ih === 0) {
          requestAnimationFrame(draw);
          return;
        }

        // Get current canvas buffer dimensions (set by external resize call)
        const cw = this.canvas.width;
        const ch = this.canvas.height;

        // --- Calculate Drawing Parameters ---
        // Scale factor based on fitting media to canvas, adjusted by zoom
        const s = Math.min(cw / iw, ch / ih) * this.zoom;
        // Dimensions of the scaled media as it will be drawn
        const drawW = iw * s;
        const drawH = ih * s;
        // Dimensions of the source rectangle (crop) from the original media
        const cropW = iw / this.zoom;
        const cropH = ih / this.zoom;
        // Top-left corner of the source rectangle, based on panning and centered
        let cropX = this.panX * iw - cropW / 2;
        let cropY = this.panY * ih - cropH / 2;
        // Clamp the crop rectangle to the bounds of the original media
        cropX = Math.max(0, Math.min(cropX, iw - cropW));
        cropY = Math.max(0, Math.min(cropY, ih - cropH));
        // Top-left corner for drawing on the canvas (centered)
        const drawX = (cw - drawW) / 2;
        const drawY = (ch - drawH) / 2;
        // --- End Calculation ---


        // --- Drawing ---
        // Clear the canvas for the new frame
        this.ctx.clearRect(0, 0, cw, ch);
        // Disable image smoothing for potentially sharper rendering at non-integer scales
        this.ctx.imageSmoothingEnabled = false;
        // Draw the (potentially cropped) media onto the canvas, scaled and centered
        this.ctx.drawImage(this.media,
                           cropX, cropY, cropW, cropH, // Source rectangle (sx, sy, sWidth, sHeight)
                           drawX, drawY, drawW, drawH  // Destination rectangle (dx, dy, dWidth, dHeight)
                          );

        // Draw the crosshair marker if a click has occurred
        if (this.lastClick) {
          // Calculate marker position on the canvas based on its position on the original image
          const relX = (this.lastClick.x - cropX) / cropW;
          const relY = (this.lastClick.y - cropY) / cropH;
          const markerCanvasX = drawX + relX * drawW;
          const markerCanvasY = drawY + relY * drawH;

          // Draw simple crosshair
          this.ctx.strokeStyle = "rgba(255, 255, 255, 0.8)"; // White with some transparency
          this.ctx.lineWidth = 1;
          this.ctx.beginPath();
          this.ctx.moveTo(markerCanvasX - 10, markerCanvasY);
          this.ctx.lineTo(markerCanvasX + 10, markerCanvasY);
          this.ctx.moveTo(markerCanvasX, markerCanvasY - 10);
          this.ctx.lineTo(markerCanvasX, markerCanvasY + 10);
          this.ctx.stroke();
        }
        // --- End Drawing ---

        // Request the next frame to continue the loop
        requestAnimationFrame(draw);
      }; // End of draw function definition

      // Start the animation loop
      requestAnimationFrame(draw);
    } // End drawLoop

    mark() {
      // Return the stored click coordinates and other relevant data
      if (!this.lastClick) return null;
      return {
        id: this.id,
        x: this.lastClick.x, // Coordinate on original image
        y: this.lastClick.y, // Coordinate on original image
        // Include timestamp if the media is a video
        time: (this.media instanceof HTMLVideoElement) ? this.media.currentTime : 0
      };
    }

    // Optional: Add a destroy method for cleanup if needed
    destroy() {
        console.log(`Viewer ${this.id}: Destroy called`);
        // Stop the draw loop? (requestAnimationFrame usually stops if element is removed)
        // Remove event listeners explicitly? (Modern browsers might garbage collect, but explicit removal is safer)
        // e.g., window.removeEventListener("mousemove", ...); window.removeEventListener("mouseup", ...);
        // Stop WebRTC connection if active? (pc.close())
        if (this.wrapper && this.wrapper.parentNode) {
            this.wrapper.parentNode.removeChild(this.wrapper);
        }
        this.isInitialized = false;
        // Clear references
        this.container = null;
        this.media = null;
        this.canvas = null;
        this.ctx = null;
        this.wrapper = null;
    }

} // End Class Viewer
