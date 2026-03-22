import {ajax_get} from '../utils/ajax.js';
import {dispatchTitlesUpdated} from '../utils/events.js';

document.addEventListener('DOMContentLoaded', function () {
    getSubscriptionHtml('premium-popup');
    getSubscriptionHtml('activated-premium-popup');
});

function getSubscriptionHtml(popup) {
    const button = document.querySelector(`[data-open="${popup}"]`);
    if (!button) return;

    button.addEventListener('click', function () {
        ajax_get(button.dataset.url).then(response => updateHtml(response, popup));
    });
}

function updateHtml(response, popup) {
    if (!response?.data?.html) return;

    const container = document.getElementById(popup);
    if (!container) return;

    container.innerHTML = response.data.html;
}
