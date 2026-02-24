import {ajax_get} from '../utils/ajax.js';
import {dispatchTitlesUpdated} from '../utils/events.js';

document.addEventListener('DOMContentLoaded', function () {
    getChartByClick();
    getChartByDefault();
});


function getChartByClick() {
    const chartButtons = document.querySelectorAll('[data-chart]');

    chartButtons.forEach(button => {
        button.addEventListener('click', function () {
            ajax_get(button.dataset.url).then(response => updateHtml(response));
        });
    });
}


function getChartByDefault() {
    ajax_get(window.INDEX.popularChartUrl).then(response => updateHtml(response));
}


function updateHtml(response) {
    if (!response?.data?.html) return;

    const container = document.getElementById('chart');
    if (!container) return;

    container.innerHTML = response.data.html;
    dispatchTitlesUpdated();
}
