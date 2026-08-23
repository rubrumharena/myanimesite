document.addEventListener('DOMContentLoaded', () => {
    const lightbox = document.getElementById('lightbox');
    console.log(lightbox)
    const lightboxImg = document.getElementById('lightbox-img');

    document.addEventListener('click', (e) => {
        const trigger = e.target.closest('[data-lightbox]');
        if (trigger) {
            lightboxImg.src = trigger.dataset.lightbox;
            lightbox.showModal();
            return;
        }
        if (e.target === lightbox) lightbox.close();
    });

    lightbox.addEventListener('close', () => { lightboxImg.src = ''; });
});