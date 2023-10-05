#!/bin/sh

export $(xargs <.env)

if [ $# -ne 1 ]; then
    echo "Usage: $0 <batch_number>"
    exit 1
fi

batch_number="$1"

python3 teixml2json_converter.py --in_path "${TEI_PATH}References/DocFiles_${batch_number}/" --out_path "${JSON_PATH}DocFiles_${batch_number}/" --yes
