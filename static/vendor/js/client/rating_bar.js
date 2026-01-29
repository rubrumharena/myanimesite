const stars = document.querySelectorAll('.star');
const ratingElement = document.getElementById('rating-value');
const votesElement = document.getElementById('votes');


export function updateRatingBar(data) {
    console.log(data)
    const rating = parseFloat(data.rating);
    const votes = data.votes;

    ratingElement.textContent = data.rating;
    votesElement.textContent = `(${votes})`;

    const ratingClasses = {
        red: '!text-red-600',
        yellow: '!text-yellow-300',
        green: '!text-green-500',
        blue: '!text-primary',
        gray: '!text-stone-400',
    };

    let newColor;

    if (rating >= 1 && rating < 5) newColor = ratingClasses.red;
    else if (rating >= 5 && rating < 7) newColor = ratingClasses.yellow;
    else if (rating >= 7 && rating < 9) newColor = ratingClasses.green;
    else if (rating >= 9 && rating <= 10) newColor = ratingClasses.blue;

    // Удалить все предыдущие цветовые классы
    Object.values(ratingClasses).forEach(cls => ratingElement.classList.remove(cls));

    // Добавить текущий
    ratingElement.classList.add(newColor);


    const fullStars = Math.floor(rating);
    const partial = rating % 1 * 100;

    stars.forEach((star, index) => {
        const goldRect = star.querySelector('.rect-gold');
        const grayRect = star.querySelector('.rect-gray');
        grayRect.classList.remove('fill-stone-400');
        grayRect.classList.add('fill-stone-800');
        if (!goldRect || !grayRect) return;

        if (index < fullStars) {
            goldRect.setAttribute('width', '100%');
            grayRect.setAttribute('x', '100%');
        } else if (index === fullStars) {
            goldRect.setAttribute('width', `${partial}%`);
            grayRect.setAttribute('x', `${partial}%`);
        } else {
            goldRect.setAttribute('width', '0%');
            grayRect.setAttribute('x', '0');
        }
    });
}

function highlightRatingBar() {
    stars.forEach((star, index) => {
        star.addEventListener('mouseover', () => updateHover(index));
        star.addEventListener('mouseout', () => clearHover());
    });
}

function updateHover(index) {
    stars.forEach((star, i) => {
        const rects = star.querySelectorAll('rect');

        rects.forEach(rect => {
            if (i <= index) {
              rect.classList.add('fill-yellow-500');
            } else {
              rect.classList.remove('fill-yellow-500');
            }

        });
    });
}

function clearHover() {
    stars.forEach(star => {
        const rects = star.querySelectorAll('rect');

        rects.forEach(rect => {
            rect.classList.remove('fill-yellow-500');
        });
    });
}

if ([...stars].every(star => star.classList.contains('cursor-pointer'))) {
    highlightRatingBar();
}
