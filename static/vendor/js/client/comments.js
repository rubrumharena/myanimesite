document.addEventListener('click', function (event) {
    const target = event.target;

    if (target.id && target.id.startsWith('reply-')) {
        const itemId = target.id.split('reply-')[1];
        const comment = document.getElementById(`comment-${itemId}`);
        if (!comment) return;

        const activeForms = document.querySelectorAll('form[id^="comment-form-"]');
        if (activeForms.length) {
            activeForms.forEach((form) => {
                form.remove();
            });
            return;
        }


        const form = document.createElement('form');
        form.className = 'mt-1 w-full';
        form.id = `comment-form-${itemId}`;
        form.method = 'POST';
        form.action = window.WATCH_PAGE.postComment;

        const text = document.createElement('textarea');
        text.className = 'min-h-16 h-16 p-2.5 rounded-[5px] bg-secondary border-[0.09rem] border-[#2b2c2d] w-full text-text-gray focus:border-primary';
        text.id = 'id_text';
        text.name = 'text';
        text.placeholder = 'Напишите ответ...';
        text.rows = 10;
        text.cols = 40;

        const submit = document.createElement('button');
        submit.className = 'standard-button flex-center text-[1rem] gap-2 bg-[#20201d] min-w-20 !h-10 rounded-2xl w-80 mt-4';
        submit.textContent = 'Ответить';
        submit.type = 'submit';

        comment.querySelector('.comment-content').appendChild(form);

        form.appendChild(text);
        form.appendChild(submit);
    }
});

