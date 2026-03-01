import {ajax_get, ajax_post} from '../utils/ajax.js';

document.addEventListener('DOMContentLoaded', () => loadVideoPlyer());
document.addEventListener('click', saveProgress);


function loadVideoPlyer() {
    const data = parseUrlHash();

    ajax_get(window.WATCH_PAGE.getVideoContent, data).then(response => updateHtml(response));
}


function saveProgress(event) {
    const episodeBtn = event.target.closest?.('.episode');
    const seasonBtn = event.target.closest?.('.season');
    const voiceBtn = event.target.closest?.('.voiceover');

    if (!episodeBtn && !seasonBtn && !voiceBtn) return;

    let episode = null;
    let season = null;
    let voiceover = null;
    if (episodeBtn) {
        episode = episodeBtn.dataset.episode;
        season = document.querySelector('.season.active')?.dataset.season;
        voiceover = document.querySelector('.voiceover.active')?.dataset.voiceover;
    } else if (seasonBtn) {
        season = seasonBtn.dataset.season;
        voiceover = document.querySelector('.voiceover.active')?.dataset.voiceover;
    } else if (voiceBtn) {
        voiceover = voiceBtn.dataset.voiceover;
    } else {
        return;
    }

    const params = {
        episode: String(episode),
        season: String(season),
        voiceover_id: String(voiceover),
    };


    const data = new FormData();
    Object.entries(params).forEach(([k, v]) => data.append(k, v));

    return ajax_get(window.WATCH_PAGE.getVideoContent, params)
        .then(html => {
            updateHtml(html);
            pushUrl(params);
            return ajax_post(window.WATCH_PAGE.saveVideoProgress, data);
        })
}


function pushUrl(params) {
    if (!params) return;

    let episode = params.episode;
    let season = params.season;
    let voiceover = params.voiceover_id;

    if (episode && season && voiceover) {
        const newUrl = `#voiceover_id:${voiceover}-season:${season}-episode:${episode}`;
        window.history.pushState({season, episode, voiceover}, '', newUrl);
    }
}


function updateHtml(response) {
    if (!response?.data?.html) return;
    const player = document.getElementById('video-player');
    if (!player) return;

    player.innerHTML = response.data.html;
}


function parseUrlHash() {
    const hash = window.location.hash.slice(1);

    if (!hash) return {};

    const parts = hash.split('-');

    const entries = parts
        .map(part => part.split(':'))
        .filter(arr => arr.length === 2);

    return Object.fromEntries(entries);
}
