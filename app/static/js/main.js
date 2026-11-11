// Small, accessible mobile navigation enhancement; no libraries required.
const toggle = document.querySelector('.nav-toggle');
const links = document.querySelector('.nav-links');

if (toggle && links) {
    document.documentElement.classList.add('has-js');
    toggle.addEventListener('click', () => {
        const isOpen = toggle.getAttribute('aria-expanded') === 'true';
        toggle.setAttribute('aria-expanded', String(!isOpen));
        links.classList.toggle('is-open', !isOpen);
    });
}

// Ask administrators to confirm event deletion; server-side POST + CSRF remain mandatory.
for (const form of document.querySelectorAll('form[data-confirm]')) {
    form.addEventListener('submit', (event) => {
        if (!window.confirm(form.dataset.confirm)) event.preventDefault();
    });
}

// V5.3: Accessible light/dark themes, persisted only in the visitor's browser.
(() => {
  const button = document.querySelector('.theme-toggle');
  const prefersDark = window.matchMedia?.('(prefers-color-scheme: dark)').matches;
  let theme = prefersDark ? 'night' : 'day';
  try {
    const stored = window.localStorage.getItem('cstbs-theme');
    if (stored === 'night' || stored === 'day') theme = stored;
  } catch (_) { /* Browser storage can be disabled; theme still works. */ }
  const apply = () => {
    document.documentElement.dataset.theme = theme;
    if (button) {
      button.textContent = theme === 'night' ? '☀' : '☾';
      button.setAttribute('aria-pressed', String(theme === 'night'));
      button.setAttribute('aria-label', theme === 'night' ? 'Switch to campus light theme' : 'Switch to stadium night theme');
    }
  };
  apply();
  button?.addEventListener('click', () => {
    theme = theme === 'night' ? 'day' : 'night';
    try { window.localStorage.setItem('cstbs-theme', theme); } catch (_) {}
    apply();
  });
  if (window.IntersectionObserver && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    const sections = document.querySelectorAll('.metric-card, .event-card, .report-card');
    const observer = new IntersectionObserver((entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          entry.target.classList.add('revealed');
          observer.unobserve(entry.target);
        }
      }
    }, { threshold: 0.1 });
    for (const section of sections) {
      section.classList.add('reveal-ready');
      observer.observe(section);
    }
  }
})();
