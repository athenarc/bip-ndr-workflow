#!/bin/sh

export $(xargs <.env)

mv ${OUTPUT_DATASET_PATH}/${LATEST_DATE}/bip_ndr.jsonl ${OUTPUT_DATASET_PATH}/${LATEST_DATE}/bip_ndr_${DATASET_VERSION}.jsonl
tar -czvf ${OUTPUT_DATASET_PATH}/${LATEST_DATE}/bip_ndr_${DATASET_VERSION}.tar.gz ${OUTPUT_DATASET_PATH}/${LATEST_DATE}/bip_ndr_${DATASET_VERSION}.jsonl 