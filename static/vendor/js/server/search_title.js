import {ajax_get} from '../utils/ajax.js';
import {dispatchModalContentUpdated, dispatchTitlesUpdated} from '../utils/events.js';

document.addEventListener('DOMContentLoaded', loadTitles);

function loadTitles() {
    const input = document.querySelector('#title-search');
    if (!input) return;

    input.addEventListener('input', function () {
        const searchField = this.value.trim();
        ajax_get(input.dataset.url, {'search': searchField}).then(response => updateHtml(response));
    });
}


function updateHtml(response) {
    if (!response?.data?.html) return;

    const container = document.getElementById('search-content');

    if (!container) return;
    container.innerHTML = response.data.html;
    dispatchModalContentUpdated();
    dispatchTitlesUpdated();
}