#!/bin/sh

export $(xargs <.env)

mongoexport mongodb://${MONGO_USER}:${MONGO_PASS}@${MONGO_IP}:27017/?authSource=admin --db=${MONGO_DB} --collection=${DBLP_DATASET}_$(date +%d-%m-%Y) --out=${OUTPUT_DATASET_PATH}/$(date +%d-%m-%Y)/bip_ndr.jsonl
