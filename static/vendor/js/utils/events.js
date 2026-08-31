export function dispatchModalContentUpdated() {
    const event = new CustomEvent('modalContentUpdated', {});
    document.dispatchEvent(event);
}


export function dispatchTitlesUpdated() {
    const event = new CustomEvent('titles:updated', {});
    document.dispatchEvent(event);
}

export function dispatchReviewUpdated(commentId) {
    const event = new CustomEvent('comments:reviewUpdated', {detail: {commentId}});
    document.dispatchEvent(event);
}


export function dispatchTitleAdded(titleId) {
    if (!Number.isInteger(titleId)) {
        return;
    }

    document.dispatchEvent(new CustomEvent('folders:titleAdded', {
        detail: {titleId}
    }));
}


export function dispatchTitleRemoved(titleId) {
    if (!Number.isInteger(titleId)) {
        return;
    }

    document.dispatchEvent(new CustomEvent('folders:titleRemoved', {
        detail: {titleId}
    }));
}
