from transformers import ClapModel, ClapProcessor, ClapFeatureExtractor, RobertaTokenizer
import torch, torchaudio, spotify, os

def get_audio_embeds(processor, model, track, cache='/embeds'):
    cached_file = lambda : os.path.join(cache, track['uri'] + '.pt')
    is_cached = lambda : os.path.isfile(cached_file())
    def from_computed():
        data, sampling_rate = track['data_getter']()
        audios = torchaudio.functional.resample(data, sampling_rate, processor.feature_extractor.sampling_rate)
        audios = audios.tolist()
        audio_inputs = processor(audios=audios, sampling_rate=processor.feature_extractor.sampling_rate, padding=True, return_tensors="pt")
        audio_inputs['input_features'] = audio_inputs['input_features'].type(torch.float16)
        audio_inputs.to('cuda')
        audio_embeds = model.get_audio_features(**audio_inputs)
        if cache:
            torch.save(audio_embeds, cached_file())
        return audio_embeds

    def from_cache():
        audio_embeds = torch.load(cached_file()).to('cuda')
        return audio_embeds

    return from_computed() if not cache or not is_cached() else from_cache()

def get_text_embeds(processor, model, text):
    text_inputs      = processor(text=text, padding=True, return_tensors="pt").to('cuda')
    text_embeds      = model.get_text_features(**text_inputs)
    return text_embeds

def text_audio_similarity(model, text_embeds, audio_embeds):
    logit_scale_text = model.logit_scale_t.exp()
    logits_per_text  = torch.matmul(text_embeds, audio_embeds.t()) * logit_scale_text
    score = torch.sum(logits_per_text)
    return score.detach().item()

def sort_audio_by_text_prompt(processor, model, text, tracks, user_info):
    track_list = []
    text_embeds = get_text_embeds(processor, model, text)
    # TODO: parallelize 
    for track in tracks:
        try:
            audio_embeds = get_audio_embeds(processor, model, track, cache=f"/embeds/{user_info['id']}")
            track['score'] = text_audio_similarity(model, text_embeds, audio_embeds)
            track_list.append(track)
            print("Song scored!", flush=True)
        except Exception as e:
            print(f"Cannot embed with exception: {repr(e)}")
    track_list.sort(key=lambda track: track['score'], reverse=True)
    return track_list

