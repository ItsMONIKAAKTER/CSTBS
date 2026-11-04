// Stadium gate QR camera scanner. BarcodeDetector is optional; the normal
// camera app/manual form remain available without any external CDN.
(() => {
  const video = document.getElementById('gate-video');
  if (!video) return;
  const start = document.getElementById('start-scanner');
  const stop = document.getElementById('stop-scanner');
  const status = document.getElementById('scanner-status');
  let stream = null;
  let timeoutId = null;
  let scanning = false;
  const shutdown = () => {
    scanning = false;
    if (timeoutId) window.clearTimeout(timeoutId);
    if (stream) stream.getTracks().forEach(track => track.stop());
    video.srcObject = null;
    stream = null;
    status.textContent = 'Camera stopped.';
  };
  stop?.addEventListener('click', shutdown);
  window.addEventListener('pagehide', shutdown, { once: true });
  start?.addEventListener('click', async () => {
    if (!('BarcodeDetector' in window) || !navigator.mediaDevices?.getUserMedia) {
      status.textContent = 'Direct scanning is unavailable in this browser. Use your camera app or paste the QR link.';
      return;
    }
    try {
      shutdown();
      stream = await navigator.mediaDevices.getUserMedia({ audio: false, video: { facingMode: 'environment' } });
      video.srcObject = stream;
      await video.play();
      const detector = new window.BarcodeDetector({ formats: ['qr_code'] });
      scanning = true;
      status.textContent = 'Point the camera at the official CSTBS QR ticket.';
      const scanFrame = async () => {
        if (!scanning) return;
        try {
          const codes = await detector.detect(video);
          const code = codes.find(item => item.rawValue);
          if (code) {
            const raw = code.rawValue;
            const target = new URL(raw, window.location.origin);
            if (target.origin !== window.location.origin ||
                !target.pathname.startsWith('/entry/verify/') || target.search || target.hash) {
              status.textContent = 'That QR does not belong to this CSTBS server.';
            } else {
              shutdown();
              window.location.assign(target.href); // GET verification only; POST must authorize entry.
              return;
            }
          }
        } catch (_) { status.textContent = 'Unable to read QR; try again or paste its link.'; }
        timeoutId = window.setTimeout(scanFrame, 280);
      };
      scanFrame();
    } catch (_) {
      shutdown();
      status.textContent = 'Camera unavailable or permission denied. Try HTTPS / localhost, or enter the QR URL manually.';
    }
  });
})();
