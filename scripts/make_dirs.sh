#!/bin/sh

export $(xargs <.env)

mkdir -p $PDF_PATH
mkdir -p $TEI_PATH
mkdir -p $JSON_PATH
mkdir -p $DBLP_CORPUS_PATH
mkdir -p $LOGS_PATH
mkdir -p $PUB_RETRIEVER_PATH/DBLP/
mkdir -p $OUTPUT_DATASET_PATH/$(date +%d-%m-%Y)