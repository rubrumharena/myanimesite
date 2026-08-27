const FADE_MS = 300;

export function showFormErrors(form, {message, fields = {}} = {}) {
    if (!form) return;

    clearFormErrors(form);

    const prefix = form.dataset.fieldPrefix ?? '';

    for (const [name, text] of Object.entries(fields)) {
        const field = form.elements[prefix + name];
        if (field instanceof HTMLElement) markInvalid(form, field, text);
    }

    if (message) showBanner(form, message);
}

export function clearFormErrors(form) {
    form.querySelectorAll('[aria-invalid="true"]').forEach(field => clearField(form, field));
    hideBanner(form.querySelector('.error-banner'));
}

function markInvalid(form, field, text) {
    field.setAttribute('aria-invalid', 'true');

    const slot = errorSlot(form, field);
    if (slot) {
        if (text) slot.textContent = text;
        slot.hidden = false;
        field.setAttribute('aria-describedby', slot.id);
    }

    field.addEventListener('input', () => clearField(form, field), {once: true});
}

function clearField(form, field) {
    field.removeAttribute('aria-invalid');
    field.removeAttribute('aria-describedby');

    const slot = errorSlot(form, field);
    if (slot) {
        slot.textContent = '';
        slot.hidden = true;
    }
}

function errorSlot(form, field) {
    const name = (field.name ?? '').replace(form.dataset.fieldPrefix ?? '', '');
    return form.querySelector(`[data-error-field="${name}"]`);
}

function showBanner(form, message) {
    let banner = form.querySelector('.error-banner');

    if (!banner) {
        banner = document.createElement('div');
        banner.className = 'error-banner';
        banner.setAttribute('role', 'alert');
        form.prepend(banner);
    }

    banner.textContent = message;
    banner.classList.remove('opacity-0');
    dismissOnInput(form);
}

function dismissOnInput(form) {
    form.addEventListener('input', () => hideBanner(form.querySelector('.error-banner')), {once: true});
}

function hideBanner(banner) {
    if (!banner) return;

    banner.classList.add('opacity-0');
    setTimeout(() => banner.remove(), FADE_MS);
}

document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('form').forEach(form => {
        form.querySelectorAll('.error-message:not([hidden])').forEach(slot => {
            const name = (form.dataset.fieldPrefix ?? '') + slot.dataset.errorField;
            const field = form.elements[name];
            if (field instanceof HTMLElement) markInvalid(form, field);
        });

        if (form.querySelector('.error-banner')) dismissOnInput(form);
    });
});

document.addEventListener('input', event => {
    const field = event.target.closest('[aria-invalid="true"]');
    if (!field) return;

    const form = field.closest('form');
    if (form) clearField(form, field);
});