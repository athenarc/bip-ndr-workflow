#!/bin/sh

export $(xargs <.env)

# Initialize variables
batch_number=""
all_batches=false

# Parse options
while [ "$#" -gt 0 ]; do
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
    python3 src/teixml2json_converter.py --in_path "${TEI_PATH}/${MODE}/DocFiles_${batch_number}/" --out_path "${JSON_PATH}/${MODE}/DocFiles_${batch_number}/" --yes
    echo "Finished processing batch ${batch_number}"
}

# Check if the script should process all batches
if [ "$all_batches" = true ]; then
    for batch_dir in ${TEI_PATH}/${MODE}/DocFiles_*; do
        batch_number=$(basename "$batch_dir" | sed 's/DocFiles_//')
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