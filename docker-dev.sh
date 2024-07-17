docker run -it --entrypoint /bin/bash \
--mount src=$HOME/melonsort/src/$1,dst=/src,type=bind \
--volume melonsort_hf:/hf \
--volume melonsort_embeds:/embeds \
--volume melonsort_data:/data \
--volume melonsort_models:/models \
--gpus all \
melonsort-$1
