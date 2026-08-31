const WRAPS = {
    bold:    ['**', '**', 'жирный текст'],
    italic:  ['*', '*', 'курсив'],
    spoiler: ['||', '||', 'спойлер'],
    quote:   ['> ', '', 'цитата'],
    link:    ['[', '](https://)', 'текст ссылки'],
};

function applyFormat(area, type) {
    if (!area || !WRAPS[type]) return;

    const [before, after, hint] = WRAPS[type];
    const {selectionStart: start, selectionEnd: end, value} = area;
    const selected = value.slice(start, end);

    if (type === 'quote') {
        const lineStart = value.lastIndexOf('\n', start - 1) + 1;
        const alreadyQuoted = value.slice(lineStart, lineStart + 2) === '> ';

        if (alreadyQuoted) {
            area.value = value.slice(0, lineStart) + value.slice(lineStart + 2);
            area.setSelectionRange(start - 2, end - 2);
        } else {
            area.value = value.slice(0, lineStart) + '> ' + value.slice(lineStart);
            area.setSelectionRange(start + 2, end + 2);
        }

        area.focus();
        area.dispatchEvent(new Event('input', {bubbles: true}));
        return;
    }

    const inner = selected || hint;
    area.value = value.slice(0, start) + before + inner + after + value.slice(end);
    area.focus();
    area.setSelectionRange(start + before.length, start + before.length + inner.length);
    area.dispatchEvent(new Event('input', {bubbles: true}));
}

function fieldFor(element) {
    return element.closest('[data-editor]')?.querySelector('textarea') ?? null;
}

document.addEventListener('click', event => {
    const button = event.target.closest('[data-format]');
    if (!button) return;

    event.preventDefault();
    applyFormat(fieldFor(button), button.dataset.format);
});

document.addEventListener('keydown', event => {
    if (!event.ctrlKey && !event.metaKey) return;

    const area = event.target;
    if (!(area instanceof HTMLTextAreaElement) || !area.closest('[data-editor]')) return;

    const key = event.key.toLowerCase();
    if (key === 'b') {
        event.preventDefault();
        applyFormat(area, 'bold');
    }
    if (key === 'i') {
        event.preventDefault();
        applyFormat(area, 'italic');
    }
});