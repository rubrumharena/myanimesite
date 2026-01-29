class AnchorSystem {
    constructor(popoverId) {
        this.popoverId = popoverId;
        this.popover = document.getElementById(popoverId);
        this.buttons = document.querySelectorAll(`[data-target="${popoverId}"]`);
        this.active = false;
        this.currentButton = null;

        this.scrollHandler = null;
        this.currentScrollParents = [];
        this.windowScrollHandler = null;
        this.windowResizeHandler = null;
        this.documentClickHandler = null;

        AnchorSystem.activeInstance = null;
    }

    init() {
        if (CSS.supports("top", "anchor(--anchor top)")) return;

        this.buttons.forEach(button => {
            button.addEventListener('click', (e) => {
                e.stopPropagation();
                this.currentButton = button;
                this.toggle();
            });
        });
    }

    toggle() {
        if (this.active) {
            this.hide();
        } else {
            this.show();
        }
    }

    show() {
        if (AnchorSystem.activeInstance) {
            AnchorSystem.activeInstance.hide();
        }

        this.setupPopoverStyle();
        this.updatePosition();
        this.attachScrollListeners();

        this.windowScrollHandler = () => this.updatePosition();
        window.addEventListener('scroll', this.windowScrollHandler);

        this.windowResizeHandler = () => this.updatePosition();
        window.addEventListener('resize', this.windowResizeHandler);

        this.documentClickHandler = (e) => this.handleDocumentClick(e);
        document.addEventListener('mousedown', this.documentClickHandler);

        this.active = true;
        AnchorSystem.activeInstance = this;
    }

    handleDocumentClick(e) {
        const isPopover = this.popover.contains(e.target);
        const isButton = Array.from(this.buttons).some(button => button.contains(e.target));

        if (!isPopover && !isButton) {
            this.hide();
        }
    }

    isInFixedElement(element) {
        let parent = element;
        while (parent && parent !== document.body) {
            const style = window.getComputedStyle(parent);
            if (style.position === 'fixed') {
                return true;
            }
            parent = parent.parentElement;
        }
        return false;
    }

    setupPopoverStyle() {
        const isFixed = this.isInFixedElement(this.currentButton);
        this.popover.style.position = isFixed ? 'fixed' : 'absolute';

        // просто убираем hidden
        this.popover.classList.remove('hidden');
    }

    updatePosition() {
        if (!this.popover || !this.currentButton) return;

        const btnRect = this.currentButton.getBoundingClientRect();
        const popoverRect = this.popover.getBoundingClientRect();
        const isFixed = this.popover.style.position === 'fixed';

        const position = this.calculatePosition(btnRect, popoverRect, isFixed);

        this.popover.style.top = `${position.top}px`;
        this.popover.style.left = `${position.left}px`;
    }

    calculatePosition(btnRect, popoverRect, isFixed) {
        const offset = 5;
        const space = {
            below: window.innerHeight - btnRect.bottom,
            above: btnRect.top,
            right: window.innerWidth - btnRect.left
        };

        return {
            top: isFixed
                ? (space.below >= popoverRect.height + offset
                    ? btnRect.bottom + offset
                    : btnRect.top - popoverRect.height - offset)
                : window.scrollY + (space.below >= popoverRect.height + offset
                    ? btnRect.bottom + offset
                    : btnRect.top - popoverRect.height - offset),
            left: isFixed
                ? Math.min(btnRect.left, window.innerWidth - popoverRect.width - 10)
                : window.scrollX + Math.min(btnRect.left, window.innerWidth - popoverRect.width - 10)
        };
    }

    attachScrollListeners() {
        this.currentScrollParents = this.getScrollParents(this.currentButton);
        this.scrollHandler = () => this.hide();
        this.currentScrollParents.forEach(p =>
            p.addEventListener('scroll', this.scrollHandler)
        );
    }

    getScrollParents(element) {
        const parents = [];
        let parent = element.parentNode;

        while (parent && parent !== document.body) {
            const style = window.getComputedStyle(parent);
            const isScrollable = ['auto', 'scroll'].includes(style.overflowY) ||
                               ['auto', 'scroll'].includes(style.overflowX);

            if (isScrollable) parents.push(parent);
            parent = parent.parentNode;
        }

        return parents;
    }

    hide() {
        if (!this.active) return;

        // просто добавляем hidden
        this.popover.classList.add('hidden');

        this.removeScrollListeners();

        if (this.documentClickHandler) {
            document.removeEventListener('mousedown', this.documentClickHandler);
            this.documentClickHandler = null;
        }

        this.active = false;
        this.currentButton = null;

        if (AnchorSystem.activeInstance === this) {
            AnchorSystem.activeInstance = null;
        }
    }

    removeScrollListeners() {
        if (this.scrollHandler) {
            this.currentScrollParents.forEach(p =>
                p.removeEventListener('scroll', this.scrollHandler)
            );
            this.scrollHandler = null;
            this.currentScrollParents = [];
        }

        if (this.windowScrollHandler) {
            window.removeEventListener('scroll', this.windowScrollHandler);
            this.windowScrollHandler = null;
        }

        if (this.windowResizeHandler) {
            window.removeEventListener('resize', this.windowResizeHandler);
            this.windowResizeHandler = null;
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const controls = new AnchorSystem('controls-popover');
    controls.init();
    const navigator = new AnchorSystem('navigator-popover');
    navigator.init();
    const userLibrary = new AnchorSystem('user-library-popover');
    userLibrary.init();
    const folder = new AnchorSystem('folder-popover');
    folder.init();
});

document.addEventListener('TitlesUpdated', () => {
    const userLibrary = new AnchorSystem('user-library-popover');
    userLibrary.init();
});



// function showHoverPopover(btnId, popoverId) {
//     const button = document.getElementById(btnId);
//     const popover = document.getElementById(popoverId);
//
//
//     button.addEventListener("mouseenter", () => {
//         popover.classList.remove("hidden");
//
//         const btnRect = button.getBoundingClientRect();
//         const offset = 5;
//
//         popover.style.left = `${window.scrollX + btnRect.left - 235}px`;
//         popover.style.top = `${window.scrollY + btnRect.bottom - 190}px`
//     });
//
//     button.addEventListener("mouseleave", () => {
//         popover.classList.add("hidden");
//     });
//
//     popover.addEventListener("mouseleave", () => {
//         popover.classList.add("hidden");
//     });
// }
//
