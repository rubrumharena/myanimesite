function setupDialog(id) {
    const dialog = document.getElementById(id);
    if (!dialog) return;

    dialog.addEventListener('click', event => {
        if (event.target === dialog) {
            dialog.close();
        }
    });

    document.addEventListener('click', (event) => {
        const button = event.target.closest('[data-open]');
        if (!button) return;

        const dialogId = button.dataset.open;
        const dialog = document.getElementById(dialogId);

        if (dialog) {
            dialog.showModal();
        }
    });


    document.addEventListener('modalContentUpdated', () => {
        const closeButtons = document.querySelectorAll('.close-modal');
        closeButtons.forEach(button => {
            button.addEventListener('click', () => {
                dialog.close();
            });
        });
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
    'folder-popup',
    'alert-popup',
    'collection-popup'
].forEach(setupDialog);
