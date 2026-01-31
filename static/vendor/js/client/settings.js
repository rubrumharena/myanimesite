import {ajax_post} from '../utils/ajax.js';


function displayEmailSave() {
    const container = document.getElementById('emailForm');

    if (!container) {
        return;
    }

    const saveButton = container.querySelector('#saveEmail');
    const input = container.querySelector('#id_email');

    if (!saveButton || !input) {
        return;
    }


    let originalEmail = '';
    let verified = false;
    if (saveButton.classList.contains('hidden')) {
        verified = true;
    }

    originalEmail = input.value.trim();
    container.addEventListener('input', (event) => {
        if (event.target.id === 'id_email') {
            saveButton.innerHTML = 'Сохранить';
            saveButton.classList.remove('hidden');
            const currentValue = event.target.value.trim();
            if (currentValue === originalEmail) {
                if (verified) {
                    saveButton.classList.toggle('hidden');
                } else {
                    saveButton.innerHTML = 'Подтвердить';
                }
            }

        }
    });

}

document.addEventListener('panel:updated', function (event) {
    displayEmailSave();
});



