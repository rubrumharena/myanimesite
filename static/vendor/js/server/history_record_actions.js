import {ajax_post} from '../utils/ajax.js';

document.addEventListener('click', async event => {
    const button = event.target.closest('button[data-method]');
    if (!button) return;

    const recordId = button.getAttribute('data-record-id');
    const url = button.getAttribute('data-method');

    let method;
    if (url === window.HISTORY.deleteRecord) {
        method = removeContainer;
    } else if (url === window.HISTORY.toggleCompleted) {
        method = toggleVisibility;
    } else {
        return;
    }

    const data = new FormData();
    data.append('record_id', recordId);

    await ajax_post(url, data);
    method(recordId);
    document.dispatchEvent(new CustomEvent('TitlesUpdated'));
});


function toggleVisibility(recordId) {
    const button = document.querySelector(`[data-record-id="${recordId}"]`);
    if (!button) return;

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

function removeContainer(recordId) {
    const button = document.querySelector(`[data-record-id="${recordId}"]`);
    const container = button.closest('.primary-card');
    if (container) {
        container.remove();
    }
}
