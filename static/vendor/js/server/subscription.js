import {ajax_get} from '../utils/ajax.js';
import {dispatchTitlesUpdated} from '../utils/events.js';

document.addEventListener('DOMContentLoaded', getSubscriptionHtml)


function getSubscriptionHtml() {
    const button = document.querySelector('[data-open="premium-popup"]');

    button.addEventListener('click', function () {
        ajax_get(button.dataset.url).then(response => updateHtml(response));
    });
}

function updateHtml(response) {
    if (!response?.data?.html) return;

    const container = document.getElementById('premium-popup');
    if (!container) return;

    container.innerHTML = response.data.html;
}
