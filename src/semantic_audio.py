import torch, torchaudio, os

from pathlib import Path
from transformers import ClapModel, ClapProcessor
from data import Track, Description, user_dir

def model_dir(user_id):
    return Path(f"{user_dir(user_id)}/model/current")

def embed_dir(user_id):
    return Path(f"{os.environ['EMBEDS']}/{user_id}")

def text_embed_dir(user_id):
    return Path(f"{embed_dir(user_id)}/text")

def audio_embed_dir(user_id):
    return Path(f"{embed_dir(user_id)}/audio")

class Embeddings:

    def get_user_model(user_id):
        os.makedirs(model_dir(user_id), exist_ok=True)
        model = ClapModel.from_pretrained("laion/clap-htsat-fused", device_map='auto')
        try:
            model = ClapModel.from_pretrained(model_dir(user_id), device_map='auto')
        except BaseException as error:
            print(f"\nFailed to load user model with error, using default instead: \n{str(error)}\n")
        return model

    def get_processor():
        return ClapProcessor.from_pretrained("laion/clap-htsat-fused", device_map='auto')

    def __init__(self, user_id):
        self.user_id = user_id
        self.model = Embeddings.get_user_model(user_id)
        self.processor = Embeddings.get_processor()

    def train(self):
        self.model = self.model.train()
        return self

    def _process(self, **kwargs):
        return self.processor(**kwargs, padding=True, return_tensors="pt").to('cuda')
    
    def _text(self, text: str):
        inputs = self._process(text=text)
        embeds = self.model.get_text_features(**inputs)
        return embeds

    def _preprocess_audio(self, audio: torch.tensor, sampling_rate: int):
        audio = torchaudio.functional.resample(audio, sampling_rate, self.processor.feature_extractor.sampling_rate)
        audio = torch.mean(audio, 0)
        return audio, self.processor.feature_extractor.sampling_rate

    def _audio(self, audio: torch.tensor, sampling_rate: int):
        inputs = self._process(audios=audio, sampling_rate=sampling_rate)
        embeds = self.model.get_audio_features(**inputs)
        return embeds
                
    def get_embeds(self, fpath: str, compute) -> torch.tensor:
        is_cached = os.path.isfile(fpath)
        embeds = compute() if not is_cached else torch.load(fpath)
        if not is_cached:
            os.makedirs(fpath.parent, exist_ok=True)
            torch.save(embeds, fpath)
        return embeds

    def audio(self, uri: str) -> torch.tensor:
        fpath = Path(f"{audio_embed_dir(self.user_id)}/{uri}.pt")
        def compute():
            track = Track(uri)
            audio, sampling_rate = track.load()
            audio, sampling_rate = self._preprocess_audio(audio, sampling_rate)
            return self._audio(audio, sampling_rate)
        return self.get_embeds(fpath, compute)
    
    def text(self, uri: str) -> torch.tensor:
        fpath = Path(f"{text_embed_dir(self.user_id)}/{uri}.pt")
        def compute():
            description = Description(self.user_id, uri)
            text = description.load()
            return self._text(text)
        return self.get_embeds(fpath, compute)

    def _similarity(self, text_embedding: torch.tensor, audio_embedding: torch.tensor) -> torch.tensor:
        logit_scale_text = self.model.logit_scale_t.exp()
        logits_per_text  = torch.matmul(text_embedding, audio_embedding.t()) * logit_scale_text
        score = torch.sum(logits_per_text)
        return score.detach().item()

    def similarity(self, text_embeddings: list[torch.tensor], audio_embeddings: list[torch.tensor]) -> torch.tensor:
        return torch.tensor(
            [[self._similarity(text, audio) for audio in audio_embeddings] for text in text_embeddings]
        )

    def sort_tracks(self, query: str, tracks: list[Track]):
        text_embeddings = [self._text(query)]
        audio_embeddings = [self.audio(track.uri) for track in tracks]
        similarities = self.similarity(text_embeddings, audio_embeddings)
        for score, track in zip(similarities.squeeze().tolist(), tracks):
            track.score = score
        tracks.sort(key=lambda track: track.score, reverse=True)
        def to_metadata(track):
            description = Description(self.user_id, track.uri)
            metadata = track.metadata()
            metadata.score = track.score
            metadata.description = description.load()[0] if description.is_cached() else None
            return dict(metadata)
        return list(map(to_metadata, tracks))

