import {ajax_get, ajax_post} from '../utils/ajax.js';
import {dispatchReviewUpdated} from '../utils/events.js';

const REMOTE_MODALS = new Set(['review-view-popup', 'review-edit-popup']);

document.addEventListener('click', event => {
    const button = event.target.closest('button[data-open][data-url]');
    if (!button || !REMOTE_MODALS.has(button.dataset.open)) return;

    const modal = document.getElementById(button.dataset.open);
    if (!modal) return;

    modal.innerHTML = '';
    ajax_get(button.dataset.url).then(response => {
        if (response?.data?.html) modal.innerHTML = response.data.html;
    });
});

document.addEventListener('submit', sendForm);

function sendForm(event) {
    const form = event.target;
    const modal = document.getElementById('review-edit-popup');

    if (!modal) return;
    if (form.id !== 'review-edit-form') return;

    event.preventDefault();
    const formData = new FormData(form);
    ajax_post(form.action, formData)
        .then(response => {
            if (response?.data?.commentId) {
                dispatchReviewUpdated(response.data.commentId);
                modal.close();
            } else if (response?.data?.html) {
                modal.innerHTML = response.data.html;
            }
        });
}