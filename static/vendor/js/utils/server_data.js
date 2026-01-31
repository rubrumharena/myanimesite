import {ajax_get} from './ajax.js';

export async function loadUserTitles() {
    const response = await ajax_get(window.COMMON.getUserTitles);
    return response.data;
}