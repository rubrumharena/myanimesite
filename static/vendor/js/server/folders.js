import {ajax_get, ajax_post} from '../utils/ajax.js';
import {createErrorBanner} from '../client/validator.js';
import {displayFolders, toggleFolderButton} from '../client/folders.js';

document.addEventListener('DOMContentLoaded', loadFolders);
document.getElementById('create-folder-form').addEventListener('submit', createFolder);
document.getElementById('user-library-popover').addEventListener('change', updateFolder);
document.addEventListener('TitlesUpdated', loadFolders);


function createFolder(event) {
    const form = event.target;

    if (form.id !== 'create-folder-form') {
        return;
    }
    const titleId = document.querySelector(`button[data-target='create-folder-popup']`).getAttribute('data-title-id');
    event.preventDefault();

    const data = new FormData(form);
    if (titleId) {
        data.append('title_id', titleId);
    }

    const url = window.COMMON.createFolder;
    ajax_post(url, data).then(response => renderResponse(response, form, titleId));
}

function updateFolder(event) {
    const folderMethods = window.COMMON.folderHelper.folder_methods;
    const button = event.target;
    const url = COMMON.updateFolder;
    const data = new FormData();
    const titleId = button.getAttribute('data-title-id');
    data.append('folder_id', button.getAttribute('data-folder-id'));
    data.append('title_id', titleId);

    const checked = button.checked;

    if (checked) {
        data.append('method', folderMethods.ADD);
    } else {
        data.append('method', folderMethods.DELETE);
    }

    ajax_post(url, data).then(() => {
        if (button.getAttribute('data-no-toggle') === 'true') {
            return;
        }
        toggleFolderButton(titleId);
    });
}


function loadFolders() {
    const buttons = document.querySelectorAll('button[data-target="user-library-popover"]');
    buttons.forEach(button => {
        button.addEventListener('click', function () {
            const titleId = this.getAttribute('data-title-id');
            const data = {'title_id': titleId};
            const url = window.COMMON.getFolders;

            ajax_get(url, data).then(response => displayFolders(response.data, titleId));
        });
    });
}

function renderResponse(response, form, titleId) {
    if (response.status === 200) {
        toggleFolderButton(titleId, true);
    } else {
        Object.entries(response.data.errors).forEach(([fieldName, messages]) => {
            const input = form.querySelector(`[name='${fieldName}']`);
            if (input) {
                messages.forEach(message => {
                    createErrorBanner(message, [input], form);
                });
            }
        });
    }
    if (!titleId && response.status === 200) {
        window.location.reload()
    }
}
