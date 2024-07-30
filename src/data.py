import os
import json
import torchaudio
import pathlib
import mutagen
import random

from pathlib import Path

from torch.utils.data import Dataset

from typing import Union, Any, Optional
from pydantic import BaseModel

def uri(string):
    return pathlib.Path(string).stem

def user_dir(user_id):
    return Path(f"{os.environ['DATA']}/{user_id}")

def text_dir(user_id):
    return Path(f"{user_dir(user_id)}/text")

def audio_dir(user_id):
    return Path(f"{user_dir(user_id)}/audio")

# class Cache(dict):

#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)

#     def policy(self):
#         raise NotImplementedError()
    
#     def __fetch__(self, key):
#         raise NotImplementedError()

#     def fetch(self, key):
#         return self.__fetch__(key)

#     def __persist__(self, key):
#         raise NotImplementedError()

#     def persist(self, key):
#         if key not in self.keys():
#             raise KeyError("Attempted to persist a value not present in cache")
#         else:
#             self.__persist__(key)

#     def __getitem__(self, key):
#         if key in self.keys():
#             return super().__getitem__(key)
#         else:
#             return self.fetch(key)


# class DiskBufferCache(Cache):

#     def __init__(self, *args, diskpath, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.diskpath = diskpath

#     def __fetch__(self, key):
#         with open(f'{self.diskpath}/{key}', 'rb') as file:
#             return file.read()

#     def __persist__(self, key):
#         with open(f'{self.diskpath}/{key}', 'wb+') as file:
#             value = super(Cache, self).__getitem__(key)
#             file.write(value)


# class RandomPolicyCache(Cache):

#     def __init__(self, *args, max_size, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.max_size = max_size

#     def policy(self):
#         keys = self.keys()
#         if len(keys) >= self.max_size and len(keys) > 0:
#             return keys[random.randint(0, len(keys)-1)]
#         else:
#             return None


# class TrackBufferCache(DiskBufferCache, RandomPolicyCache):
    
#     def __init__(self, *args, diskpath, max_size, **kwargs):
#         DiskBufferCache.__init__(self, *args, diskpath, **kwargs)
#         RandomPolicyCache.__init__(self, *args, max_size, **kwargs)
        

class TrackMetadata(BaseModel):
    title: str
    artist: str
    uri: str
    score: Optional[str] = None
    description: Optional[str] = None
    format: Optional[str] = None


class TrackProvider:

    def get_buffer(self, uri) -> bytes:
        raise NotImplementedError()
    
    def metadata(self, uri, **metadata):
        raise NotImplementedError()
        

class FLACProvider(TrackProvider):

    def __init__(self, user_id):
        self.directory = audio_dir(user_id)

    def get_buffer(self, uri) -> bytes:
        fpath = self.fpath(uri)
        if os.path.isfile(fpath):
            with open(fpath, 'br+') as file:
                return file.read()
        else:
            raise FileNotFoundError(f"{fpath} not found")

    def metadata(self, uri):
        fpath = self.fpath(uri)
        file = mutagen.File(fpath)
        return TrackMetadata(title=file.tags['TIT2'].text[0], artist=file.tags['TPE1'].text[0], uri=uri)

    def fpath(self, uri):
        return f"{self.directory}/{uri}"

class Entry:

    def fpath(self):
        raise NotImplementedError()

    def is_cached(self):
        return os.path.isfile(self.fpath())
    
    def load(self):
        raise NotImplementedError()

    def save(self, **kwargs):
        raise NotImplementedError()


class Track(Entry):

    cache: str
    providers: dict[Any, TrackProvider] = {}

    def from_uris(uris):
        tracks = []
        for uri in uris:
            try:
                track = Track(uri)
                track.save()
                tracks.append(track)
            except RuntimeError as error:
                print(f'Getting track {uri} failed with error:\n{repr(error)}\n', flush=True)
        return tracks

    def __init__(self, uri):
        self.cache = self.providers[FLACProvider].directory
        if uri is None:
            raise ValueError(f'`Track` object cannot be initialized without a `uri`.')
        self.uri = uri

    def fpath(self):
        return Path(f"{self.cache}/{self.uri}")
    
    def load(self):
        return torchaudio.load(self.__bytes__())

    def save(self):
        if not self.is_cached():
            metadata = self.metadata()
            os.makedirs(self.fpath().parent, exist_ok=True)
            torchaudio.save(self.fpath(), *self.load())
            self.metadata(metadata)

    def get_provider(self):
        if self.is_cached():
            return self.__class__.providers[FLACProvider]
        else:
            raise FileNotFoundError("Tried to use FLACProvider, but could not find file on disk")
        
    def metadata(self, **metadata):
        return self.get_provider().metadata(self.uri, **metadata)

    def __bytes__(self):
        return self.get_provider().get_buffer(self.uri)        

    def factory(module):
        # use
        # Track.factory(sys.modules[__name__])
        # to override `Track` with a subclass, allowing class attributes to be assigned in a new context
        class _Track(Track):
            differing_var = "ayoo"
        module.Track = _Track
        return _Track


class Description(Entry):

    def __init__(self, user_id, uri):
        self.user_id = user_id
        self.uri = uri

    def fpath(self):
        return Path(f"{text_dir(self.user_id)}/{self.uri}.json")

    def load(self):
        if self.is_cached():
            with open(self.fpath(), 'r') as file:
                return json.load(file)['text']
        else:
            raise FileNotFoundError(f"Could not find description file {self.fpath()}")

    def save(self, **data):
        os.makedirs(self.fpath().parent, exist_ok=True)
        with open(self.fpath(), 'w', encoding='utf-8') as file:
            json.dump(data, file)


class UserDataset(Dataset):

    def __init__(self, user_id, shuffle=True):
        self.user_id = user_id
        self.uris = [uri(file) for file in os.listdir(text_dir(user_id))]
        if shuffle:
            random.shuffle(self.uris)

    def get_description(self, uri):
        return Description(self.user_id, uri).load()
    
    def get_audio(self, uri):
        return Track(uri).load()

    def __len__(self):
        return len(self.uris)

    def __getitem__(self, idx):
        uri = self.uris[idx]
        return self.get_description(uri), self.get_audio(uri)
    


