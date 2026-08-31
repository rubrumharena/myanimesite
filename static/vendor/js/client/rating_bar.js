function partsOf(element) {
    const scope = element.closest('[data-rating]');
    if (!scope) return null;

    return {
        scope,
        stars: scope.querySelector('[data-rating-stars]'),
        value: scope.querySelector('[data-rating-value]'),
        input: scope.querySelector('[data-rating-input]'),
        flag: scope.querySelector('[data-review-flag]'),
        panel: scope.querySelector('[data-review-panel]'),
        toggle: scope.querySelector('[data-review-toggle]'),
    };
}

function colorFor(score) {
    if (!score) return 'var(--color-neutral-400)';

    const t = (Math.max(1, Math.min(10, score)) - 1) / 9;

    const l = 63.7 + (78.9 - 63.7) * t;
    const c = 0.237 + (0.154 - 0.237) * t;
    const h = 25.3 + (211.5 - 25.3) * t;

    return `oklch(${l.toFixed(1)}% ${c.toFixed(3)} ${h.toFixed(1)})`;
}

function paintStars(parts, score) {
    parts.scope.style.setProperty('--rating-color', colorFor(score));

    parts.stars.querySelectorAll('.star').forEach((star, i) => {
        const filled = Math.min(100, Math.max(0, (score - i) * 100));
        star.querySelector('.rect-gold').setAttribute('width', `${filled}%`);
        star.querySelector('.rect-gray').setAttribute('x', `${filled}%`);
    });

    if (parts.value) parts.value.textContent = score ? score.toFixed(1) : 'NS';
    parts.suffix?.classList.toggle('hidden', !score);
}

function scoreFromPointer(parts, clientX) {
    const rect = parts.stars.querySelector('ul').getBoundingClientRect();
    const raw = ((clientX - rect.left) / rect.width) * 10;
    const snapped = Math.round(raw * 2) / 2;

    return Math.min(10, Math.max(0, snapped));
}

function commit(parts, score) {
    parts.stars.dataset.value = String(score);
    if (parts.input) parts.input.value = score ? score.toFixed(1) : '';
    paintStars(parts, score);
}

function setReviewMode(parts, on) {
    parts.panel?.classList.toggle('hidden', !on);
    parts.panel?.classList.toggle('flex', on);

    if (parts.flag) parts.flag.value = on ? '1' : '0';

    parts.toggle?.setAttribute('aria-pressed', String(on));
    parts.toggle?.classList.toggle('!text-(--accent)', on);
    parts.toggle?.classList.toggle('bg-(--accent)/10', on);
    parts.toggle?.classList.toggle('!text-neutral-400', !on);

    if (!on) commit(parts, 0);
}

let dragging = null;

document.addEventListener('pointerdown', event => {
    const stars = event.target.closest('[data-rating-stars]');
    if (!stars) return;

    const parts = partsOf(stars);
    if (!parts) return;

    dragging = parts;
    stars.setPointerCapture?.(event.pointerId);
    commit(parts, scoreFromPointer(parts, event.clientX));
});

document.addEventListener('pointermove', event => {
    if (!dragging) return;
    commit(dragging, scoreFromPointer(dragging, event.clientX));
});

document.addEventListener('pointerup', () => { dragging = null; });
document.addEventListener('pointercancel', () => { dragging = null; });

document.addEventListener('click', event => {
    const toggle = event.target.closest('[data-review-toggle]');
    if (!toggle) return;

    const parts = partsOf(toggle);
    if (!parts) return;

    setReviewMode(parts, parts.flag?.value !== '1');
});

document.addEventListener('submit', event => {
    const scope = event.target.querySelector('[data-rating]');
    if (!scope) return;

    const parts = partsOf(scope.firstElementChild ?? scope);
    if (!parts?.flag) return;

    if (parts.flag.value === '1' && !parts.input?.value) {
        event.preventDefault();
        parts.stars.classList.add('ring-2', 'ring-red-500/50', 'rounded-lg');
        setTimeout(() => parts.stars.classList.remove('ring-2', 'ring-red-500/50', 'rounded-lg'), 1200);
    }
});


document.addEventListener('click', () => {
    document.title = `stars: ${document.querySelectorAll('[data-rating-stars]').length}`;
}, true);