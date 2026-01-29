export function createErrorBanner(message = 'Проверьте корректность заполнения формы', inputs = [], form=null) {
    document.querySelector('.error-banner')?.remove();

    const banner = document.createElement('div');
    banner.className = 'error-banner text-pink-300 border border-pink-600 bg-pink-900 p-4 rounded-2xl space-y-2 mt-4 transition-opacity duration-500';
    banner.textContent = message;

    if (form) {
        form.parentNode.insertBefore(banner, form);
    }

    inputs.forEach(input => {
        highlightField(input, form);
    });
    removeBanner(banner)
}

function highlightField(input, form) {
    const label = form.querySelector(`label[for='${input.id}']`);
    input.classList.add('border-pink-600', '!text-pink-600', 'focus:border-pink-600');
    label.classList.add('!text-pink-600');
    label.classList.remove('!text-neutral-300')

    const onInput = () => {
        input.classList.remove('border-pink-600', '!text-pink-600', 'focus:border-pink-600');
        label.classList.remove('!text-pink-600');
        label.classList.add('!text-neutral-300')

        const errorContainer = form.querySelector(`[data-error-field='${input.name}']`)
        if (errorContainer) {
            errorContainer.remove();
        }
        input.removeEventListener('input', onInput);
    };
    input.addEventListener('input', onInput);
}

function removeBanner(banner) {
    setTimeout(() => {
        banner.classList.add('opacity-0', 'transition-opacity', 'duration-500');
        setTimeout(() => banner.remove(), 500);}, 5000);
}

function processFormError(formId, errorContainer) {
    const form = document.getElementById(formId);
    if (!form) {
        return;
    }

    let suffix = ''
    if (formId === 'update-folder-form') {
        suffix = 'update-';
    }
    console.log(formId);
    document.querySelectorAll(`.${errorContainer}`).forEach(container => {
        const errorField = container.getAttribute('data-error-field');
        const input = form.querySelector(`[name='${suffix + errorField}']`);

        if (input) {
            highlightField(input, form);
        }
        if (errorContainer === 'error-banner') {
            removeBanner(container)
        }
    });
}

document.addEventListener('DOMContentLoaded', () => {
    processFormError('register-form', 'error-message')
    processFormError('login-form', 'error-message')
    processFormError('password-reset-form', 'error-message')
    processFormError('email-form', 'error-message')

    processFormError('update-folder-form', 'error-banner')
})
