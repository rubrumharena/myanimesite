document.addEventListener('modalContentUpdated', previewFolderImage);


function previewFolderImage() {
    const form = document.getElementById('folder-form');
    if (!form) {
        return;
    }

    const input = form.querySelector('input[type="file"]');
    const previewContainer = form.querySelector('#preview-container');
    const deleteButton = form.querySelector('.delete-image');

    if (!(input && deleteButton)) {
        return;
    }

    input.addEventListener('change', function () {
        const file = this.files[0];

        if (file) {
            createPreview(file, previewContainer);
        }
    });

    deleteButton.addEventListener('click', function () {
        const preview = form.querySelector('#preview');
        if (preview) {
            preview.src = '';
        }

        input.value = '';
    });
}

function createPreview(file, container) {
    const img = document.createElement('img');
    img.id = 'preview';
    img.className = 'h-full w-full object-cover object-center rounded-2xl border border-[#2b2c2d]';

    if (file instanceof File) {
        img.src = URL.createObjectURL(file);
    } else if (typeof file === 'string') {
        img.src = file;
    } else {
        return;
    }

    container.innerHTML = '';
    container.appendChild(img);
}

