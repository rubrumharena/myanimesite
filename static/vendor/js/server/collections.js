import {ajax_get} from '../utils/ajax.js';
import {dispatchModalContentUpdated} from '../utils/events.js';

const POPUP_ID = 'collection-popup';

document.addEventListener('click', (event) => {
    const opener = event.target.closest('[data-open="collection-popup"]');
    if (!opener?.dataset.url) return;
    ajax_get(opener.dataset.url).then(updateHtml);
});

document.addEventListener('change', (event) => {
    const input = event.target;
    if (input.name !== 'collections') return;

    const url = input.dataset.url;
    if (!url) return;

    ajax_get(url).then(updateHtml);
});

function updateHtml(response) {
    const html = response?.data?.html;
    if (!html) return;

    const popup = document.getElementById(POPUP_ID);
    if (!popup) return;

    popup.innerHTML = html;
    dispatchModalContentUpdated();
}