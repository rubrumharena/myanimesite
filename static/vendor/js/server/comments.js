import {ajax_get, ajax_post} from '../utils/ajax.js';


document.addEventListener('DOMContentLoaded', () => loadComments());

document.addEventListener('click', redirectPage);

document.addEventListener('submit', postComment);

document.addEventListener('click', likeComment);


function loadComments(url = null) {
    const requestUrl = url ? url : window.WATCH_PAGE.loadComments;
    ajax_get(requestUrl, {}).then(response => updateCommentsHtml(response));
}


function updateCommentsHtml(response) {
    if (!response?.data?.html) return;
    const tree = document.getElementById('comment-tree');

    if (tree) {
        tree.innerHTML = response.data.html;
        const event = new CustomEvent('comments:updated', {});
        document.dispatchEvent(event);
    }
}


function redirectPage(event) {
    const container = document.querySelector('#comment-tree');
    if (!container) return;

    const link = event.target.closest('a');

    if (!link) return;
    if (!container.contains(link)) return;

    event.preventDefault();
    const anchor = document.querySelector('#comments');
    if (anchor) {
        const offset = 350;

        const y =
            anchor.getBoundingClientRect().top +
            window.pageYOffset -
            offset;

        window.scrollTo({
            top: y,
            behavior: 'smooth'
        });
    }
    const url = link.href;
    loadComments(url);
}


function postComment(event) {
    const form = event.target;

    if (!form.id.startsWith('comment-form')) return;

    event.preventDefault();

    const requestData = getCommentsRequestData(form, 'comment-form');
    if (!requestData) return;

    const data = new FormData(form);
    data.append('parent', requestData.id);
    ajax_post(form.action, data)
        .then(() => loadComments(requestData.url));

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


