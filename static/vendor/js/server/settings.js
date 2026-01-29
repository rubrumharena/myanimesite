import {ajax_get, ajax_post} from '../utils/ajax.js';

document.addEventListener('DOMContentLoaded', () => {
    const profileButton = document.querySelector('button[data-panel="profile"]');
    if (!profileButton) return;

    profileButton.click();
});


function callSettingPanel() {
    document.addEventListener('click', function (event) {
        const button = event.target.closest('button[data-url][data-panel]');
        if (!button) return;

        event.preventDefault();

        ajax_get(button.dataset.url, {})
            .then(response => {
                toggleActiveButton(button.dataset.panel);
                updatePanelHtml(response);
            });
    });
}

function sendForm() {
    document.addEventListener('submit', function (event) {
        const form = event.target.closest('form[data-setting]');
        console.log(form)
        if (!form) return;

        event.preventDefault();
        const formData = new FormData(form);
        formData.append('form', form.dataset.setting);

        ajax_post(form.action, formData)
            .then(response => {
                updatePanelHtml(response);
            });
    });
}

function toggleActiveButton(activePanel) {
    document
        .querySelectorAll('button[data-panel]')
        .forEach(button => {
            const isActive = button.dataset.panel === activePanel;
            button.classList.toggle('font-bold', isActive);
            button.classList.toggle('border-b-primary', isActive);
            button.classList.toggle('border-b-[0.1rem]', isActive);
        });
}

function updatePanelHtml(response) {
    if (!response?.data?.html) return;
    const panelContainer = document.getElementById('panelContainer');

    if (panelContainer) {
        panelContainer.innerHTML = response.data.html;
        const event = new CustomEvent('panel:updated', {});

        document.dispatchEvent(event);

    }
}

function submitAvatar() {
    const avatarInput = document.getElementById('id_avatar');
    const form = document.getElementById('avatarForm');
    if (!avatarInput || !form) return;

    avatarInput.addEventListener('change', () => {
        if (avatarInput.files.length > 0) {
            form.dispatchEvent(
                new Event('submit', { bubbles: true, cancelable: true })
            );
        }
    });
}

function checkHistory() {
    const url = window.SETTINGS.checkHistoryVisibility;
    const historyToggle = document.getElementById('id_is_history_public');
    const label = historyToggle.closest('label');
    const textSpan = label.querySelector('span');

    historyToggle.addEventListener('change', () => {
        ajax_post(url, {})
            .then(response => {
                const isEnabled = response.data.is_enabled;

                historyToggle.checked = isEnabled;

                textSpan.textContent = isEnabled
                    ? 'История видна другим пользователям'
                    : 'История скрыта';
            })
            .catch(() => {
                historyToggle.checked = !historyToggle.checked;
            });
    });
}


document.addEventListener('panel:updated', function (event) {
    checkHistory();
    submitAvatar();
});


callSettingPanel();
sendForm();

