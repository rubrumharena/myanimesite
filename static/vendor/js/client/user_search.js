const searchInput = document.getElementById('user-search');
const searchButton = document.getElementById('user-search-button');

function buildUrl(event) {
    if (event.type === 'keydown' && event.key === 'Enter' && event.target === searchInput) {
        event.preventDefault();
        performSearch();
    }

    else if (event.type === 'click' && event.target.closest('#user-search-button')) {
        event.preventDefault();
        performSearch();
    }
}

function performSearch() {
    const searchQuery = searchInput.value.trim();
    const url = new URL(window.location.href);

    if (searchQuery) {
        url.searchParams.set('search', searchQuery);
    } else {
        url.searchParams.delete('search');
    }

    window.location.href = url.toString();
}

searchInput.addEventListener('keydown', buildUrl);
searchButton.addEventListener('click', buildUrl);
