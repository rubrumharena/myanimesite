export function ajax_get(url, data={}) {
    return fetch(`${url}?${new URLSearchParams(data).toString()}`, {
        method: 'GET'
    })
    .then(response =>
        response.json().then(json => {
            if (response.status === 401) {
                window.location.href = json.redirect;
            }
            return { data: json, status: response.status };
        })
    )
    .catch(error => console.error(error));
}

export function ajax_post(url, data) {
    return fetch(url, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: data
    })
    .then(response =>
        response.json().then(json => {
            if (response.status === 401) {
                window.location.href = json.redirect;
            }
            return { data: json, status: response.status };
        })
    )
    .catch(error => console.error(error));
}


function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
        cookie = cookie.trim();
        if (cookie.startsWith(name + '=')) {
            cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
            break;
        }
        }
    }
  return cookieValue;
}
