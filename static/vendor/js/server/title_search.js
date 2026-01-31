import { ajax_get } from '../utils/ajax.js';
import {chooseFolderButton} from '../client/folders.js';
import {loadUserTitles} from '../utils/server_data.js';


const popup = document.getElementById('search-popup');

function getSearchResults() {
    const input = popup.querySelector('#title-search');
    console.log(input);

    input.addEventListener('input', function() {
        const searchField = this.value.trim()
        ajax_get(window.COMMON.search, {'search_field': searchField}).then(response => displaySearchResult(response.data, searchField));
    });
}

async function displaySearchResult(data, searchField) {
    const titles = data.items
    console.log(data.items)
    const searchResult = popup.querySelector('#title-search-result');
    const annotation = popup.querySelector('#title-search-annotation');

    let content = '';
    let banner = popup.querySelector('.nothing-found');

    if (!searchField) {
        banner.classList.remove('hidden');
        annotation.classList.add('hidden');
        searchResult.innerHTML = content;
        return
    } else {
        banner.classList.add('hidden');
        annotation.classList.remove('hidden');
        annotation.querySelector('span').innerText = searchField;
    }
    const userTitles = (await loadUserTitles()).items;
    console.log(userTitles);
    if (titles.length > 0) {
        for (const title of titles) {
            content +=
                `
                <li class="h-fit w-full gap-4 flex">
                    <a href="${title.url}" class="shrink-0" title='Смотреть онлайн "${title.name}"'>
                        <img class="rounded-lg !h-12 w-12 object-cover object-center" src="${title.image}" alt="title">
                    </a>
                    <div class="flex items-center justify-between pb-6 border-b-[0.09rem] border-b-[#2b2c2d] w-full">
                        <div class="max-w-96">
                            <div class="flex items-center w-[500px]">
                                <h4 class="text-[1.1rem] line-clamp-2 text-ellipsis w-full font-bold leading-6">
                                    <a href="${title.url}" title='Смотреть онлайн "${title.name}"'>${title.name}</a>
                                </h4>
                            </div>
                            <div class="text-sm  break-words mt-1 w-[400px]">
                                <p>${title.genres.join(' | ')}</p>
                                <p>${title.year} | ${title.type}</p>
                            </div>
                        </div>

                        ${chooseFolderButton(title, userTitles)}
                    </div>
                </li>
                `
        }
    } else {
        content =
            `
                <h5 class="nothing-found text-[1.4rem] font-bold">Ничего не найдено</h5>
            `;
    }

    searchResult.innerHTML = content;
    const popover = document.getElementById('user-library-popover')
    popover.classList.add('z-1001');
    document.dispatchEvent(new CustomEvent('TitlesUpdated', {}));
}


getSearchResults()