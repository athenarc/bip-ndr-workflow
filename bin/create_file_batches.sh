#!/bin/bash

export $(xargs <.env)

# Check if the correct number of arguments is provided
if [ $# -ne 3 ]; then
  echo "Usage: $0 <source_directory> <files_per_subdirectory> <subdir_prefix>"
  exit 1
fi

# Assign the arguments to variables
SOURCE_DIR="$1"
FILES_PER_SUBDIR="$2"
SUBDIR_PREFIX="$3"

# Initialize a counter for subdirectory naming and tracking files moved
counter=0
file_counter=0

# Check if the source directory exists
if [ ! -d "$SOURCE_DIR" ]; then
  echo "Source directory $SOURCE_DIR does not exist."
  exit 1
fi

# Loop through the files in the source directory
for file in "$SOURCE_DIR"/*; do
  # If the file counter is a multiple of the user-specified number, create a new subdirectory
  if [ $((file_counter % FILES_PER_SUBDIR)) -eq 0 ]; then
    subdir="${SOURCE_DIR}/${SUBDIR_PREFIX}_$(printf "%03d" $counter)"
    mkdir -p "$subdir"
    ((counter++))
  fi

  # Move the file to the current subdirectory
  mv "$file" "$subdir"

  # Increment the file counter
  ((file_counter++))
done

echo "Files have been successfully split into subdirectories."
