const COMPOSE = {
    get form()    { return document.getElementById('comment-form'); },
    get banner()  { return document.getElementById('reply-banner'); },
    get link()    { return document.getElementById('reply-link'); },
    get mode()    { return document.getElementById('reply-mode'); },
    get parent()  { return document.getElementById('reply-parent'); },
    get editId()  { return document.getElementById('edit-id'); },
    get author()  { return document.getElementById('reply-author'); },
    get excerpt() { return document.getElementById('reply-excerpt'); },
    get submit()  { return document.getElementById('comment-submit'); },
    get area()    { return document.querySelector('#comment-form textarea'); },
};

function showBanner(id) {
    COMPOSE.link.href = `#comment-${id}`;
    COMPOSE.banner.classList.remove('hidden');
    COMPOSE.banner.classList.add('flex');

    COMPOSE.form.scrollIntoView({behavior: 'smooth', block: 'center'});
    setTimeout(() => COMPOSE.area.focus({preventScroll: true}), 400);
}

function setReply(id, author, excerpt) {
    resetCompose();

    COMPOSE.parent.value = id;
    COMPOSE.mode.textContent = 'Ответ';
    COMPOSE.author.textContent = author;
    COMPOSE.excerpt.textContent = excerpt;
    COMPOSE.submit.textContent = 'Ответить';
    COMPOSE.area.placeholder = `Ответить ${author}...`;

    showBanner(id);
}

function setEdit(id) {
    const card = document.getElementById(`comment-${id}`);
    const node = card?.querySelector('[data-comment-text]');
    if (!node) return;

    resetCompose();

    COMPOSE.editId.value = id;
    COMPOSE.mode.textContent = 'Редактирование';
    COMPOSE.author.textContent = '';
    COMPOSE.excerpt.textContent = node.textContent.trim().slice(0, 120);
    COMPOSE.submit.textContent = 'Сохранить';
    COMPOSE.area.placeholder = 'Измените комментарий...';

    COMPOSE.area.value = node.dataset.raw ?? node.textContent.trim();
    COMPOSE.area.dispatchEvent(new Event('input', {bubbles: true}));

    showBanner(id);
}

function resetCompose() {
    if (!COMPOSE.form) return;

    COMPOSE.parent.value = '';
    COMPOSE.editId.value = '';
    COMPOSE.banner.classList.add('hidden');
    COMPOSE.banner.classList.remove('flex');

    COMPOSE.submit.textContent = 'Опубликовать';
    COMPOSE.area.placeholder = 'Напишите отзыв...';
}

document.addEventListener('click', event => {
    if (event.target.closest('#reply-cancel')) {
        resetCompose();
        COMPOSE.area.value = '';
        COMPOSE.area.dispatchEvent(new Event('input', {bubbles: true}));
        return;
    }

    const edit = event.target.closest('[data-edit-feedback]');
    if (edit) {
        edit.closest('details')?.removeAttribute('open');
        setEdit(edit.dataset.editFeedback);
        return;
    }

    const reply = event.target.closest('[data-reply]');
    if (!reply) return;

    reply.closest('details')?.removeAttribute('open');

    const id = reply.dataset.commentId;
    const text = document.getElementById(`comment-${id}`)
        ?.querySelector('[data-comment-text]')?.textContent.trim() ?? '';

    setReply(id, reply.dataset.author, text.slice(0, 120));
});

document.addEventListener('click', event => {
    const link = event.target.closest('#reply-link');
    if (!link) return;

    event.preventDefault();

    const id = COMPOSE.parent.value || COMPOSE.editId.value;
    const card = document.getElementById(`comment-${id}`);
    if (!card) return;

    card.scrollIntoView({behavior: 'smooth', block: 'center'});

    const box = card.querySelector('div');
    box?.classList.add('ring', 'ring-(--accent)');
    setTimeout(() => box?.classList.remove('ring', 'ring-(--accent)'), 1500);
});