#!/bin/sh

# TODO: check all python scripts for argv input methods, change them to click

export $(xargs <.env)

./bin/make_dirs.sh  # initial structure 
echo "Make Directories (initial structure) - DONE"

python3 ./src/download_dblp_corpus.py
echo "Download DBLP Corpus - DONE"

export $(xargs <.env)

./bin/make_dirs.sh  # with latest date
echo "Make Directories (with latest release date) - DONE"

gunzip -k ${DBLP_CORPUS_PATH}/dblp-${LATEST_DATE}/dblp-${LATEST_DATE}.xml.gz

cp ${DBLP_CORPUS_PATH}/DTD/dblp-*.dtd ${DBLP_CORPUS_PATH}/dblp-${LATEST_DATE}/

python3 ./src/submodules/dblp-to-csv/XMLToCSV.py ${DBLP_CORPUS_PATH}/dblp-${LATEST_DATE}/dblp-${LATEST_DATE}.xml ${DBLP_CORPUS_PATH}/dblp-${LATEST_DATE}/dblp-*.dtd ${DBLP_CORPUS_PATH}/dblp-${LATEST_DATE}/dblp_${LATEST_DATE}.csv
echo "DBLP to CSV - DONE"

python3 ./src/metadata_extractor.py 0  # import_to_mongo
echo "Import to Mongo - DONE"

python3 ./src/metadata_extractor.py 1  # create_download_object
echo "Create Download Object - DONE"

./bin/split_dl_file.sh ${DBLP_CORPUS_PATH}/dblp-${LATEST_DATE}/DL_Object/input "input_urls.jsonl" "urls_batch_" 1000

./bin/run_pub_retriever.sh --all
echo "Publication Retriever - DONE"

mv ${DBLP_CORPUS_PATH}/dblp-${LATEST_DATE}/DL_Object/output/DocFiles_* ${PDF_PATH}
python3 ./src/grobid_pdf2tei.py 1 --batch all # --config 1
echo "GROBID PDF2TEI - DONE"

./bin/run_tei2json.sh --all  # executes -> python3 ./src/teixml2json_converter.py
echo "TEI2JSON - DONE"

python3 ./src/metadata_extractor.py 2 --batch all  # match_key_to_filename
echo "Match DBLP keys to filenames - DONE"

./bin/merge_batches.sh  # merge batches (in PDFs/TEI_XML/JSON)

python3 ./src/dataset_generator.py
echo "Dataset Generation - DONE"

./bin/run_mongoexport.sh
echo "Mongo Export - DONE"

./bin/run_total_citations_calculation.sh

./bin/rename_compress_dataset.sh
echo "Rename and compress dataset file - DONE"

./bin/get_dataset_size.sh ${OUTPUT_DATASET_PATH}/${LATEST_DATE}
