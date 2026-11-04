/* Gate camera scanner: native QR detector when supported + cross-browser QR
   photograph upload fallback. QR contains a signed token, not a website URL. */
(() => {
  const video = document.getElementById('gate-video');
  if (!video) return;
  const status = document.getElementById('scanner-status');
  const start = document.getElementById('start-scanner');
  const stop = document.getElementById('stop-scanner');
  const gateSelect = document.getElementById('gate-selector');
  const hiddenGates = document.querySelectorAll('.scanner-gate-id');
  let stream = null;
  let timer = null;
  let active = false;
  let detector = null;
  const setStatus = (message) => { status.textContent = message; };
  const shutdown = () => {
    active = false;
    if (timer) clearTimeout(timer);
    timer = null;
    if (stream) stream.getTracks().forEach(track => track.stop());
    stream = null;
    video.srcObject = null;
  };
  gateSelect?.addEventListener('change', () => {
    for (const input of hiddenGates) input.value = gateSelect.value;
    if (active) shutdown();
    setStatus(gateSelect.value ? 'Gate selected. Ready to scan.' : 'Select a gate before scanning.');
  });
  stop?.addEventListener('click', () => { shutdown(); setStatus('Camera stopped.'); });
  window.addEventListener('pagehide', shutdown);
  for (const form of [document.getElementById('manual-code-form'), document.getElementById('qr-photo-form')]) {
    form?.addEventListener('submit', (event) => {
      if (!gateSelect.value) {
        event.preventDefault();
        setStatus('Select the gate where you are working first.');
        gateSelect.focus();
      }
    });
  }
  start?.addEventListener('click', async () => {
    if (!gateSelect.value) {
      setStatus('Select your entrance above before starting the camera.');
      gateSelect.focus(); return;
    }
    if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia) {
      setStatus('Live camera requires HTTPS or localhost. Use the QR photograph form on this page instead.');
      return;
    }
    if (!('BarcodeDetector' in window)) {
      setStatus('Your browser lacks live QR detection. Use the QR photograph button; it works on mobile and desktop.');
      return;
    }
    shutdown();
    try {
      detector = new BarcodeDetector({ formats: ['qr_code'] });
      stream = await navigator.mediaDevices.getUserMedia({ audio: false, video: { facingMode: { ideal: 'environment' } } });
      video.srcObject = stream;
      await video.play();
      active = true;
      setStatus('Camera running. Hold the ticket QR inside the preview.');
      const scanFrame = async () => {
        if (!active) return;
        try {
          const codes = await detector.detect(video);
          const raw = codes.find(value => value.rawValue)?.rawValue;
          if (raw) {
            shutdown();
            // Same-origin navigation to a GET verifier, which NEVER grants entry.
            const url = new URL('/entry/scan', window.location.origin);
            url.searchParams.set('gate_id', gateSelect.value);
            url.searchParams.set('code', raw);
            window.location.assign(url.href);
            return;
          }
        } catch (_) { setStatus('Could not read QR yet. Adjust lighting or use a photo.'); }
        timer = setTimeout(scanFrame, 300);
      };
      scanFrame();
    } catch (error) {
      shutdown();
      const permission = error?.name === 'NotAllowedError' ? 'Camera permission was denied.' : 'Camera unavailable.';
      setStatus(permission + ' Enable permissions or use the photo form below.');
    }
  });
})();
