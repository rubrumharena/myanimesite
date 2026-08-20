const COLORS = {
    'not-watched': 'var(--color-neutral-400)',
    'current':     'var(--color-cyan-400)',
    'planned':     'var(--color-pink-500)',
    'watched':     'var(--color-green-500)',
    'skipped':     'var(--color-red-500)',
};

const filter = document.getElementById('library-filter');
const summary = filter.querySelector('summary');
const labelEl = filter.querySelector('.library-filter__label');

function apply(input) {
    const color = COLORS[input.dataset.chart];
    summary.style.setProperty('color', color, 'important');
    summary.style.setProperty('border-color', color, 'important');
    summary.style.background = `color-mix(in oklab, ${color} 10%, transparent)`;
    labelEl.style.setProperty('color', color, 'important');
    labelEl.textContent = filter
        .querySelector(`label[for="${input.id}"]`)
        .firstChild.textContent.trim();
}

filter.addEventListener('change', (e) => {
    apply(e.target);
    filter.open = false;
});

apply(filter.querySelector('input:checked'));

document.addEventListener('click', (e) => {
    if (!filter.contains(e.target)) filter.open = false;
});