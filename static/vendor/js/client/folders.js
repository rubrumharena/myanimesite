export function displayFolders(folders, titleId) {
    const favoriteFolder = window.COMMON.folderHelper.reserved_folders.favorites;
    console.log(folders);
    const data = folders.items;
    let foldersContainer = document.getElementById('user-folders');
    let content = '';

    document.querySelector(`button[data-target='create-folder-popup']`).setAttribute('data-title-id', titleId);

    for (const folder of data) {
        const checked = folder.folder_titles.includes(Number(titleId));
        if (folder.name === favoriteFolder) {
            const savedInput = document.getElementById('favorites');

            savedInput.checked = checked;
            savedInput.setAttribute('data-folder-id', folder.id);
            savedInput.setAttribute('data-title-id', titleId);
            continue;
        }

        content +=
            `
                <li>
                    <label for="folder-${folder.id}" class="group popover-button gap-1.5 select-none flex items-center">
                        <input id="folder-${folder.id}" data-folder-id="${folder.id}" data-title-id="${titleId}" type="checkbox" class="peer hidden" ${checked ? 'checked' : ''}>
          
                        <svg fill="none" width="1.4rem" height="1.4rem" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                            <rect width="24" height="24"/>
                            <path class="group-has-[:checked]:fill-primary transition-colors duration-200" fill="currentColor" fill-rule="evenodd" clip-rule="evenodd" d="M2 12C2 6.47715 6.47715 2 12 2C17.5228 2 22 6.47715 22 12C22 17.5228 17.5228 22 12 22C6.47715 22 2 17.5228 2 12ZM15.7071 9.29289C16.0976 9.68342 16.0976 10.3166 15.7071 10.7071L12.0243 14.3899C11.4586 14.9556 10.5414 14.9556 9.97568 14.3899L8.29289 12.7071C7.90237 12.3166 7.90237 11.6834 8.29289 11.2929C8.68342 10.9024 9.31658 10.9024 9.70711 11.2929L11 12.5858L14.2929 9.29289C14.6834 8.90237 15.3166 8.90237 15.7071 9.29289Z"/>
                        </svg>
                        ${folder.name}
                    </label>
                </li>
            `;
    }
    foldersContainer.innerHTML = content;
}

export function toggleFolderButton(titleId, adding = false) {
    let checkedCount = 1;
    if (!adding) {
        checkedCount = document.querySelectorAll('#user-library-popover input[type="checkbox"]:checked').length;
    }

    let inner = '';
    if (checkedCount === 0) {
        inner =
            `
            <svg xmlns="http://www.w3.org/2000/svg" width="18px" height="18px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M12 5l0 14"></path>
                <path d="M5 12l14 0"></path>
            </svg>
            `;
    } else if (checkedCount === 1) {
        inner =
            `
            <svg width="25px" height="25px" viewBox="0 0 24 24" id="_24x24_On_Light_Checkmark" data-name="24x24/On Light/Checkmark" xmlns="http://www.w3.org/2000/svg">
                <rect id="view-box" width="24" height="24" fill="#141124" opacity="0"></rect>
                <path id="Shape" d="M5.341,12.247a1,1,0,0,0,1.317,1.505l4-3.5a1,1,0,0,0,.028-1.48l-9-8.5A1,1,0,0,0,.313,1.727l8.2,7.745Z" transform="translate(19 6.5) rotate(90)" fill="white"></path>
            </svg>
            `;
    }
    if (inner) {
        const buttons = document.querySelectorAll(`[data-title-id="${titleId}"][data-target="user-library-popover"]`);
        buttons.forEach(button => {
            button.innerHTML = inner;
        });
    }
}


export function chooseFolderButton(title, userTitles) {
    let iconInner = '';

    if (userTitles.includes(Number(title.id))) {
        iconInner =
            `
            <svg width="25px" height="25px" viewBox="0 0 24 24" id="_24x24_On_Light_Checkmark" data-name="24x24/On Light/Checkmark" xmlns="http://www.w3.org/2000/svg">
                <rect id="view-box" width="24" height="24" fill="#141124" opacity="0"></rect>
                <path id="Shape" d="M5.341,12.247a1,1,0,0,0,1.317,1.505l4-3.5a1,1,0,0,0,.028-1.48l-9-8.5A1,1,0,0,0,.313,1.727l8.2,7.745Z" transform="translate(19 6.5) rotate(90)" fill="white"></path>
            </svg>                        
            `;
    } else {
        iconInner =
            `
            <svg xmlns="http://www.w3.org/2000/svg" width="18px" height="18px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M12 5l0 14"></path>
                <path d="M5 12l14 0"></path>
            </svg>
            `;
    }
    return `
           <button title='Добавить "${title.name}" в коллекцию' class="add flex-center" data-title-id="${title.id}" data-target="user-library-popover">
               ${iconInner}  
           </button>
           `;
}


function previewFolderImage(formId) {
    const form = document.getElementById(formId);
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

export function createPreview(file, container) {
    const img = document.createElement('img');
    img.id = 'preview';
    img.className = 'h-full w-full object-cover object-center rounded-2xl border border-[#2b2c2d]';

    if (file instanceof File) {
        img.src = URL.createObjectURL(file);
    } else if (typeof file === 'string') {
        img.src = file;
    } else {
        console.error('Невозможно создать превью', file);
        return;
    }

    // очищаем контейнер и добавляем новое превью
    container.innerHTML = '';
    container.appendChild(img);
}



previewFolderImage('update-folder-form');
previewFolderImage('create-folder-form');
