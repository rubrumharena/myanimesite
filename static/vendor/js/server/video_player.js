import {ajax_get, ajax_post} from '../utils/ajax.js';
import {renderVideoPlayer} from '../client/video_player.js';


document.addEventListener('DOMContentLoaded', () => initVideoPlayer());
document.addEventListener('click', saveViewingProgress);


function initVideoPlayer(data = null) {
    const url = window.WATCH_PAGE.getVideo;
    let urlData = null;
    console.log(data);
    if (!data) {
        urlData = parseUrlHash();
    }

    ajax_get(url, data).then(response => {
        const responseData = response.data;
        renderVideoPlayer(responseData);

        if (!urlData) {
            let episode = responseData.cur_episode;
            let season = responseData.cur_season;
            let voiceover = responseData.cur_voiceover;

            if (episode && season && voiceover) {
                const newUrl = `#voiceover:${voiceover}-season:${season}-episode:${episode}`;
                window.history.pushState({season, episode, voiceover}, '', newUrl);
            }
        }
    });
}


function parseUrlHash() {
    const hash = window.location.hash.substring(1);
    const parts = hash.split('-');
    return Object.fromEntries(parts.map(part => part.split(':')));
}


function saveViewingProgress(event) {
    console.log('dsdsd');
    const button = event.target;
    let episode = null;
    let season = null;
    let voiceover = null;
    if (button.classList.contains('episode')) {
        episode = button.dataset.episode;
        season = document.querySelector('.season.active')?.dataset.season;
        voiceover = document.querySelector('.voiceover.active')?.dataset.voiceover;
    } else if (button.classList.contains('season')) {
        season = button.dataset.season;
        voiceover = document.querySelector('.voiceover.active')?.dataset.voiceover;
    } else if (button.classList.contains('voiceover')) {
        voiceover = button.dataset.voiceover;
    } else {
        return;
    }

    const data = new FormData();
    data.append('episode', episode);
    data.append('season', season);
    data.append('voiceover', voiceover);
    data.append('title_id', window.WATCH_PAGE.titleId);
    ajax_post(window.WATCH_PAGE.saveVideoProgress, data)
        .then(response => {
            if (response.status === 403) {
                initVideoPlayer(data);
            } else {
                initVideoPlayer(response.data);
            }
        });
}

//
//
// function getSeasonsInfo(titleId) {
//     const url = window.WATCH_PAGE.getSeasonsInfo;
//     const data = {'title_id': titleId};
//     ajax_get(url, data).then(response => displaySeasonsInfo(response.data));
// }