import google.protobuf.json_format
import subprocess
import requests
import os
import torchaudio
import io
import json
from librespot.core import Session, ApiClient
from librespot.metadata import TrackId, PlaylistId
from librespot.audio.decoders import AudioQuality, VorbisOnlyAudioQuality
from librespot.proto import Authentication_pb2 as Authentication

# TODO: Make an audio provider-agnostic framework (e.g. get_track(provider='spotify') ) 
def pb_to_dict(pb):
    return google.protobuf.json_format.MessageToDict(pb)

def get_track_metadata_from_uri(session, uri):
    metadata = session.api().get_metadata_4_track(TrackId.from_uri(uri))
    metadata = pb_to_dict(metadata)
    metadata['uri'] = uri
    return metadata

def get_track_uris_from_liked_songs(session, limit=50):
    access_token = session.tokens().get("user-library-read")
    def req(offset, limit):
        return requests.get(
            f"https://api.spotify.com/v1/me/tracks?offset={offset}&limit={limit}", 
            headers={
                'Authorization': f'Bearer {access_token}'
            }
        ).json()
    track_uris = []
    retrieved = 0
    total = 1
    while retrieved < total:
        response = req(retrieved, limit)
        for response_item in response['items']:
            track_uri = response_item['track']['uri']
            track_uris.append(track_uri)
        retrieved += limit
        total = response['total']
    return track_uris

def get_track_uris_from_playlist(session, playlist_uri):
    playlist_id = PlaylistId.from_uri(playlist_uri)
    playlist_protobuf = session.api().get_playlist(playlist_id)
    playlist = pb_to_dict(playlist_protobuf)
    return [ track['uri'] for track in playlist['contents']['items'] ]

def get_track_buffer(session, uri, quality):
    stream     = session.content_feeder().load(TrackId.from_uri(uri), VorbisOnlyAudioQuality(quality), False, None)
    bytes_data = stream.input_stream.stream().read(stream.input_stream.size)
    return io.BytesIO(bytes_data)

# TODO: make librespot session stream a file-like object
def get_track(session, uri, quality=AudioQuality.NORMAL):
    track = get_track_metadata_from_uri(session, uri)
    def create_data_getter(session, uri, quality):
        def get_data():
            buffer = get_track_buffer(session, uri, quality)
            return torchaudio.load(buffer)
        return get_data
    track['data_getter'] = create_data_getter(session, uri, quality)
    track['title'] = track['name']
    track['artist'] = ', '.join( artist['name'] for artist in track['artist'] )
    return track

def get_liked_tracks(session, quality=AudioQuality.NORMAL):
    for track_uri in get_track_uris_from_liked_songs(session):
        yield get_track(session, track_uri, quality)

def get_user_info(access_token):
    return requests.get(
    "https://api.spotify.com/v1/me", 
        headers={
            "Authorization": f"Bearer {access_token}"
        }
    ).json()

def get_session(access_token):
    user_info = get_user_info(access_token)
    auth_blob = subprocess.run(['./librespot', '--username', user_info['id'], '--access-token', access_token, '--quiet', '--dump'], capture_output=True).stdout
    session = Session.Builder()
    session.login_credentials = Authentication.LoginCredentials(
        username=user_info['id'],
        auth_data=auth_blob,
        typ=Authentication.AuthenticationType.AUTHENTICATION_STORED_SPOTIFY_CREDENTIALS
    )
    session = session.create()
    return session
