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
    const params = 
    {
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
    const params = 
    {
        method: 'POST',
        headers: 
        {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: new URLSearchParams(
            {
                client_id: clientId,
                grant_type: 'authorization_code',
                code,
                redirect_uri: redirectUri,
                code_verifier: codeVerifier,
            }
        )
    }
    const response = await fetch("https://accounts.spotify.com/api/token", params);
    return await response.json();
}

async function request_refresh_token(){
    const params = 
    {
        method: 'POST',
        body: new URLSearchParams(
            {
                grant_type: 'refresh_token',
                refresh_token: getCookie('spotify-refresh-token'),
                client_id: clientId
            }
        )
    }
    const response = await fetch("https://accounts.spotify.com/api/token", params);
    return await response.json()
    .then( 
        response => 
        {
            document.cookie = `spotify-access-token=${response.access_token}`;
            document.cookie = `spotify-refresh-token=${response.refresh_token}`;
            return response;
        }
    )
    .then(
        response => 
        {
            setTimeout(() => request_refresh_token(), response.expires_in * 1000);
            return response;
        }
    );
}

async function getUserID(){
    let params =
    {
        method: 'GET',
        headers: 
        {
            "Authorization": `Bearer ${getCookie('spotify-access-token')}`
        }
    }
    let response = await fetch("https://api.spotify.com/v1/me", params)
    return await response.json()
    .then(
        response => 
        {
            return response.id
        }
    )
}

function spotifyOnLoad(){
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