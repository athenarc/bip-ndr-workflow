#!/bin/bash

if [ -z "$1" ]; then
    echo "Usage: $0 <file_or_directory_or_wildcard>"
    exit 1
fi

echo -e "\n------------\nDataset Size\n------------"

for file in "$1"/* "$1"; do
    if [ -e "$file" ]; then
        filename=$(basename "$file")

        du -B1 "$file" | awk -v name="$filename" '{printf "%s: %.1f MB\n", name, $1/1024/1024}'
    fi
done
