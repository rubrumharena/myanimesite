import {ajax_get, ajax_post} from '../utils/ajax.js';
import {dispatchTitleAdded, dispatchTitleRemoved} from '../utils/events.js';


document.addEventListener('DOMContentLoaded', loadFolders);

document.addEventListener('titles:updated', loadFolders);

document.addEventListener('folders:titleAdded', setLibraryButtonToAdded);

document.addEventListener('folders:titleRemoved', setLibraryButtonToNew);

document.addEventListener('folders:updated', toggleTitle);


function loadFolders() {
    const buttons = document.querySelectorAll(
        'button[popovertarget="library-popover"]'
    );
    const popover = document.getElementById('library-popover');
    if (!popover) {
        console.error('Failed to load library');
        return;
    }

    buttons.forEach(button => {
        button.addEventListener('click', async (event) => {
            buttons.forEach(l => l.style.anchorName = '');
            button.style.anchorName = '--library';
            ajax_get(button.dataset.url).then(response => updatePopoverHtml(response));
        });
    });
}


function updatePopoverHtml(response) {
    if (!response?.data?.html) return;
    const popover = document.getElementById('library-popover');
    if (popover) {
        popover.innerHTML = response.data.html;
    }
    const event = new CustomEvent('folders:updated', {});
    document.dispatchEvent(event);
}


function toggleTitle() {
    const buttons = document.querySelectorAll(
        '[data-action-url][data-reload-url]'
    );

    buttons.forEach(button => {
        button.addEventListener('click', () => {
            ajax_post(button.dataset.actionUrl)
                .then(response => {
                    if (response.data.curCount === 0) {
                        dispatchTitleRemoved(response.data.titleId);
                    } else {
                        dispatchTitleAdded(response.data.titleId);
                    }

                    return ajax_get(button.dataset.reloadUrl);
                })
                .then(response => {
                    updatePopoverHtml(response);
                })
                .then();
        });
    });
}


function setLibraryButtonToNew(event) {
    const titleId = Number(event.detail.titleId);

    const buttons = document.querySelectorAll(
        `[popovertarget="library-popover"][data-title-id="${titleId}"]`
    );

    buttons.forEach(button => {
        button.innerHTML = `
            <svg xmlns="http://www.w3.org/2000/svg" width="18px" height="18px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M12 5l0 14"></path>
                <path d="M5 12l14 0"></path>
            </svg>
            `;
    });
}


function setLibraryButtonToAdded(event) {
    const titleId = Number(event.detail.titleId);

    const buttons = document.querySelectorAll(
        `[popovertarget="library-popover"][data-title-id="${titleId}"]`
    );

    buttons.forEach(button => {
        button.innerHTML = `
            <svg width="25px" height="25px" viewBox="0 0 24 24" id="_24x24_On_Light_Checkmark" data-name="24x24/On Light/Checkmark" xmlns="http://www.w3.org/2000/svg">
                <rect id="view-box" width="24" height="24" fill="#141124" opacity="0"></rect>
                <path id="Shape" d="M5.341,12.247a1,1,0,0,0,1.317,1.505l4-3.5a1,1,0,0,0,.028-1.48l-9-8.5A1,1,0,0,0,.313,1.727l8.2,7.745Z" transform="translate(19 6.5) rotate(90)" fill="white"></path>
            </svg>                        
            `;
    });
}


