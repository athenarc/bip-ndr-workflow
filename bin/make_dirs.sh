#!/bin/sh

export $(xargs <.env)

mkdir -p $PDF_PATH
mkdir -p ${TEI_PATH}/${MODE}
mkdir -p ${JSON_PATH}/${MODE}
mkdir -p $DBLP_CORPUS_PATH
mkdir -p ${LOGS_PATH}/${LATEST_DATE}
mkdir -p $PUB_RETRIEVER_PATH/DBLP/
mkdir -p $OUTPUT_DATASET_PATH/${LATEST_DATE}
