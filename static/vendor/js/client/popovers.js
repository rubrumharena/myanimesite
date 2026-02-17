const popover = document.getElementById('library-popover');
const carousels = document.querySelectorAll('.carousel');

carousels.forEach(carousel => {
    carousel.addEventListener(
        'scroll',
        () => {
            if (popover.matches(':popover-open')) {
                popover.hidePopover();
            }
        },
        { passive: true }
    );
});