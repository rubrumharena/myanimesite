document.addEventListener("DOMContentLoaded", () => {
    activateParallax();
});

function activateParallax() {
    let back = document.getElementById('back');
    let girl = document.getElementById('girl');
    let middle = document.getElementById('middle');
    let girlBack = document.getElementById('inner-front');
    let front = document.getElementById('front');
    let container = document.querySelector("#main-banner");

    container.addEventListener("mousemove", (e) => {
        let rect = container.getBoundingClientRect();
        let x = (e.clientX - rect.left) / rect.width - 0.5;
        let y = (e.clientY - rect.top) / rect.height - 0.5;

        back.style.transform = `translate(${x * 25}px, ${y * 25}px)`;
        girl.style.transform = `translate(${x * 50}px, ${y * 50}px)`;
        girlBack.style.transform = `translate(${x * 40}px, ${y * 40}px)`;
        middle.style.transform = `translate(${x * 32}px, ${y * 32}px)`;
        front.style.transform = `translate(${x * 40}px, ${y * 40}px)`;
    });

    container.addEventListener("mouseleave", () => {
        back.style.transform = `translate(0, 0)`;
        middle.style.transform = `translate(0, 0)`;
        girl.style.transform = `translate(0, 0)`;
        girlBack.style.transform = `translate(0, 0)`;
        front.style.transform = `translate(0, 0)`;
    });
};


