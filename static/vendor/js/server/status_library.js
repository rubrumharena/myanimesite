import {ajax_get} from '../utils/ajax.js';
import {dispatchTitlesUpdated} from '../utils/events.js';


document.addEventListener('DOMContentLoaded', () => loadLibrary());

document.addEventListener('click', redirectPage);

document.addEventListener('change', (event) => {

    const input = event.target;
    console.log('change', input.name)
    if (input.name !== 'tab') return;

    const url = input.dataset.url;
    console.log(input.dataset.url)
    if (!url) return;

    ajax_get(url).then(response => updateHtml(response));
});


function loadLibrary(url = null) {
    const requestUrl = url ? url : window.PROFILE.loadLibrary;
    ajax_get(requestUrl, {}).then(response => updateHtml(response));
}


function updateHtml(response) {
    if (!response?.data?.html) return;
    console.log(response.data.html)
    const container = document.getElementById('history');

    if (container) {
        container.innerHTML = response.data.html;
        dispatchTitlesUpdated()
    }
}


function redirectPage(event) {
    const link = event.target.closest('#paginator a');
    if (!link) return;

    event.preventDefault();

    const anchor = document.querySelector('#history');
    if (anchor) {
        const offset = 350;
        const y = anchor.getBoundingClientRect().top + window.pageYOffset - offset;
        window.scrollTo({top: y, behavior: 'smooth'});
    }

    loadLibrary(link.href);
}


