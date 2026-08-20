const REPLY = {
    get form() { return document.getElementById('comment-form'); },
    get banner() { return document.getElementById('reply-banner'); },
    get parent() { return document.getElementById('reply-parent'); },
    get author() { return document.getElementById('reply-author'); },
    get excerpt() { return document.getElementById('reply-excerpt'); },
    get submit() { return document.getElementById('comment-submit'); },
    get area() { return document.querySelector('#comment-form textarea'); },
};

function setReply(id, author, excerpt) {
    const link = document.getElementById('reply-link');

    REPLY.parent.value = id;
    REPLY.author.textContent = author;
    REPLY.excerpt.textContent = excerpt;
    link.href = `#comment-${id}`;

    REPLY.banner.classList.remove('hidden');
    REPLY.banner.classList.add('flex');

    REPLY.submit.textContent = 'Ответить';
    REPLY.area.placeholder = `Ответить ${author}...`;

    REPLY.form.scrollIntoView({ behavior: 'smooth', block: 'center' });
    setTimeout(() => REPLY.area.focus({ preventScroll: true }), 400);
}

function clearReply() {
    if (!REPLY.form) return;

    REPLY.parent.value = '';
    REPLY.banner.classList.add('hidden');
    REPLY.banner.classList.remove('flex');

    REPLY.submit.textContent = 'Опубликовать';
    REPLY.area.placeholder = 'Напишите отзыв...';
}

document.addEventListener('click', (e) => {
    if (e.target.closest('#reply-cancel')) {
        clearReply();
        return;
    }

    const btn = e.target.closest('[data-reply]');
    if (!btn) return;

    const id = btn.dataset.commentId;
    const text = document.getElementById(`comment-${id}`)
        ?.querySelector('[data-comment-text]')?.textContent.trim() ?? '';

    setReply(id, btn.dataset.author, text.slice(0, 120));
});

document.addEventListener('click', (e) => {
    const link = e.target.closest('#reply-link');
    if (!link) return;

    e.preventDefault();

    const card = document.getElementById(`comment-${REPLY.parent.value}`);
    if (!card) return;

    card.scrollIntoView({ behavior: 'smooth', block: 'center' });

    const box = card.querySelector('div');
    box?.classList.add('ring', 'ring-(--accent)');
    setTimeout(() => box?.classList.remove('ring', 'ring-(--accent)'), 1500);
});