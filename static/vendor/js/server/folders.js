import {ajax_get, ajax_post} from '../utils/ajax.js';
import {dispatchModalContentUpdated, dispatchTitleAdded} from '../utils/events.js';

document.addEventListener('DOMContentLoaded', loadForm);

document.addEventListener('folders:updated', loadForm);

document.addEventListener('submit', sendForm);


function loadForm() {
    const buttons = document.querySelectorAll(
        'button[data-open="folder-popup"]'
    );
    buttons.forEach(button => {
        button.addEventListener('click', async () => {
            await ajax_get(button.dataset.url).then(response => updateFormHtml(response));
        });
    });
}


function updateFormHtml(response) {
    if (!response?.data?.html) return;
    const popup = document.getElementById('folder-popup');

    if (!popup) return;
    popup.innerHTML = response.data.html;
    popup.showModal();
    dispatchModalContentUpdated();
}


function sendForm(event) {
    const form = event.target;

    if (form.id !== 'folder-form') return;

    event.preventDefault();
    const formData = new FormData(form)
    ajax_post(form.action, formData)
        .then(response => {

            if (response.status === 201) {
                document.getElementById('folder-popup')?.close();
                const titleId = Number(formData.get('title'));
                if (titleId) {
                    dispatchTitleAdded(titleId)
                }
            } else {
                updateFormHtml(response);
            }
        });
}