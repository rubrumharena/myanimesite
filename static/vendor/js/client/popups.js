import {createPreview} from './folders.js';

function showPopup(targetPopup) {
    const buttons = document.querySelectorAll(`[data-target='${targetPopup}']`);
    const popup = document.getElementById(targetPopup);
    if (!popup) return;

    const popupContent = popup.querySelector('.modal-content');
    const popovers = document.querySelectorAll('[id$="-popover"]');
    const form = popup.querySelector('form');


    buttons.forEach(button => {
        button.addEventListener('click', () => {
            popovers.forEach(popover => {
                popover.classList.add('hidden');
            })
            if (form) {
                setInitials(form);

                clearHighlights(form);
            }
            togglePopup(popup);
        });
    });
    if (!popup._hasHandlers) {
        popupContent.addEventListener('click', event => {
            event._isClickWithinModal = true;
        });
        popup.addEventListener('click', event => {
            if (event._isClickWithinModal) return;
            clearInputs(popup)
            togglePopup(popup);
        });

        popup.querySelectorAll('[data-action-close]').forEach(closeButton => {
            closePopup('click', closeButton, popup);
        });

        window.addEventListener('keydown', (event) => {
            closePopup('Escape', event, popup);
        });

        const form = popup.querySelector('form')
        if (form) {
            form.addEventListener('submit', (event) => {
                setTimeout(() => {
                    const hasError = popup.querySelectorAll('.error-banner').length > 0;

                    if (hasError) {
                        return;
                    }
                    clearInputs(popup);
                    togglePopup(popup);
                }, 300);
            });
        }

        popup._hasHandlers = true; // чтобы не навесить повторно
    }
}

function closePopup(action, event=null, popup) {
    if (action === 'Escape' && event.key === action && popup.classList.contains('visible')) {
        clearInputs(popup);
        togglePopup(popup);
    }
    else if (action === 'click') {
        event.addEventListener(action, () => {
            clearInputs(popup);
            togglePopup(popup);
        });
    }
}

function togglePopup(popup) {
    const body = document.body;

    popup.classList.toggle('visible');
    popup.classList.toggle('invisible');
    body.classList.toggle('overflow-y-hidden');
    body.classList.toggle('overflow-y-auto');
}

function clearInputs(popup) {
    if (popup.getAttribute('data-clean') === 'false') {
        return;
    }

    const inputs = popup.querySelectorAll('input');
    const textarea = popup.querySelector('textarea');
    const image = popup.querySelector('#preview');

    inputs.forEach(input => {
        if (input.name === 'csrfmiddlewaretoken') {
            return;
        }

        if (input.type === 'checkbox' || input.type === 'radio') {
            input.checked = false;
        } else {
            input.value = '';
        }
    });

    if (textarea) textarea.value = '';

    if (image) image.remove();
}

function clearHighlights(form) {
    form.querySelectorAll('input').forEach(input => {
        input.classList.remove('border-pink-600', '!text-pink-600', 'focus:border-pink-600');
    });
    form.querySelectorAll('label').forEach(label => {
        label.classList.remove('!text-pink-600');
        label.classList.remove('!text-neutral-300');
    });
    form.querySelectorAll('.error-banner').forEach(banner => {
        banner.remove();
    });
}

function setInitials(form) {
    if (!form) return;
    const inputs = form.querySelectorAll('input, textarea');
    inputs.forEach(input => {
        let initial = input.getAttribute('data-initial')
        if (input.type === 'file') {
            const previewContainer = form.querySelector('#preview-container');
            const preview = previewContainer.querySelector('#preview');
            if (!preview) {
                createPreview(initial, previewContainer);
            }
            else {
                preview.src = initial;
            }

            input.value = '';
            return;
        }
        if (initial && input) {
            if (input.type === 'radio' || input.type === 'checkbox') {
                if (initial === 'True') {
                    input.checked = true;
                } else {
                    input.removeAttribute('checked');
                }
            }
            else {
                input.value = initial;
            }
        }
    })
}




showPopup('search-popup');
showPopup('create-folder-popup');
showPopup('collections-popup');
showPopup('update-folder-popup');
showPopup('alert-popup');






