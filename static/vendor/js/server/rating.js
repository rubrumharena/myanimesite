import {ajax_post} from '../utils/ajax.js';
import {updateRatingBar} from '../client/rating_bar.js';


document.addEventListener('DOMContentLoaded', setRating);

function setRating() {
    const stars = document.querySelectorAll('#rating-bar li');
    if (!stars) return;

    stars.forEach(star => {
        star.addEventListener('click', function () {
            ajax_post(star.dataset.url).then(response => updateRatingBar(response.data));
        });
    });
}