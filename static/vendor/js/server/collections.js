import {ajax_get} from '../utils/ajax.js';

const collection_types = {
    year: 'YEAR',
    genre: 'GEN',
    movie: 'MOV_COL',
    series: 'SER_COL'
};

function getCollections() {
    const collection = document.querySelector(`[data-target='collections-popup']`);
    const url = window.COMMON.getCollections

    collection.addEventListener('click', function() {
        const preview = document.getElementById(collection_types.genre);
        preview.checked = true
        const data = {'type': collection_types.genre};
        ajax_get(url, data).then(response => generateCollectionList(response.data));
    });

    Object.entries(collection_types).forEach(([key, value]) => {
        const element = document.getElementById(value);
        const data = { type: value };
        if (element) {
            element.addEventListener('click', () =>
                ajax_get(url, data).then(response => generateCollectionList(response.data))
            );
        }
    });
}

function generateCollectionList(data) {
    const collections = data.items
    const list = document.querySelector('#collections-list')
    const popupContent = list.parentElement
    const banner = popupContent.querySelector('.nothing-found');
    list.classList.remove('hidden');
    banner.classList.add('hidden');

    let content = ''

    if (collections.length === 0) {
        list.classList.add('hidden');
        banner.classList.remove('hidden');
    }
    else {
        for (const collection of collections) {
            const humanized_count = getHumanizedTitleCount(collection.title_count, collection.type)
            content +=
                `
                <li class="flex relative w-full items-center gap-4 group">
                    <div class="absolute inset-[-0.8rem] bg-[#20201d] rounded-3xl opacity-0 transition-opacity duration-300 ease-in-out group-hover:opacity-100 z-[-1]"></div>
                    
                    <a href="${collection.url}" title="${collection.name}">
                        <img class="rounded-2xl h-24 w-24 object-cover object-center" 
                             src="${collection.image ? collection.image : window.COMMON.static + 'vendor/img/no_collection_image2.jpg'}" 
                             alt="title">
                    </a>
                    
                    <div>
                        <h4 class="text-3xl font-bold">
                            <a href="${collection.url}" title="${collection.name}">${collection.name}</a>
                        </h4>
                        ${collection.title_count >= 1 
                            ? `<p class="text-size-sm !text-text-gray">${humanized_count}</p>` 
                            : ''
                        }
                    </div>
                </li>
                `
        }
        list.innerHTML = content
    }
}

function getHumanizedTitleCount(title_count, type) {
    let ending
    let humanized_count = ''
    if (title_count >= 1) {
        if ((title_count >= 11 && title_count <= 19) || title_count % 10 === 0 || title_count % 10 >= 5) {
            ending = 'ов';
        }
        else if (title_count % 10 === 1) {
            ending = ''
        }
        else {
            ending = 'а'
        }

        if (type === collection_types.movie) {
            humanized_count = `${title_count} фильм${ending}`;
        } else if (type === collection_types.series) {
            humanized_count = `${title_count} сериал${ending}`;
        } else {
            if (title_count === 1) {
                humanized_count = `${title_count} тайтл`;
            }
            else {
                humanized_count = `${title_count} фильм${ending} и сериал${ending}`;
            }
        }
    }
    return humanized_count;
}


getCollections()