import torch
import transformers

from data import UserDataset
from semantic_audio import Embeddings, model_dir
from torch.utils.data import Dataset


class TrainingDataset(Dataset):

    model: Embeddings

    def __init__(self, model, batch_size=1, shuffle=True):
        self.batch_size = batch_size
        self.dataset = UserDataset(model.user_id, shuffle=shuffle)
        self.model = model

    def __len__(self):
        return len(self.dataset) // self.batch_size
    
    def collate(batch):
        collated = {}
        max_attention_mask_len = max( map(lambda feature: feature['attention_mask'].size(1), batch) )
        for feature in batch:
            for key in feature.keys():
                if key == 'attention_mask' or key == 'input_ids':
                    end_padding = feature[key][:, -1].repeat(max_attention_mask_len - feature[key].size(1)).unsqueeze(0)
                    feature[key] = torch.cat([feature[key], end_padding], dim=1)
                collated[key] = feature[key] if not key in collated else torch.cat([collated[key], feature[key]], dim=0)
        collated['input_features'] = collated['input_features'].type(torch.float32)
        collated['input_features'].to('cuda')
        return collated

    def __getitem__(self, idx):
        description, (audio, sampling_rate) = self.dataset[idx]
        audio, sampling_rate = self.model._preprocess_audio(audio, sampling_rate)
        inputs = self.model._process(audios=audio, text=description[0], sampling_rate=sampling_rate)
        return inputs

class Trainer(transformers.Trainer):

    def compute_loss(self, model, inputs, return_outputs=False):
        outputs = model(**inputs, return_loss=True)
        loss = outputs["loss"]
        return (loss, outputs) if return_outputs else loss
