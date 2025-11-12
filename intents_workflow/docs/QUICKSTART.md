# Quick Start Guide - Dataset Generator

Get started with the citation dataset generator in 5 minutes!

## Prerequisites

- Python 3.8+
- MongoDB running locally or remotely
- DBLP data loaded in MongoDB (optional for intents mode)

## 1. Installation

```bash
# Clone the repository (if not already done)
git clone https://github.com/allenai/s2orc-doc2json.git
cd s2orc-doc2json

# Create virtual environment
conda create -n doc2json python=3.8 pytest
conda activate doc2json

# Install dependencies
pip install -r requirements.txt
```

## 2. Environment Configuration

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your MongoDB credentials
nano .env  # or use your favorite editor
```

**Minimum .env configuration:**
```bash
MONGO_IP=localhost
MONGO_DB=DBLP
PAPERS_COL=manuscript_metadata
```

## 3. Test Installation

```bash
python test_installation.py
```

You should see:
```
✓ PASS    Imports
✓ PASS    Environment Config
✓ PASS    MongoDB Connection
✓ PASS    Citation Intent API
```

## 4. Choose Your Mode

**Option A: Full workflow with citation intents (recommended)**

**Input:** TEI XML files from Grobid

**Output:** Dataset with citation contexts and intent classifications

```bash
# If you don't have TEI XML files, generate them:
bash scripts/run_grobid.sh

# Configure paths in .env:
# TEI_PATH=tests/pdf/FullText_darko_Batch1
# MODE=TEI_XML_IN
# JSON_PATH=output/my_first_run/JSON_OUT

# Run dataset generator
python dataset_generator.py --mode intents
```

**What happens:**
1. ⏳ Converts TEI XML → S2ORC JSON (with DBLP enrichment)
2. ⏳ Extracts citations with context strings
3. ⏳ Classifies citation intents (Background, Methods, Results, etc.)
4. ⏳ Saves enriched dataset to MongoDB
5. ✅ Done! Check logs directory for results

---

### Option B: Bibliography Only (Faster)

**Input:** Existing JSON reference files

**Output:** Citation relationships without contexts

```bash
# Configure in .env:
# JSON_PATH=tests/json

# Run dataset generator
python dataset_generator.py --mode references
```

**What happens:**
1. ⏳ Reads JSON reference files
2. ⏳ Looks up DBLP IDs via MongoDB
3. ⏳ Saves bibliography to MongoDB
4. ✅ Done! Check logs for statistics

---

## 5. View Results

### Check Logs

```bash
cat output/my_first_run/logs/dataset_generator_*.log
```

Look for:
```
Total files checked: 150
Total DBLP keys matched: 2505
Papers with contexts: 2341  # Intents mode only
```

### Query MongoDB

```bash
# Open MongoDB shell
mongosh

# Switch to database
use DBLP

# List collections
show collections

# View a sample document
db.dblp_dataset_20241028_143022.findOne()
```

### Export to JSONL

```python
from pymongo import MongoClient
import json

client = MongoClient('localhost', 27017)
db = client['DBLP']

# Replace with your collection name
collection = db['dblp_dataset_20241028_143022']

with open('my_dataset.jsonl', 'w') as f:
    for doc in collection.find():
        doc.pop('_id', None)
        f.write(json.dumps(doc) + '\n')

print(f"Exported {collection.count_documents({})} documents")
```

---

## Example Output

### Example Output Structure

```
output/my_first_run/
├── JSON_OUT/
│   ├── paper_1.json              # Converted JSON (full text + metadata from TEI XML)
│   ├── paper_2.json
│   └── ...
├── S2ORC_JSONL_OUT/
│   ├── base/
│   │   ├── paper_1.jsonl         # Citation JSONL (S2ORC format)
│   │   └── ...
│   └── intents/
│       ├── paper_1_with_intent.jsonl  # Citation JSONL WITH intent classifications ✨
│       └── ...
└── logs/
    └── dataset_generator_intents_20241028_143022.log
```

### Sample Document (Intents Mode)

```json
{
  "citing_paper": {
    "dblp_id": "conf/example/Paper2024",
    "doi": "10.1234/example"
  },
  "cited_papers": [
    {
      "dblp_id": "conf/example/CitedPaper2023",
      "doi": "10.1234/cited",
      "bibliographic_reference": "Author et al., Title, Venue 2023",
      "citation_contexts": [
        {
          "section": "Introduction",
          "text": "Previous research [1] has shown...",
          "cite_start": 18,
          "cite_end": 21,
          "intent": "Background"
        }
      ]
    }
  ]
}
```

---

## Troubleshooting

### Issue: "Missing required environment variables"

**Solution:**
```bash
# Check .env file exists
ls -la .env

# Verify contents
cat .env

# Should contain:
MONGO_IP=localhost
MONGO_DB=DBLP
PAPERS_COL=manuscript_metadata
```

---

### Issue: "MongoDB connection failed"

**Solutions:**

1. **Check MongoDB is running:**
   ```bash
   # Linux/macOS
   sudo systemctl status mongod
   
   # Or try
   ps aux | grep mongod
   ```

2. **Start MongoDB:**
   ```bash
   # Linux
   sudo systemctl start mongod
   
   # macOS (Homebrew)
   brew services start mongodb-community
   
   # Docker
   docker run -d -p 27017:27017 mongo
   ```

3. **Test connection manually:**
   ```bash
   mongosh
   # Should connect without errors
   ```

---

### Issue: "No citation contexts loaded"

**Possible causes:**
- TEI XML files are invalid or empty
- Grobid processing failed
- Wrong input directory specified

**Solutions:**

1. **Verify TEI XML files exist:**
   ```bash
   ls -l tests/pdf/FullText_darko_Batch1/TEI_XML_IN/*.tei.xml
   ```

2. **Check TEI XML file content:**
   ```bash
   head -20 tests/pdf/FullText_darko_Batch1/TEI_XML_IN/sample.tei.xml
   # Should see XML with <biblStruct> elements
   ```

3. **Run Grobid again:**
   ```bash
   bash scripts/run_grobid.sh
   ```

---

## Next Steps

### Explore Output

1. **View converted JSON files (full text from TEI XML):**
   ```bash
   cat output/my_first_run/JSON_OUT/paper_1.json | jq .
   ```

2. **Check citation JSONL with intents:**
   ```bash
   cat output/my_first_run/S2ORC_JSONL_OUT/intents/paper_1_with_intent.jsonl | jq .
   ```

3. **Count intent distribution:**
   ```bash
   grep -oh '"citationIntent":"[^"]*"' output/my_first_run/S2ORC_JSONL_OUT/intents/*.jsonl | sort | uniq -c
   ```

### Advanced Usage

See detailed documentation:
- [DATASET_GENERATOR_CLI.md](DATASET_GENERATOR_CLI.md) - Complete CLI reference
- [DATASET_INTEGRATION_GUIDE.md](DATASET_INTEGRATION_GUIDE.md) - Integration details
- [CITATION_INTENT_GUIDE.md](CITATION_INTENT_GUIDE.md) - Intent classification

### Batch Processing

Process large batches:
```bash
# Process all files in directory
python dataset_generator.py \
    --mode intents \
    --tei-input /path/to/large/dataset/tei_xml \
    --output output/batch_$(date +%Y%m%d)
```

Monitor progress:
```bash
# Watch log file in real-time
tail -f output/batch_20241028/logs/dataset_generator_*.log
```

---

## Common Workflows

### Workflow 1: Process New PDFs

```bash
# 1. Place PDFs in input directory
cp my_papers/*.pdf tests/pdf/input/

# 2. Run Grobid to generate TEI XML
bash scripts/run_grobid.sh

# 3. Generate dataset with intents
python dataset_generator.py \
    --mode intents \
    --tei-input tests/pdf/TEI_XML_IN \
    --output output/$(date +%Y%m%d)

# 4. Export results
python export_to_jsonl.py
```

### Workflow 2: Update Existing Dataset

```bash
# 1. Process only new JSON files
python dataset_generator.py \
    --mode references \
    --json-input new_json_files/ \
    --output output/update_$(date +%Y%m%d)

# 2. MongoDB automatically handles duplicates
```

### Workflow 3: Test on Sample Data

```bash
# 1. Create test directory
mkdir -p test_run/tei_xml

# 2. Copy sample files
cp tests/pdf/2020.acl-main.207.tei.xml test_run/tei_xml/

# 3. Run on sample
python dataset_generator.py \
    --mode intents \
    --tei-input test_run/tei_xml \
    --output test_run/output

# 4. Verify results
cat test_run/output/logs/*.log
```

---

## Performance Tips

### Speed up processing:
- Use `--mode references` for faster bibliography-only processing
- Process files in parallel (split into batches)
- Use SSDs for faster I/O

### Reduce memory usage:
- Process smaller batches
- Clear output directories between runs
- Use streaming for large datasets

### Monitor progress:
```bash
# Count converted JSON files
ls {JSON_PATH}/*.json | wc -l

# Count citation JSONL files with intents
ls {S2ORC_JSONL_PATH}/intents/*_with_intent.jsonl | wc -l

# Check current processing
tail -f {LOGS_PATH}/*.log | grep "Processing"
```

---

## Getting Help

### Check Documentation
- [README.md](../README.md) - Project overview
- [DATASET_GENERATOR_CLI.md](DATASET_GENERATOR_CLI.md) - CLI reference
- [DATASET_INTEGRATION_GUIDE.md](DATASET_INTEGRATION_GUIDE.md) - Technical details

### Debug Issues
1. Check log files in `output/*/logs/`
2. Run `python test_installation.py`
3. Verify MongoDB connection
4. Check input file formats

### Report Issues
- Include log files
- Describe input data
- Share error messages
- Specify mode (intents/references)

---

## Summary

You've successfully:
✅ Installed the dataset generator  
✅ Configured environment variables  
✅ Run your first dataset generation  
✅ Viewed results in MongoDB  

**Next:** Explore the full documentation for advanced features!

---

**Happy dataset generation! 🚀**
