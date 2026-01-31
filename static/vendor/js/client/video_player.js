const CLASSES = {
    ACTIVE: 'active !bg-neutral-500 pointer-events-none',
    DISABLED: '!text-neutral-500 pointer-events-none',
    WATCH_BUTTON: 'watch-button'
};

function displaySeasonsInfo(data) {
    const episodes_element = document.getElementById('episodes');
    const seasons_element = document.getElementById('seasons');

    seasons_element.innerHTML = '';
    episodes_element.innerHTML = '';

    const curSeason = data['cur_season'];
    const curEpisode = data['cur_episode'];
    const episodes = data['episodes'];
    const seasons = data['seasons'];

    const styles = '!bg-neutral-500 pointer-events-none';
    let html = '';
    for (const episode of episodes) {
        const highlightingStyles = episode === curEpisode ? styles : '';
        html += `<li class="episode watch-button !min-w-auto ${highlightingStyles}" data-episode="${episode}"><p class="select-none">Серия ${episode}</p></li>`;
    }
    episodes_element.innerHTML = html;

    html = '';
    for (const season of seasons) {
        const highlightingStyles = season === curSeason ? styles : '';
        html += `<li class="season watch-button !min-w-auto ${highlightingStyles}" data-season="${season}"><p class="select-none">Сезон ${season}</p></li>`;
    }
    seasons_element.innerHTML = html;
}


export function renderVideoPlayer(data) {
    const videoPlayer = document.getElementById('video-player');
    if (!videoPlayer) return;

    const sections = [
        renderVoiceovers(data.voiceovers, data.cur_voiceover),
        renderVideoSection(data),
    ];

    videoPlayer.innerHTML = sections.filter(Boolean).join('');
}


function renderVoiceovers(voiceovers, currentId) {
    if (!voiceovers) return '';
    let isHidden = voiceovers.length === 1

    const items = voiceovers.map(vo => {
        const isActive = vo.voiceover_id === currentId;
        const activeClass = isActive ? CLASSES.ACTIVE : '';

        return `
            <li class="voiceover ${CLASSES.WATCH_BUTTON} ${activeClass} flex-1 basis-auto overflow-hidden text-ellipsis whitespace-nowrap" data-voiceover="${vo.voiceover_id}">
                ${vo.voiceover__name}
            </li>
        `;
    }).join('');

    return `
        <div class="w-full -px-4 bg-neutral-950">
            <div class="p-4">
                <ul class="flex flex-wrap gap-2">
                    ${items}
                </ul>
            </div>
        </div>
    `;
}

function renderVideoSection(data) {
    const seasonsHTML = renderSeasons(data.seasons, data.cur_season, data.available_seasons);
    const videoHTML = renderVideo(data.video);
    const episodesHTML = renderEpisodes(data.episodes, data.cur_episode, data.available_episodes);

    return `
        <div class="bg-black flex flex-col pb-12 pt-4 px-4">
            ${seasonsHTML}
            ${videoHTML}
            ${episodesHTML}
        </div>
    `;
}

function renderSeasons(seasons, currentSeason, availableSeasons) {
    if (!seasons || seasons.length === 0) return '';

    const items = seasons.map(season => {
        const statusClass = getStatusClass(season, currentSeason, availableSeasons);

        return `
            <li class="season ${CLASSES.WATCH_BUTTON} min-w-auto ${statusClass}" data-season="${season}">
                Сезон ${season}
            </li>
        `;
    }).join('');

    return `
        <ul id="seasons" class="pb-4 grid grid-cols-6 gap-2 w-full">
            ${items}
        </ul>
    `;
}

function renderEpisodes(episodes, currentEpisode, availableEpisodes) {
    if (!episodes || episodes.length === 0) return '';

    const items = episodes.map(episode => {
        const statusClass = getStatusClass(episode, currentEpisode, availableEpisodes);

        return `
            <li class="episode ${CLASSES.WATCH_BUTTON} !min-w-auto ${statusClass}" data-episode="${episode}">
                Серия ${episode}
            </li>
        `;
    }).join('');

    return `
        <ul id="episodes" class="pt-4 grid grid-cols-6 gap-2 w-full">
            ${items}
        </ul>
    `;
}


function renderVideo(videoUrl) {
    if (videoUrl) {
        const staticDir = window.COMMON.static;
        return `
            <video 
                class="w-full" 
                data-url="${videoUrl}" 
                src="${staticDir}vendor/img/sample-video.mp4" 
                controls>
            </video>
        `;
    }

    return `
        <div class="flex-center flex-col gap-4 flex-1 min-h-[522px]">
            <svg class="fill-neutral-300" width="10rem" height="10rem" viewBox="-8 0 512 512" xmlns="http://www.w3.org/2000/svg">
                <path d="M248 8C111 8 0 119 0 256s111 248 248 248 248-111 248-248S385 8 248 8zm0 448c-110.3 0-200-89.7-200-200S137.7 56 248 56s200 89.7 200 200-89.7 200-200 200zm8-152c-13.2 0-24 10.8-24 24s10.8 24 24 24c23.8 0 46.3 10.5 61.6 28.8 8.1 9.8 23.2 11.9 33.8 3.1 10.2-8.5 11.6-23.6 3.1-33.8C330 320.8 294.1 304 256 304zm-88-64c17.7 0 32-14.3 32-32s-14.3-32-32-32-32 14.3-32 32 14.3 32 32 32zm160-64c-17.7 0-32 14.3-32 32s14.3 32 32 32 32-14.3 32-32-14.3-32-32-32zm-165.6 98.8C151 290.1 126 325.4 126 342.9c0 22.7 18.8 41.1 42 41.1s42-18.4 42-41.1c0-17.5-25-52.8-36.4-68.1-2.8-3.7-8.4-3.7-11.2 0z"></path>
            </svg>
            <h1 class="font-bold text-2xl">Видео пока недоступно</h1>
        </div>
    `;
}

function getStatusClass(episode, currentEpisode, availableEpisodes) {
    if (episode === currentEpisode) {
        return CLASSES.ACTIVE;
    }
    if (availableEpisodes && availableEpisodes.includes(episode)) {
        return '';
    }
    return CLASSES.DISABLED;
}