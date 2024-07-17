const clientId = 'a7c414b11d594773bdfffd58d463cfbd';
const redirectUri = 'http://localhost/';

function generateRandomString(length){
    const possible = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    const values = crypto.getRandomValues(new Uint8Array(length));
    return values.reduce((acc, x) => acc + possible[x % possible.length], "");
}

function sha256(plain){
    const encoder = new TextEncoder()
    const data = encoder.encode(plain)
    return window.crypto.subtle.digest('SHA-256', data)
}

function base64encode(input){
    return btoa(String.fromCharCode(...new Uint8Array(input)))
      .replace(/=/g, '')
      .replace(/\+/g, '-')
      .replace(/\//g, '_');
}

async function userAuthRequest(){
    const codeVerifier  = generateRandomString(64);
    window.localStorage.setItem('code-verifier', codeVerifier);
    const hashed = await sha256(codeVerifier)
    const codeChallenge = base64encode(hashed);
    const authUrl = new URL("https://accounts.spotify.com/authorize")
    const params = {
        response_type: 'code',
        client_id: clientId,
        scope: 'streaming user-library-read',
        code_challenge_method: 'S256',
        code_challenge: codeChallenge,
        redirect_uri: redirectUri,
    }
    authUrl.search = new URLSearchParams(params).toString();
    window.location.href = authUrl.toString();
}

async function request_access_token(code){
    let codeVerifier = window.localStorage.getItem('code-verifier');
    const payload = {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: new URLSearchParams({
          client_id: clientId,
          grant_type: 'authorization_code',
          code,
          redirect_uri: redirectUri,
          code_verifier: codeVerifier,
        })
    }
    const response = await fetch("https://accounts.spotify.com/api/token", payload);
    return await response.json();
}

async function request_refresh_token(){
    const params = {
      method: 'POST',
      body: new URLSearchParams({
        grant_type: 'refresh_token',
        refresh_token: getCookie('spotify-refresh-token'),
        client_id: clientId
      })
    }
    const response = await fetch("https://accounts.spotify.com/api/token", params);
    return await response.json()
    .then( response => {
        document.cookie = `spotify-access-token=${response.access_token}`;
        document.cookie = `spotify-refresh-token=${response.refresh_token}`;
        return response;
    })
    .then( response => {
        setTimeout(() => request_refresh_token(), response.expires_in * 1000);
        return response;
    });
}

function getCookie(cookie_name){
    let match = document.cookie.match(RegExp(`(?:^|;\\s*)${cookie_name}=([^;]*)`));
    return match && match[1];
}

// We have htmx at home
// the htmx:
class SongEntry extends HTMLElement {

    constructor() {
      super();
      this.onDescriptionSubmit = this.onDescriptionSubmit.bind(this)
    }

    onDescriptionSubmit(event){
        event.preventDefault();
        let params = {
            method: 'POST',
            body: JSON.stringify({
                spotify_access_token: getCookie('spotify-access-token'),
                uri: this.song_link.href,
                text: this.description_input.value
            })
        }
        fetch('/data', params);
        this.setAttribute('description', this.description_input.value);
    }

    connectedCallback(){
        this.song_link         = document.createElement("a");
        this.artist_div        = document.createElement("div");
        this.score_div         = document.createElement("div");
        this.form              = document.createElement("form");
        this.description_input = document.createElement("input");

        this.song_link.innerText         = this.getAttribute('name');
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
}

customElements.define( "song-entry", SongEntry );

async function onSearchSubmit(event){
    event.preventDefault();
    const search_query = document.querySelector('#search-query-form input').value;
    let params = {
        method: 'POST',
        body: JSON.stringify({
            spotify_access_token: getCookie('spotify-access-token'),
            search_query: search_query
        })
    }
    const response = await fetch(`/search`, params).then(r => r.json());
    const search_results = document.querySelector('#search-results');
    while (search_results.firstChild) {
        search_results.removeChild(search_results.lastChild);
    }
    for(const {name, uri, artist, score, description} of response){
        const entry = document.createElement('song-entry');
        entry.setAttribute('name', name);
        entry.setAttribute('uri', uri);
        entry.setAttribute('artist', artist.map(a => a.name).join(', '));
        entry.setAttribute('score', score);
        entry.setAttribute('description', description);
        search_results.appendChild(entry);
    }
}

function onTrainButtonClick(event){
    event.preventDefault();
    for(const song of document.querySelectorAll('song-entry')){
        if(song.description_input.value.length > 0){
            song.onDescriptionSubmit(event);
        }
    }
    let params = {
        method: 'POST',
        body: JSON.stringify({
            spotify_access_token: getCookie('spotify-access-token')
        })
    }
    fetch('/train', params);
}

function dropHandler(event){
    event.preventDefault();
    let reader = new FileReader();
    [...event.dataTransfer.files].forEach(async file => {
        let data = await file.arrayBuffer();
        console.log(data);
    })
}

window.onload = () => {
    document.querySelector('body').ondrop     = dropHandler;
    document.querySelector('body').ondragover = event => {event.preventDefault()};  
    document.getElementById('search-query-form').onsubmit = onSearchSubmit
    document.getElementById('train-button').onclick = onTrainButtonClick;
    if( !window.localStorage.getItem('code-verifier') ){
        userAuthRequest();
    } else {
        const urlParams = new URLSearchParams(window.location.search);
        const authCode = urlParams.get('code');
        if( authCode ){
            request_access_token(authCode)
            .then( response => {
                document.cookie = `spotify-access-token=${response.access_token}`;
                document.cookie = `spotify-refresh-token=${response.refresh_token}`;
                setTimeout( () => request_refresh_token(), response.expires_in * 1000);
            })
            .then(() => window.history.pushState({}, '', redirectUri))
            .then(() => window.localStorage.removeItem('code-verifier'))
        }
    }
}


