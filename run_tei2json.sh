if [ $# -ne 1 ]; then
    echo "Usage: $0 <batch_number>"
    exit 1
fi

batch_number="$1"

python3 ./src/teixml2json_converter.py --in_path "/home/pkoloveas/Desktop/dblp_corpus/full_corpus/TEI_XML/References/DocFiles_${batch_number}/" --out_path "/home/pkoloveas/Desktop/dblp_corpus/full_corpus/json_references/DocFiles_${batch_number}/" --yes
