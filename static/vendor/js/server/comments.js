import {ajax_get, ajax_post} from '../utils/ajax.js';
import {displayComments} from '../client/comments.js';

document.addEventListener('submit', function (event) {
    const form = event.target;
    if (form.id && form.id.startsWith('comment-form')) {
        event.preventDefault();
        postComment(form);
    }
});

document.addEventListener('click', function (event) {
    const button = event.target;
    if (button.id && button.id.startsWith('like-')) {
        likeComment(button);
    }
});

document.addEventListener('DOMContentLoaded', async function () {

    await loadComments(true); // ждем загрузки

    // Теперь отправляем событие
    const event = new CustomEvent('commentsLoaded');
    document.dispatchEvent(event);
});

document.addEventListener('commentsLoaded', function () {
    initializeCommentsPagination(); // вместо loadComments
});


async function postComment(form) {
    const urlGet = window.WATCH_PAGE.getComments;
    const idData = form.id.split('-');

    let commentId = '';
    let getData = {};

    if (idData.length > 2) {
        commentId = idData[2];
        const pageNumber = document.querySelector('.active-page')?.getAttribute('data-page') || 1;
        getData = {page: pageNumber};
    } else {
        getData = {page: 1};
    }

    const data = new FormData(form);
    data.append('parent', commentId);
    data.append('title', window.WATCH_PAGE.titleId);

    const urlPost = window.WATCH_PAGE.postComment;

    const commentInput = form.querySelector('textarea');
    if (commentInput) commentInput.value = '';

    try {
        await ajax_post(urlPost, data);
        const response = await ajax_get(urlGet, getData);
        displayComments(response);
        initializeCommentsPagination(); // переинициализируем кнопки
    } catch (error) {
        console.error('Error posting comment:', error);
    }
}


async function likeComment(button) {
    const itemId = button.id.split('like-')[1];
    const url = window.WATCH_PAGE.likeComment;

    if (!url) return;

    const data = new FormData();
    data.append('comment_id', itemId);

    try {
        await ajax_post(url, data);
        const urlGet = window.WATCH_PAGE.getComments;
        const pageNumber = document.querySelector('.active-page')?.getAttribute('data-page') || 1;
        const response = await ajax_get(urlGet, {page: pageNumber});
        displayComments(response);
        initializeCommentsPagination(); // переинициализируем кнопки
    } catch (error) {
        console.error('Error liking comment:', error);
    }
}

async function loadComments(loadInitial = false) {
    const url = window.WATCH_PAGE.getComments;

    if (loadInitial) {
        // Загружаем первую страницу при инициализации
        try {
            const response = await ajax_get(url, {page: 1});
            displayComments(response);
        } catch (error) {
            console.error('Error loading comments:', error);
        }
    }

    // Инициализируем пагинацию
    initializeCommentsPagination();
}

function initializeCommentsPagination() {
    const url = window.WATCH_PAGE.getComments;
    const pageButtons = document.querySelectorAll('[data-page]');

    console.log('Found page buttons:', pageButtons.length);

    pageButtons.forEach((button) => {
        const newButton = button.cloneNode(true);
        button.parentNode.replaceChild(newButton, button);

        newButton.addEventListener('click', async function () {
            const anchor = document.getElementById('comments');
            if (anchor) {
                const offset = anchor.getBoundingClientRect().top + window.scrollY - 100;
                window.scrollTo({top: offset, behavior: 'smooth'});
            }

            const pageNumber = this.getAttribute('data-page');
            const data = {'page': pageNumber};

            try {
                const response = await ajax_get(url, data);
                displayComments(response);
                initializeCommentsPagination(); // переинициализируем после обновления
            } catch (error) {
                console.error('Error loading page:', error);
            }
        });
    });
}