import semantic_audio
import spotify
import logging
import os
import glob
import json
import requests
import webdataset as wds
import torchaudio
import torchvision.transforms as transforms

from fastapi import FastAPI, Body, Request, Response

client_id='a7c414b11d594773bdfffd58d463cfbd'
scope='streaming user-library-read'

sort = FastAPI()
logger = logging.getLogger("uvicorn")

def get_user_track_description(user_info, track):
    text_fpath = os.path.join('/data', user_info['id'], 'raw', track['uri'] + '.json')
    if os.path.isfile(text_fpath):
        with open(text_fpath, 'r') as file:
            return json.load(file)['text'][0]
    else:
        return ''

def get_user_model(user_info):
    user_model = os.path.join('/data', user_info['id'], 'model')
    if not os.path.isdir(user_model):
        user_model = "laion/clap-htsat-fused"
    model = semantic_audio.ClapModel.from_pretrained(user_model, torch_dtype=semantic_audio.torch.float32, device_map='cuda').to(semantic_audio.torch.float16)
    return model

@sort.post("/search")
async def search(spotify_access_token: str = Body(...), search_query: str = Body(...)):
    session = spotify.get_session(spotify_access_token)
    liked_tracks = spotify.get_liked_tracks(session)
    user_info = spotify.get_user_info(spotify_access_token)
    model = get_user_model(user_info)
    processor = semantic_audio.ClapProcessor.from_pretrained("laion/clap-htsat-fused", torch_dtype=semantic_audio.torch.float16, device_map='cuda')
    os.makedirs(f"/embeds/{user_info['id']}", exist_ok=True)
    return [
        {
            'name': track['name'],
            'uri': track['uri'],
            'artist': track['artist'],
            'score': track['score'],
            'description': get_user_track_description(user_info, track)
        }
        for track in semantic_audio.sort_audio_by_text_prompt(processor, model, search_query, liked_tracks, user_info)
    ]

@sort.post("/data")
async def add_user_data(spotify_access_token: str = Body(...), uri: str = Body(...), text: str = Body(...)):
    user_info = spotify.get_user_info(spotify_access_token)
    flac_fpath = os.path.join('/data', user_info['id'], 'raw', uri + '.flac')
    text_fpath = os.path.join('/data', user_info['id'], 'raw', uri + '.json')
    os.makedirs(os.path.dirname(text_fpath), exist_ok=True)
    with open(text_fpath, 'w') as file:
        json.dump({
            'text': [text],
            'tag': text.split(', ')
        }, file)
    if not os.path.isfile(flac_fpath):
        session = spotify.get_session(spotify_access_token)
        track_buffer = spotify.get_track_buffer(session, uri, spotify.AudioQuality.NORMAL)
        track_data, sample_rate = semantic_audio.torchaudio.load(track_buffer)
        semantic_audio.torchaudio.save(flac_fpath, track_data, sample_rate, format='flac')


@sort.post("/train")
async def train(data=Body(...)):
    access_token = data['spotify_access_token']
    user_info = spotify.get_user_info(access_token)
    model = get_user_model(user_info)
    processor = semantic_audio.ClapProcessor.from_pretrained("laion/clap-htsat-fused", torch_dtype=semantic_audio.torch.float16, device_map='cuda')
    shard_urls = glob.glob(f"/data/{user_info['id']}/train/*.tar")
    preprocess = transforms.Compose([
        lambda data_point: (torchaudio.load(data_point[0]), data_point[1]['tag'])
    ])
    dataset = wds.DataPipeline(
        wds.SimpleShardList(shard_urls),
        wds.tarfile_to_samples(),
        wds.to_tuple("flac", "json"),
        wds.map(preprocess)
    )
    # trainer = 
    requests.post('http://train/', json=user_info)
