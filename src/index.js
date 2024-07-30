function remove_children(element)
{
    while(element.firstChild)
    {
        element.removeChild(element.lastChild);
    }
}

function getCookie(cookie_name)
{
    let match = document.cookie.match(RegExp(`(?:^|;\\s*)${cookie_name}=([^;]*)`));
    return match && match[1];
}

function getUserID()
{
    return "0";
}


// We have htmx at home
// the htmx:
class SongEntry extends HTMLElement 
{

    constructor()
    {
      super();
      this.onDescriptionSubmit = this.onDescriptionSubmit.bind(this);
    }


    onDescriptionSubmit(event)
    {

        event.preventDefault();
        let params = 
        {
            method: 'POST',
            headers:
            {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(
                {
                    user_id: getUserID(),
                    uri: this.getAttribute('uri'),
                    text: this.description_input.value
                }
            )
        }
        fetch('/text', params);
        this.setAttribute('description', this.description_input.value);
    }

    connectedCallback()
    {
        remove_children(this);
        this.song_link         = document.createElement("a");
        this.artist_div        = document.createElement("div");
        this.score_div         = document.createElement("div");
        this.form              = document.createElement("form");
        this.description_input = document.createElement("input");
        this.song_link.innerText         = this.getAttribute('title');
        this.song_link.href              = this.getAttribute('uri');
        this.artist_div.innerText        = this.getAttribute('artist');
        this.score_div.innerText         = this.getAttribute('score');
        this.description_input.value     = this.getAttribute('description');
        this.form.append(this.description_input);
        this.form.onsubmit = this.onDescriptionSubmit;
        this.append(this.song_link);
        this.append(this.artist_div);
        this.append(this.score_div);
        this.append(this.form);
    }

    setAttributes(attributes)
    {
        this.setAttribute('title', attributes.title ?? '');
        this.setAttribute('uri', attributes.uri ?? '');
        this.setAttribute('artist', attributes.artist ?? '');
        this.setAttribute('score', attributes.score ?? '');
        this.setAttribute('description', attributes.description ?? '');
        this.connectedCallback();
    }
}

customElements.define( "song-entry", SongEntry );

async function onSearchSubmit(event)
{
    event.preventDefault();
    const search_query = document.querySelector('#search-query-form input').value;
    let params = 
    {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(
            {
                user_id: getUserID(),
                search_query: search_query,
                uris: [...document.querySelectorAll('song-entry')].map(element => element.getAttribute('uri'))
            }
        )
    }
    const response = await fetch(`/search`, params).then(r => r.json());
    const search_results = document.querySelector('#search-results');
    remove_children(search_results);
    for(const song of response)
    {
        const entry = document.createElement('song-entry');
        entry.setAttributes(song);
        search_results.appendChild(entry);
    }
}

async function onTrainButtonClick(event){
    event.preventDefault();
    for(const song of document.querySelectorAll('song-entry'))
    {
        if(song.description_input.value.length > 0)
        {
            song.onDescriptionSubmit(event);
        }
    }
    let params = 
    {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(
            {
                user_id: getUserID()
            }
        )
    }
    await fetch('/train', params);
}

async function dropHandler(event){
    event.preventDefault();
    const search_results = document.querySelector('#search-results');
    remove_children(search_results);
    [...event.dataTransfer.files].forEach(
        async file => 
        {
            const user_id = getUserID();
            const fname = encodeURIComponent(file.name);
            const data = await file.arrayBuffer();
            const params = 
            {
                method: 'POST',
                body: data
            }
            let response = await fetch(`/audio/${user_id}/${fname}`, params);
            if (response.status != 200){
                alert(`Upload for ${file.name} failed with status:\n${response.statusText}`)
            }
            let entry = await response.json();
            console.log(entry)
            let song_entry = document.createElement('song-entry');
            song_entry.setAttributes(entry);
            search_results.appendChild(song_entry);
        }
    )
}

window.onload = () => {
    // document.querySelector('body').ondrop     = dropHandler;
    document.querySelector('body').ondragover = event => event.preventDefault();
    document.getElementById('search-query-form').onsubmit = onSearchSubmit
    document.getElementById('train-button').onclick = onTrainButtonClick;
    spotifyOnLoad();
}


