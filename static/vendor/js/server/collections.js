import {ajax_get} from '../utils/ajax.js';
import {dispatchModalContentUpdated} from '../utils/events.js';

document.addEventListener('DOMContentLoaded', loadCollections);

document.addEventListener('modalContentUpdated', loadFromPopup);

function loadCollections() {
    const collection = document.querySelector('[data-open="collection-popup"]');

    if (!collection) return;

    collection.addEventListener('click', function () {
        ajax_get(collection.dataset.url).then(response => updateHtml(response));
    });
}

function loadFromPopup() {
    const popup = document.getElementById('collection-popup');
    if (!popup) return;
    const buttons = popup.querySelectorAll('[data-url]');

    buttons.forEach((button) => {
        button.addEventListener('click', function () {
            ajax_get(button.dataset.url).then(response => updateHtml(response));
        });
    });
}


function updateHtml(response) {
    if (!response?.data?.html) return;
    const popup = document.getElementById('collection-popup');

    if (!popup) return;
    popup.innerHTML = response.data.html;
    dispatchModalContentUpdated();
}