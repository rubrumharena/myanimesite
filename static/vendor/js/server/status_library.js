import {ajax_get} from '../utils/ajax.js';
import {dispatchTitlesUpdated} from '../utils/events.js';


document.addEventListener('DOMContentLoaded', () => loadLibrary());

document.addEventListener('comments:reviewUpdated', () => loadLibrary());

document.addEventListener('click', redirectPage);

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

document.addEventListener('change', (event) => {
    const input = event.target;
        console.log(input.name)
    if (input.name !== 'statuses') return;

    const url = input.dataset.url;
    if (!url) return;

    ajax_get(url).then(response => updateHtml(response));
});


function loadLibrary(url = null) {
    const requestUrl = url ? url : window.PROFILE.loadLibrary;
    ajax_get(requestUrl, {}).then(response => updateHtml(response));
}


function updateHtml(response) {
    if (!response?.data?.html) return;
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


