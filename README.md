# Melonsort
This repository uses Contrastive Language-Audio Pretraining to rank songs according to a descriptive tag. 

## Usage 
Run `docker compose up melonsort` to start the service. Once you've done that, you can head to `http://localhost` on your browser to use the application. 

### Searching
You can drag + drop audio files into the window to load them. Then, type your query in the search box, and hit `search!` to sort your tracks. 

Tracks with higher scores match more closely to your query than tracks with lower scores. However, this is far from a perfect science, so expect lukewarm results (for the time being `>:D`).

### Training
If you'd like to alter how the model thinks about your tracks, you can label them using the text inputs on the right. Hitting the `train!` button will fine-tune the model to agree with your descriptions.