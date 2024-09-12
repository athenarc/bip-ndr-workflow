#!/bin/bash

# Check if jq is installed
command -v jq >/dev/null 2>&1 || { echo >&2 "jq is required but not installed. Aborting."; exit 1; }

# Check for correct number of arguments
if [ $# -ne 4 ]; then
    echo "Usage: $0 <input_directory> <input_file.jsonl> <output_prefix> <batch_size>"
    exit 1
fi

input_directory="$1"
input_file="$2"
output_prefix="$3"
batch_size="$4"

# Count total lines in the input file
total_lines=$(wc -l < "$input_directory/$input_file")

# Calculate the number of batches
num_batches=$(( (total_lines + batch_size - 1) / batch_size ))

if [ ! -d "$input_directory/input_batches" ]; then
    mkdir "$input_directory/input_batches"
fi

# Split the input file into batches
split -a 3 -dl "$batch_size" "$input_directory/$input_file" "$input_directory/input_batches/$output_prefix" 

# Rename the split files with .jsonl extension
# for ((i=0; i<num_batches; i++)); do
#     new_filename="${output_prefix}_batch${i}.jsonl"
#     mv "${output_prefix}aa" "$new_filename"
# done

for f in $input_directory/input_batches/$output_prefix*; do mv "$f" "$f.jsonl"; done

echo "Split into $num_batches batches."
