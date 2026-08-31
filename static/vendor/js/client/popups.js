document.addEventListener('click', event => {
    const opener = event.target.closest('[data-open]');
    if (opener) {
        const dialog = document.getElementById(opener.dataset.open);
        if (dialog && !dialog.open) {
            document.querySelectorAll('dialog[open]').forEach(d => {
                if (d !== dialog) d.close();
            });
            dialog.showModal();
        }
        return;
    }

    const closer = event.target.closest('.close-modal');
    if (closer) {
        closer.closest('dialog')?.close();
    }
});

document.addEventListener('click', event => {
    const trigger = event.target.closest('[popovertarget]');
    if (!trigger) return;

    const popover = document.getElementById(trigger.getAttribute('popovertarget'));
    if (!popover) return;

    const dialog = document.querySelector('dialog[open]');
    if (dialog && !dialog.contains(popover)) {
        popover.dataset.movedToDialog = '1';
        dialog.append(popover);
    }
}, true);

document.addEventListener('toggle', event => {
    const popover = event.target;
    if (!(popover instanceof HTMLElement) || !popover.hasAttribute('popover')) return;
    if (event.newState !== 'closed') return;

    if (popover.dataset.movedToDialog) {
        delete popover.dataset.movedToDialog;
        document.body.append(popover);
    }
}, true);

document.addEventListener('scroll', event => {
    const popover = document.getElementById('library-popover');
    if (!popover?.matches(':popover-open')) return;
    if (event.target instanceof Node && popover.contains(event.target)) return;

    popover.hidePopover();
}, {capture: true, passive: true});

function setupDialog(id) {
    const dialog = document.getElementById(id);
    if (!dialog) return;

    dialog.addEventListener('click', event => {
        if (event.target === dialog) dialog.close();
    });

    dialog.addEventListener('close', () => {
        document.body.classList.remove('overflow-hidden');
    });

    const originalShowModal = dialog.showModal.bind(dialog);
    dialog.showModal = function () {
        document.body.classList.add('overflow-hidden');
        originalShowModal();
    };

    return dialog;
}

[
    'activated-premium-popup',
    'premium-popup',
    'search-popup',
    'folder-popup',
    'folder-alert-popup',
    'account-alert-popup',
    'comment-alert-popup',
    'subscription-alert-popup',
    'collection-popup',
    'lightbox',
    'review-view-popup',
    'review-edit-popup',
].forEach(setupDialog);