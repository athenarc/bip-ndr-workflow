#!/bin/sh

export $(xargs <.env)

./scripts/make_dirs.sh

python3 ./src/download_dblp_corpus.py

gunzip -k ${DBLP_CORPUS_PATH}dblp-${LATEST_DATE}/dblp-${LATEST_DATE}.xml.gz

python3 ./submodules/dblp-to-csv/XMLToCSV.py ${DBLP_CORPUS_PATH}dblp-${LATEST_DATE}/dblp-${LATEST_DATE}.xml ${DBLP_CORPUS_PATH}dblp-${LATEST_DATE}/dblp-*.dtd ${DBLP_CORPUS_PATH}dblp-${LATEST_DATE}/dblp_${LATEST_DATE}.csv

# make options for these two
# python3 ./src/metadata_extractor.py import_to_mongo
# python3 ./src/metadata_extractor.py create_download_object

# ./scripts/split_dl_file.sh

# java run publication retriever script

# python3 ./src/grobid_pdf2tei.py 1 DocFiles_*

# python3 ./src/teixml2json_converter.py

# make options for this
# python3 ./src/metadata_extractor.py match_key_to_filename

# script to merge batches (maybe)

# python3 ./src/dataset_generator.py

# ./run_mongoexport.sh

