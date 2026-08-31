import {ajax_get, ajax_post} from '../utils/ajax.js';


document.addEventListener('DOMContentLoaded', () => loadComments());

document.addEventListener('click', redirectPage);

document.addEventListener('submit', postComment);

document.addEventListener('click', likeComment);

document.addEventListener('click', event => {
    const trigger = event.target.closest('[data-open="comment-alert-popup"]');
    if (!trigger) {
        return;
    }

    const popup = document.getElementById(trigger.dataset.open);
    const form = popup?.querySelector('form');
    if (form && trigger.dataset.url) {
        form.setAttribute('action', trigger.dataset.url);
    }
});

document.addEventListener('submit', event => {
    const form = event.target.closest('#comment-alert-popup form');
    if (!form) {
        return;
    }

    event.preventDefault();

    const requestUrl = form.getAttribute('action');

    ajax_post(requestUrl, new FormData(form))
        .then(response => {
            document.getElementById('comment-alert-popup')?.close()
            loadComments();
        });
});

document.addEventListener('comments:reviewUpdated', event => {
    const commentId = event.detail?.commentId ?? null;
    const paginator = document.getElementById('paginator');
    const page = paginator?.dataset.curpage || 1;

    loadComments(`${window.WATCH_PAGE.loadComments}?page=${page}`, commentId);
});

document.addEventListener('change', (event) => {
    const input = event.target;

    if (input.name !== 'comment-filter_by') return;

    const url = input.dataset.url;

    if (!url) return;

    ajax_get(url).then(response => updateCommentsHtml(response));
});


function loadComments(url = null, focusId = null) {
    const requestUrl = url ? url : window.WATCH_PAGE.loadComments;
    ajax_get(requestUrl, {}).then(response => updateCommentsHtml(response, focusId));
}


function updateCommentsHtml(response, focusId = null) {
    if (!response?.data?.html) return;
    const tree = document.getElementById('comment-tree');
    if (!tree) return;

    tree.innerHTML = response.data.html;
    document.dispatchEvent(new CustomEvent('comments:updated', {}));

    if (focusId) focusComment(focusId);
}


function focusComment(id) {
    const card = document.getElementById(`comment-${id}`);
    if (!card) return;

    card.scrollIntoView({behavior: 'smooth', block: 'center'});

    const box = card.querySelector('div');
    box?.classList.add('ring', 'ring-(--accent)');
    setTimeout(() => box?.classList.remove('ring', 'ring-(--accent)'), 1500);
}


function redirectPage(event) {
    const link = event.target.closest('#paginator a');
    if (!link) return;

    event.preventDefault();

    const anchor = document.querySelector('#comments');
    if (anchor) {
        const offset = 350;
        const y = anchor.getBoundingClientRect().top + window.pageYOffset - offset;
        window.scrollTo({top: y, behavior: 'smooth'});
    }

    loadComments(link.href);
}


function postComment(event) {
    const form = event.target;

    if (!form.id.startsWith('comment-form')) return;

    event.preventDefault();

    ajax_post(form.action, new FormData(form))
        .then(response => {
            const commentId = response?.data?.commentId ?? null;
            const page = response?.data?.page ?? currentPage();

            document.dispatchEvent(new CustomEvent('comments:posted'));
            loadComments(`${window.WATCH_PAGE.loadComments}?page=${page}`, commentId);
        });
}

function currentPage() {
    return document.getElementById('paginator')?.dataset.curpage || 1;
}


function likeComment(event) {
    const button = event.target.closest('button');
    const action = button?.getAttribute('data-action');

    if (!action) return;
    const requestData = getCommentsRequestData(button, 'like');
    if (!requestData) return;

    ajax_post(action)
        .then(() => loadComments(requestData.url));
}


function getCommentsRequestData(container, matchName) {
    if (!container.id || !container.id.startsWith(matchName)) {
        return {};
    }

    const paginator = document.getElementById('paginator');
    let curPage = paginator?.dataset.curpage || 1;

    const regex = new RegExp(`^${matchName}-(\\d+)$`);
    const match = container.id.match(regex);
    const id = match ? match[1] : '';
    if (!id) {
        curPage = 1;
    }

    const url = window.WATCH_PAGE.loadComments + `?page=${curPage}`;

    return {
        id,
        url
    };
}