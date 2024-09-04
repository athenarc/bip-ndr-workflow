#!/bin/sh

# TODO: check all python scripts for argv input methods, change them to click

export $(xargs <.env)

./make_dirs.sh 

python3 download_dblp_corpus.py

export $(xargs <.env)

gunzip -k ${DBLP_CORPUS_PATH}/dblp-${LATEST_DATE}/dblp-${LATEST_DATE}.xml.gz

python3 ./submodules/dblp-to-csv/XMLToCSV.py ${DBLP_CORPUS_PATH}/dblp-${LATEST_DATE}/dblp-${LATEST_DATE}.xml ${DBLP_CORPUS_PATH}/dblp-${LATEST_DATE}/dblp-*.dtd ${DBLP_CORPUS_PATH}/dblp-${LATEST_DATE}/dblp_${LATEST_DATE}.csv

python3 metadata_extractor.py 0  # import_to_mongo
python3 metadata_extractor.py 1  # create_download_object

./split_dl_file.sh ${DBLP_CORPUS_PATH}/dblp-${LATEST_DATE}/DL-Object/input "input_urls.jsonl" "urls_batch_" 1000

./run_pub_retriever.sh --all

mv ${DBLP_CORPUS_PATH}/dblp-${LATEST_DATE}/DL_Object/output/DocFiles_* ${PDF_PATH}
python3 grobid_pdf2tei.py 1 DocFiles_*

./run_tei2json.sh --all  # executes -> python3 teixml2json_converter.py

python3 metadata_extractor.py 2 --batch all  # match_key_to_filename

./merge_batches.sh  # merge batches (in PDFs/TEI_XML/JSON)

python3 dataset_generator.py

./run_mongoexport.sh
./run_total_citations_calculation.sh
./rename_compress_dataset.sh