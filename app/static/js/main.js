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
