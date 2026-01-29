document.querySelectorAll('.carousel').forEach(carousel => {
    let isDragging = false, startX, startScrollLeft, moved = false;

    const dragStart = (e) => {
        e.preventDefault();
        isDragging = true;
        moved = false;
        carousel.classList.add("dragging");
        startX = e.pageX;
        startScrollLeft = carousel.scrollLeft;
    }

    const dragging = (e) => {
        if (!isDragging) return;
        let moveX = Math.abs(e.pageX - startX);
        if (moveX > 2) moved = true; 
        carousel.scrollLeft = startScrollLeft - (e.pageX - startX);
    }

    const dragStop = () => {
        isDragging = false;
        carousel.classList.remove("dragging");
    }

    const handleClick = (e) => {
        if (moved) e.preventDefault();
    }

    carousel.addEventListener("mousedown", dragStart);
    carousel.addEventListener("mousemove", dragging);
    document.addEventListener("mouseup", dragStop);
    carousel.addEventListener("click", handleClick, true);
});
