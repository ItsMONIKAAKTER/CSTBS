// Accessible, progressively-enhanced V3 seat picker. The server remains authoritative.
(() => {
  const form = document.getElementById('seat-booking-form');
  if (!form) return;
  const buttons = [...document.querySelectorAll('.seat-button')];
  const selected = new Set();
  const max = Number(form.dataset.maxSeats);
  const seatIds = document.getElementById('seat-ids');
  const totalPrice = document.getElementById('total-price');
  const seatCount = document.getElementById('seat-count');
  const labels = document.getElementById('selected-labels');
  const reviewButton = document.getElementById('review-button');
  const status = document.getElementById('seat-status');
  const summary = document.getElementById('availability-summary');
  const price = Number(form.dataset.price);

  const render = () => {
    const chosen = buttons.filter(button => selected.has(button.dataset.seatId));
    seatIds.value = chosen.map(button => button.dataset.seatId).join(',');
    seatCount.textContent = String(chosen.length);
    labels.textContent = chosen.length
      ? chosen.map(button => button.dataset.label).join(' · ')
      : 'No seats selected yet';
    totalPrice.textContent = new Intl.NumberFormat('en-US', {
      style: 'currency', currency: 'USD'
    }).format(price * chosen.length);
    reviewButton.disabled = chosen.length === 0;
    for (const button of buttons) {
      const isSelected = selected.has(button.dataset.seatId);
      button.classList.toggle('is-selected', isSelected);
      button.setAttribute('aria-pressed', String(isSelected));
    }
  };

  for (const button of buttons) {
    button.addEventListener('click', () => {
      if (button.disabled) return;
      const id = button.dataset.seatId;
      if (selected.has(id)) {
        selected.delete(id);
      } else if (selected.size >= max) {
        status.textContent = `You can reserve up to ${max} seats per confirmation.`;
        return;
      } else {
        selected.add(id);
      }
      status.textContent = 'Your selection is not held until confirmation.';
      render();
    });
  }

  const refresh = async () => {
    try {
      const response = await fetch(form.dataset.availabilityUrl, {
        credentials: 'same-origin', cache: 'no-store', headers: { Accept: 'application/json' }
      });
      if (!response.ok) throw new Error('Availability service returned an error.');
      const data = await response.json();
      const unavailable = new Set(data.reserved_seat_ids.map(String));
      let selectionChanged = false;
      for (const button of buttons) {
        const id = button.dataset.seatId;
        const taken = unavailable.has(id);
        button.classList.toggle('is-taken', taken);
        button.disabled = taken || !data.booking_open;
        button.setAttribute('aria-label',
          `Seat ${button.dataset.label}, ${taken ? 'reserved' : data.booking_open ? 'available' : 'closed'}`);
        if (button.disabled && selected.delete(id)) selectionChanged = true;
      }
      summary.textContent = `${data.available} of ${data.total} seats available`;
      if (selectionChanged) status.textContent = 'A selected seat became unavailable. Your selection was updated.';
      if (!data.booking_open) status.textContent = 'Reservations are closed for this event.';
      render();
    } catch (error) {
      // Do not claim that stale availability is current; POST rechecks it.
      status.textContent = 'Live availability could not refresh. Your seats will be verified on confirmation.';
    }
  };

  form.addEventListener('submit', (event) => {
    if (selected.size === 0) event.preventDefault();
  });
  render();
  refresh();
  const polling = window.setInterval(refresh, 5000);
  window.addEventListener('pagehide', () => window.clearInterval(polling), { once: true });
})();
