#!/bin/sh

export $(xargs <.env)

# ./make_dirs.sh

# python3 download_dblp_corpus.py  # TODO modify to add $LATEST_DATE in .env file

# gunzip -k ${DBLP_CORPUS_PATH}dblp-${LATEST_DATE}/dblp-${LATEST_DATE}.xml.gz

# python3 ./submodules/dblp-to-csv/XMLToCSV.py ${DBLP_CORPUS_PATH}dblp-${LATEST_DATE}/dblp-${LATEST_DATE}.xml ${DBLP_CORPUS_PATH}dblp-${LATEST_DATE}/dblp-*.dtd ${DBLP_CORPUS_PATH}dblp-${LATEST_DATE}/dblp_${LATEST_DATE}.csv

# python3 metadata_extractor.py 0  # import_to_mongo
# python3 metadata_extractor.py 1  # create_download_object

# ./split_dl_file.sh ${PUB_RETRIEVER_PATH}DBLP/dblp-${LATEST_DATE}/input "input_urls.jsonl" "urls_batch_" 1000

# java run publication retriever script  # TODO create script to generate runner file

# python3 grobid_pdf2tei.py 1 DocFiles_*

# ./run_tei2json.sh 000  # executes -> python3 teixml2json_converter.py

# make options for this ->  # TODO add option to run on subfolder
# python3 metadata_extractor.py 2  # match_key_to_filename

# script to merge batches (in PDFs/TEI_XML/json_references) (maybe)
# mv DocFiles_*/* .
# rm -rf DocFiles_*

# python3 dataset_generator.py

./run_mongoexport.sh

