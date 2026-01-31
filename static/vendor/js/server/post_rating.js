import {ajax_post} from "../utils/ajax.js";
import {updateRatingBar} from "../client/rating_bar.js";

document.querySelectorAll('#rating-bar li').forEach(star => {
    star.addEventListener('click', function () {
        const url = window.WATCH_PAGE.setRating;
        const value = parseInt(this.getAttribute('data-index'));

        const data = new FormData();
        data.append('rating', value.toString());
        data.append('title_id', window.WATCH_PAGE.titleId);

        if (url) {
            ajax_post(url, data).then(response => updateRatingBar(response.data));
        }
    });
});
