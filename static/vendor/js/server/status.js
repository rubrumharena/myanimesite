import {ajax_post} from '../utils/ajax.js';


document.addEventListener('change', (event) => {
    const input = event.target;

    if (input.name !== 'status' || !input.closest('#status-form')) return;

    const url = input.dataset.url;
    if (!url) return;

    ajax_post(url);
});