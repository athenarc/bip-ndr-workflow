#!/bin/sh

export $(xargs <.env)

./make_dirs.sh

python3 download_dblp_corpus.py

gunzip -k ${DBLP_CORPUS_PATH}dblp-${LATEST_DATE}/dblp-${LATEST_DATE}.xml.gz

python3 ./submodules/dblp-to-csv/XMLToCSV.py ${DBLP_CORPUS_PATH}dblp-${LATEST_DATE}/dblp-${LATEST_DATE}.xml ${DBLP_CORPUS_PATH}dblp-${LATEST_DATE}/dblp-*.dtd ${DBLP_CORPUS_PATH}dblp-${LATEST_DATE}/dblp_${LATEST_DATE}.csv

# make options for these two
# python3 metadata_extractor.py import_to_mongo
# python3 metadata_extractor.py create_download_object

# ./split_dl_file.sh

# java run publication retriever script

# python3 grobid_pdf2tei.py 1 DocFiles_*

# python3 teixml2json_converter.py

# make options for this
# python3 metadata_extractor.py match_key_to_filename

# script to merge batches (maybe)

# python3 dataset_generator.py

# ./run_mongoexport.sh

