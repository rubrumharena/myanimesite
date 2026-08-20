const WRAPS = {
    bold:    ['**', '**', 'жирный текст'],
    italic:  ['*', '*', 'курсив'],
    spoiler: ['||', '||', 'спойлер'],
    quote:   ['> ', '', 'цитата'],
    link:    ['[', '](https://)', 'текст ссылки'],
};

function applyFormat(type) {
    const area = document.querySelector('#comment-form textarea');
    if (!area || !WRAPS[type]) return;

    const [before, after, hint] = WRAPS[type];
    const { selectionStart: start, selectionEnd: end, value } = area;
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
        area.dispatchEvent(new Event('input', { bubbles: true }));
        return;
    }

    const inner = selected || hint;
    area.value = value.slice(0, start) + before + inner + after + value.slice(end);
    area.focus();

    if (selected) {
        area.setSelectionRange(start + before.length, start + before.length + inner.length);
    } else {
        area.setSelectionRange(start + before.length, start + before.length + hint.length);
    }

    area.dispatchEvent(new Event('input', { bubbles: true }));
}

document.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-format]');
    if (!btn) return;
    e.preventDefault();
    applyFormat(btn.dataset.format);
});

document.addEventListener('keydown', (e) => {
    if (!e.ctrlKey && !e.metaKey) return;
    if (!e.target.matches('#comment-form textarea')) return;

    const key = e.key.toLowerCase();
    if (key === 'b') { e.preventDefault(); applyFormat('bold'); }
    if (key === 'i') { e.preventDefault(); applyFormat('italic'); }
});