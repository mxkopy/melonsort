docker run -it \
--entrypoint /bin/bash \
--env-file $PWD/.env \
--mount src=$PWD/src,dst=/srv/melonsort,type=bind \
--mount src=/mnt/d/wavs,dst=/wavs,type=bind \
--volume melonsort_hf:/hf \
--volume melonsort_data:/data \
--volume melonsort_embeds:/embeds \
--gpus all \
melonsort-melonsort
