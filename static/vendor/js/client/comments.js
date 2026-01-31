export function displayComments(response) {
    const commentsContainer = document.getElementById('comments');

    const data = response.data;

    const pageObj = data.page_obj
    const stemComments = pageObj.object_list;


    if (response.status !== 200) {
        displayBanner('Произошла ошибка',
            'Попробуйте перезагрузить страницу или проверить подключение к интернету...', commentsContainer);
        return;
    }
    if (stemComments.length <= 0) {
        displayBanner('Напишите первый комментарий',
            'Здесь пока пусто - поделитесь своим мнением о тайтле', commentsContainer);
        return;
    }

    const commentTree = data.comment_tree
    const likedComments = data.liked_comments

    let html = ''
    let pagination = ''
    if (pageObj.has_previous || pageObj.has_next) {
        let paginationNumbers = ''
        for (const page of data.page_range) {
            if (page === data.ellipsis) {
                paginationNumbers += `<li class="w-9 h-9 rounded-2xl hover:bg-[#5f6062] flex-center"><span>${page}</span></li>`
            }
            else {
                console.log(page === pageObj.number)
                paginationNumbers +=
                    `
                    <li class="w-9 h-9 rounded-2xl ${page === pageObj.number ? 'bg-primary' : 'hover:bg-[#5f6062]'}">
                        <button data-page="${page}" class="${page === pageObj.number ? 'active-page !text-black font-bold' : ''} w-full h-full flex-center">
                            ${page}
                        </button>
                    </li>
                    `
            }
        }

        pagination =
            `
            <ul class="flex flex-center mt-12 gap-2.5">
                <li class="${pageObj.has_previous ? 'w-9 h-9 rounded-2xl hover:bg-[#5f6062]' : 'hidden'}">
                    <button data-page="${pageObj.previous_page_number}" class="w-full h-full flex-center" aria-label="Предыдущая страница">
                        <svg width="1.8rem" height="1.8rem" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
                            <path d="M14.2893 5.70708C13.8988 5.31655 13.2657 5.31655 12.8751 5.70708L7.98768 10.5993C7.20729 11.3805 7.2076 12.6463 7.98837 13.427L12.8787 18.3174C13.2693 18.7079 13.9024 18.7079 14.293 18.3174C14.6835 17.9269 14.6835 17.2937 14.293 16.9032L10.1073 12.7175C9.71678 12.327 9.71678 11.6939 10.1073 11.3033L14.2893 7.12129C14.6799 6.73077 14.6799 6.0976 14.2893 5.70708Z"></path>
                        </svg>
                    </button>
                </li>
                ${paginationNumbers}
                <li class="${pageObj.has_next ? 'w-9 h-9 rounded-2xl hover:bg-[#5f6062]' : 'hidden'}">
                    <button data-page="${pageObj.next_page_number}" class="w-full h-full flex-center" aria-label="Следующая страница">
                        <svg width="1.8rem" height="1.8rem" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
                            <path d="M9.71069 18.2929C10.1012 18.6834 10.7344 18.6834 11.1249 18.2929L16.0123 13.4006C16.7927 12.6195 16.7924 11.3537 16.0117 10.5729L11.1213 5.68254C10.7308 5.29202 10.0976 5.29202 9.70708 5.68254C9.31655 6.07307 9.31655 6.70623 9.70708 7.09676L13.8927 11.2824C14.2833 11.6729 14.2833 12.3061 13.8927 12.6966L9.71069 16.8787C9.32016 17.2692 9.32016 17.9023 9.71069 18.2929Z"></path>
                        </svg>
                    </button>
                </li>
            </ul>
            `
    }


    for (const comment of stemComments) {
        html +=
            `
                <li id="comment-${comment.id}" class="flex flex-col gap-1 group">
                    ${buildCommentTree(comment, likedComments, commentTree)}
                </li>
            `
    }
    commentsContainer.innerHTML = html + pagination;
}

function buildCommentTree(comment, likedComments, commentTree) {
    const staticDir = window.COMMON.static
    const avatar = comment.user__avatar
        ? comment.user__avatar
        : `${staticDir}vendor/img/utility/miku.svg`;
    const username = comment.user__name
        ? comment.user__name
        : comment.user__username

    let likeCount = '';
    const isLiked = likedComments.includes(comment.id);
    if (comment.like_count) {
      const classes = isLiked ? '!text-green-500' : '!text-stone-400';

      likeCount = `
        <span class="${classes}">( ${comment.like_count} )</span>
      `;
    }
    let branchesHTML = ''
    const branches = commentTree[comment.id]
    if (branches) {
        let branchContent = ''
        for (const branch of branches) {
            branchContent +=
                `
                <li id="comment-${branch.id}" class="flex flex-col gap-1 group">
                   ${buildCommentTree(branch, likedComments, commentTree)}
                </li>
                `
        }
        branchesHTML =
            `
            <ul class="ml-15 flex flex-col gap-1">
                ${branchContent}
            </ul>
            `
    }

    return `
        <div class="rounded-2xl p-4 flex group-odd:bg-secondary group-even:bg-[#201520] w-full">
            <a href="${comment.user_url}" class="shrink-0 mr-4 flex">
                <img class="rounded-full w-20 h-20 object-cover object-center" src="${avatar}" alt="">
            </a>
            <div class="comment-content flex flex-col gap-2 w-full">
                <p class="text-size-sm">
                    ${username}, 
                    <span class="!text-primary">оставлен ${comment.created_at}</span>
                </p>
        
                <p class="!text-primary text-size-sm">
                    @${comment.user__username}
                </p>
                <p>${comment.text}</p>
                <div class="flex items-center gap-4">
                    <button id="reply-${comment.id}" class="standard-button flex-center !font-normal gap-2 bg-transparent min-w-20 !h-10 rounded-2xl w-fit border-[#2b2c2d] border-[0.09rem] text-size-sm">
                        Ответить 
                    </button>
        
                    <button id="like-${comment.id}" class="flex items-center gap-2 z-100">
                        <svg class="pointer-events-none ${isLiked ? 'fill-green-500' : 'fill-stone-400'}" width="1.5rem" height="2rem" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                            <path fill-rule="evenodd" clip-rule="evenodd" d="M12.444 1.35396C11.6474 0.955692 10.6814 1.33507 10.3687 2.16892L7.807 9.00001L4 9.00001C2.34315 9.00001 1 10.3432 1 12V20C1 21.6569 2.34315 23 4 23H18.3737C19.7948 23 21.0208 22.003 21.3107 20.6119L22.9773 12.6119C23.3654 10.7489 21.9433 9.00001 20.0404 9.00001H14.8874L15.6259 6.7846C16.2554 4.89615 15.4005 2.8322 13.62 1.94198L12.444 1.35396ZM9.67966 9.70225L12.0463 3.39119L12.7256 3.73083C13.6158 4.17595 14.0433 5.20792 13.7285 6.15215L12.9901 8.36755C12.5584 9.66261 13.5223 11 14.8874 11H20.0404C20.6747 11 21.1487 11.583 21.0194 12.204L20.8535 13H17C16.4477 13 16 13.4477 16 14C16 14.5523 16.4477 15 17 15H20.4369L20.0202 17H17C16.4477 17 16 17.4477 16 18C16 18.5523 16.4477 19 17 19H19.6035L19.3527 20.204C19.2561 20.6677 18.8474 21 18.3737 21H8V10.9907C8.75416 10.9179 9.40973 10.4221 9.67966 9.70225ZM6 11H4C3.44772 11 3 11.4477 3 12V20C3 20.5523 3.44772 21 4 21H6V11Z"></path>
                        </svg>
                        ${likeCount}
                    </button>
                </div>
            </div>
        </div>
        ${branchesHTML}
        `
}

function displayBanner(title, text, container) {
    const textContainer = container.querySelector('p');
    const titleContainer = container.querySelector('h1');
    container.querySelector('#comments-message').classList.toggle('hidden');
    textContainer.innerHTML = text
    titleContainer.innerHTML = title
}

document.addEventListener('click', function(event) {
    const target = event.target;

    if (target.id && target.id.startsWith('reply-')) {

        const itemId = target.id.split('reply-')[1];
        const comment = document.getElementById(`comment-${itemId}`);
        const activeForms = document.querySelectorAll('form[id^="comment-form-"]');
        if (activeForms.length) {
            activeForms.forEach((form) => {
                form.remove();
            })
            return;
        }

        const form = document.createElement('form');
        form.className = 'mt-1 w-full';
        form.id = `comment-form-${itemId}`;
        form.method = 'POST';

        const text = document.createElement('textarea');
        text.className = 'min-h-16 h-16 p-2.5 rounded-[5px] bg-secondary border-[0.09rem] border-[#2b2c2d] w-full text-text-gray focus:border-primary';
        text.id = 'id_text'
        text.name = 'text'
        text.placeholder = 'Напишите ответ...';
        text.rows = 10;
        text.cols = 40

        const submit = document.createElement('button');
        submit.className = 'standard-button flex-center text-[1rem] gap-2 bg-[#20201d] min-w-20 !h-10 rounded-2xl w-80 mt-4';
        submit.textContent = 'Ответить';
        submit.type = 'submit';

        comment.querySelector('.comment-content').appendChild(form);

        form.appendChild(text);
        form.appendChild(submit);
    }
});

