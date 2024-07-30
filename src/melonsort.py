import logging
import os
import gc
import torch
import urllib

from pathlib import Path
from data import FLACProvider, Track, Description, uri, audio_dir
from semantic_audio import Embeddings
from train import Trainer, TrainingDataset, model_dir
from transformers import TrainingArguments

from fastapi import FastAPI, Body, Request
from fastapi.responses import HTMLResponse, FileResponse

melonsort = FastAPI()
logger = logging.getLogger("uvicorn")

@melonsort.post("/search")
async def search(user_id: str = Body(...), search_query: str = Body(...), uris: list[str] = Body(...)):
    Track.providers.update(
        {
            FLACProvider: FLACProvider(user_id)
        }
    )
    tracks = Track.from_uris(uris if len(uris) > 0 else map(uri, os.listdir(audio_dir(user_id))))
    model = Embeddings(user_id)
    return model.sort_tracks(search_query, tracks)

@melonsort.post("/text", status_code=200)
async def add_text(user_id: str = Body(...), uri: str = Body(...), text: str = Body(...)):    
    description = Description(user_id, uri)
    description.save(text=[text], tag=text.split(','))

@melonsort.post("/audio/{user_id}/{uri}")
async def add_audio(user_id: str, uri: str, data: Request):
    Track.providers.update(
        {
            FLACProvider: FLACProvider(user_id)
        }
    )
    logger.info(uri)
    data = await data.body()
    track = Track(uri)
    os.makedirs(track.fpath().parent, exist_ok=True)
    with open(f"{audio_dir(user_id)}/{uri}", "wb+") as file:
        file.write(data)
    return dict(track.metadata())



@melonsort.post("/train", status_code=200)
def train_model(user_id: str = Body(..., embed=True)):
    embeddings = Embeddings(user_id)
    embeddings = embeddings.train()
    trainer_args = TrainingArguments(
        output_dir=model_dir(user_id).parent,
        overwrite_output_dir=True,
        num_train_epochs=1,
        report_to="none",
        fp16=True,
        fp16_full_eval=True,
        disable_tqdm=True,
        dataloader_pin_memory=False
    )
    dataset = TrainingDataset(embeddings)
    trainer = Trainer(
        embeddings.model,
        args=trainer_args,
        train_dataset=dataset,
        data_collator=TrainingDataset.collate
    )
    print("training!")
    trainer.train()
    embeddings.model.save_pretrained(model_dir(user_id))
    del embeddings
    del trainer
    del dataset
    gc.collect()
    torch.cuda.empty_cache()
    return

@melonsort.get("/", response_class=HTMLResponse)
async def index():
    return open("index.html").read()

@melonsort.get("/index.js")
def get_js():
    return FileResponse(f"index.js")

@melonsort.get("/spotify.js")
def get_js():
    return FileResponse(f"spotify.js")

@melonsort.get("/index.css")
def get_css():
    return FileResponse(f"index.css")
