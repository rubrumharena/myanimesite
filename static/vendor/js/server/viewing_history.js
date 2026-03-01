import {ajax_post} from '../utils/ajax.js';


document.addEventListener('click', event => {
    deleteRecord(event);
    toggleVisibility(event)
});




function toggleVisibility(event) {
    const button = event.target.closest('[name="toggle"]');
    if (!button) return;

    ajax_post(button.dataset.url).then(() => toggleHtml(button));
}

function toggleHtml(button) {
    const svgs = button.querySelectorAll('svg');
    svgs.forEach(svg => {
        svg.classList.toggle('hidden');
    });
    const card = button.closest('.primary-card');
    const cover = card?.querySelector('.cover');

    if (cover) {
        cover.classList.toggle('hidden');
    }
}


function deleteRecord(event) {
    const button = event.target.closest('[name="delete"]');
    if (!button) return;

    ajax_post(button.dataset.url).then(() => deleteHtml(button));
}

function deleteHtml(button) {
    const container = button.closest('.primary-card');
    if (container) {
        container.remove();
        const counter = document.getElementById('counter');
        if (counter) {
            const currentValue = parseInt(counter.textContent, 10) || 0;
            counter.textContent = currentValue - 1;
        }
    }
}
