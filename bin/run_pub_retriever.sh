#!/usr/bin/env bash

# Do a clean install
# mvn clean install

# Run the program.
cd $PUB_RETRIEVER_PATH/target || exit

batch_number=""
all_batches=false

# Parse options
while [[ "$#" -gt 0 ]]; do
    case "$1" in
        --batch)
            batch_number="$2"
            shift 2
            ;;
        --all)
            all_batches=true
            shift 1
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--batch <batch_number>] [--all]"
            exit 1
            ;;
    esac
done

# Function to process a single batch
process_batch() {
    local batch_number="$1"
    local command="java -jar publications_retriever-1.3-SNAPSHOT.jar -retrieveDataType document -downloadDocFiles -docFileNameType idName -firstDocFileNum 1 -docFilesStorage ${DBLP_CORPUS_PATH}/dblp-${LATEST_DATE}/DL_Object/output/DocFiles_${batch_number} < ${DBLP_CORPUS_PATH}/dblp-${LATEST_DATE}/DL_Object/input/input_batches/urls_batch_${batch_number}.jsonl > ${DBLP_CORPUS_PATH}/dblp-${LATEST_DATE}/DL_Object/output/urls_batch_${batch_number}_output.jsonl"
    echo -e "\nRunning: $command\n"
    
    eval "$command"
    
    echo "Finished processing batch ${batch_number}"
}

# Check if the script should process all batches
if [ "$all_batches" = true ]; then
    for batch_file in ${DBLP_CORPUS_PATH}/dblp-${LATEST_DATE}/DL_Object/input/input_batches/urls_batch_*.jsonl; do
        batch_number=$(basename "$batch_file" | sed 's/urls_batch_//' | sed 's/\.jsonl//')
        process_batch "$batch_number"
    done
# Otherwise, process the specified batch
elif [ -n "$batch_number" ]; then
    process_batch "$batch_number"
else
    echo "Error: You must specify either --batch <batch_number> or --all"
    echo "Usage: $0 [--batch <batch_number>] [--all]"
    exit 1
fi

cd $HOME_PATH