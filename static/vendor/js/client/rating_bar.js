const REVIEW = {
    get panel()  { return document.getElementById('review-panel'); },
    get toggle() { return document.getElementById('review-toggle'); },
    get stars()  { return document.getElementById('review-stars'); },
    get value()  { return document.getElementById('review-value'); },
    get input()  { return document.getElementById('review-rating'); },
    get flag()   { return document.getElementById('review-flag'); },
};

const STAR_COLORS = ['fill-red-500', 'fill-yellow-300', 'fill-green-500', 'fill-(--accent)', 'fill-neutral-700'];

function colorFor(score) {
    if (!score)    return 'fill-neutral-700';
    if (score < 5) return 'fill-red-500';
    if (score < 7) return 'fill-yellow-300';
    if (score < 9) return 'fill-green-500';
    return 'fill-(--accent)';
}

function paintStars(score) {
    const color = colorFor(score);

    REVIEW.stars.querySelectorAll('.star').forEach((star, i) => {
        const gold = star.querySelector('.rect-gold');
        const gray = star.querySelector('.rect-gray');

        const filled = Math.min(100, Math.max(0, (score - i) * 100));

        gold.setAttribute('width', `${filled}%`);
        gray.setAttribute('x', `${filled}%`);

        gold.classList.remove(...STAR_COLORS);
        gold.classList.add(color);
    });

    const el = REVIEW.value;
    el.classList.remove('!text-red-500', '!text-yellow-300', '!text-green-500', '!text-(--accent)', '!text-neutral-400');

    if (!score) {
        el.textContent = 'NS';
        el.classList.add('!text-neutral-400');
        return;
    }

    el.textContent = score.toFixed(1);
    el.classList.add(color.replace('fill-', '!text-'));
}

function scoreFromPointer(clientX) {
    const rect = REVIEW.stars.querySelector('ul').getBoundingClientRect();
    const ratio = (clientX - rect.left) / rect.width;
    const raw = ratio * 10;

    const snapped = Math.round(raw * 2) / 2;

    return Math.min(10, Math.max(0, snapped));
}

function commit(score) {
    REVIEW.stars.dataset.value = String(score);
    REVIEW.input.value = score.toFixed(1);
    paintStars(score);
}

function setReviewMode(on) {
    REVIEW.panel.classList.toggle('hidden', !on);
    REVIEW.panel.classList.toggle('flex', on);
    REVIEW.flag.value = on ? '1' : '0';
    REVIEW.toggle.setAttribute('aria-pressed', String(on));

    REVIEW.toggle.classList.toggle('!text-(--accent)', on);
    REVIEW.toggle.classList.toggle('bg-(--accent)/10', on);
    REVIEW.toggle.classList.toggle('!text-neutral-400', !on);

    if (!on) {
        REVIEW.input.value = '';
        REVIEW.stars.dataset.value = '0';
        paintStars(0);
    }
}

let dragging = false;

document.addEventListener('pointerdown', (e) => {
    if (!e.target.closest('#review-stars')) return;
    dragging = true;
    REVIEW.stars.setPointerCapture?.(e.pointerId);
    commit(scoreFromPointer(e.clientX));
});

document.addEventListener('pointermove', (e) => {
    if (!dragging) return;
    commit(scoreFromPointer(e.clientX));
});

document.addEventListener('pointerup', () => { dragging = false; });
document.addEventListener('pointercancel', () => { dragging = false; });

document.addEventListener('click', (e) => {
    if (e.target.closest('#review-toggle')) {
        setReviewMode(REVIEW.flag.value === '0');
    }
});

document.addEventListener('submit', (e) => {
    const form = e.target.closest('#comment-form');
    if (!form) return;

    if (REVIEW.flag.value === '1' && !REVIEW.input.value) {
        e.preventDefault();
        REVIEW.stars.classList.add('ring-2', 'ring-red-500/50', 'rounded-lg');
        setTimeout(() => REVIEW.stars.classList.remove('ring-2', 'ring-red-500/50', 'rounded-lg'), 1200);
    }
});