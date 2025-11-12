# Dataset Generator CLI

Command-line interface for generating citation datasets from scientific papers with optional citation intent enrichment.

## Overview

The dataset generator supports two modes:

1. **Intents Mode**: Full workflow including citation context extraction and intent classification
2. **References Mode**: Bibliography-only processing (original behavior)

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your MongoDB credentials
```

## Environment Configuration

Create a `.env` file with the following variables:

```bash
# MongoDB Configuration (Required)
MONGO_IP=localhost
MONGO_DB=DBLP
PAPERS_COL=manuscript_metadata

# MongoDB Authentication (Optional)
MONGO_USER=your_username
MONGO_PASS=your_password
```

## Usage

### Intents Mode (Full Workflow)

Processes TEI XML files → S2ORC JSON → Citation JSONL → Intent Enrichment → MongoDB

```bash
# Configure in .env:
# TEI_PATH=tests/pdf/FullText_darko_Batch1
# MODE=TEI_XML_IN
# JSON_PATH=output/JSON_OUT

# Run:
python dataset_generator.py --mode intents
```

**What it does:**
1. Converts TEI XML files to S2ORC JSON format
2. Enriches bibliography with DBLP IDs via MongoDB lookup
3. Generates citation JSONL files with context strings
4. Enriches citations with intent predictions (Background, Methods, Results, etc.)
5. Loads citation contexts and matches with bibliography
6. Saves enriched dataset to MongoDB

**Output:**
- `{JSON_PATH}/*.json` - Converted JSON files (from TEI XML, contains full text and metadata)
- `{S2ORC_JSONL_PATH}/base/*.jsonl` - Citation JSONL in S2ORC format
- `{S2ORC_JSONL_PATH}/intents/*_with_intent.jsonl` - Citation JSONL with intent classifications
- `{LOGS_PATH}/dataset_generator_intents_*.log` - Execution log
- MongoDB collection: `dblp_dataset_YYYYMMDD_HHMMSS`

**Output Format:**
```json
{
  "citing_paper": {
    "dblp_id": "conf/example/Paper2024",
    "doi": "10.xxxx/xxxxx"
  },
  "cited_papers": [
    {
      "dblp_id": "conf/example/CitedPaper2023",
      "doi": "10.xxxx/yyyyy",
      "bibliographic_reference": "Author et al., Title, Venue 2023",
      "citation_contexts": [
        {
          "citation_id": "conf_example_Paper2024_conf_example_CitedPaper2023_CIT0",
          "section": "Introduction",
          "text": "Previous work [1] demonstrated...",
          "cite_start": 15,
          "cite_end": 18,
          "intent": "background information"
        }
      ]
    }
  ]
}
```

---

### References Mode (Bibliography Only)

Processes existing JSON reference files → MongoDB (no citation contexts)

```bash
# Configure in .env:
# JSON_PATH=tests/json

# Run:
python dataset_generator.py --mode references
```

**What it does:**
1. Reads existing JSON reference files (from previous Grobid processing)
2. Looks up DBLP IDs via MongoDB (DOI → Title fallback)
3. Saves bibliography relationships to MongoDB (no citation contexts)

**Output:**
- `{LOGS_PATH}/dataset_generator_references_*.log` - Execution log
- MongoDB collection: `dblp_dataset_YYYYMMDD_HHMMSS`

**Output Format:**
```json
{
  "citing_paper": {
    "dblp_id": "conf/example/Paper2024",
    "doi": "10.xxxx/xxxxx"
  },
  "cited_papers": [
    {
      "dblp_id": "conf/example/CitedPaper2023",
      "doi": "10.xxxx/yyyyy",
      "bibliographic_reference": "Author et al., Title, Venue 2023"
    }
  ]
}
```

---

## Command-Line Arguments

### Required Arguments

- `--mode {intents|references}` - Mode of operation
- `--output OUTPUT` - Output directory for generated files and logs

### Mode-Specific Arguments

**For Intents Mode:**
- `--tei-input TEI_INPUT` - Input directory containing TEI XML files

**For References Mode:**
- `--json-input JSON_INPUT` - Input directory containing JSON reference files

---

## Examples

### Example 1: Process PDFs with Citation Intents

```bash
# Step 1: Generate TEI XML files using Grobid
bash scripts/run_grobid.sh

# Step 2: Run dataset generator in intents mode
python dataset_generator.py \
    --mode intents \
    --tei-input tests/pdf/FullText_darko_Batch1/TEI_XML_IN \
    --output output/intents_run_$(date +%Y%m%d)
```

### Example 2: Process Pre-existing JSON Files

```bash
# Run in references mode with existing JSON files
python dataset_generator.py \
    --mode references \
    --json-input /path/to/json/files \
    --output output/references_run_$(date +%Y%m%d)
```

### Example 3: Test with Sample Data

```bash
# Create test directory
mkdir -p test_data/tei_xml

# Copy sample TEI XML files
cp tests/pdf/2020.acl-main.207.tei.xml test_data/tei_xml/

# Run with single file
python dataset_generator.py \
    --mode intents \
    --tei-input test_data/tei_xml \
    --output output/test_run
```

---

## Output Structure

```
output/
├── JSON_OUT/                              # Converted JSON files (full text + metadata)
│   ├── paper_1.json
│   ├── paper_2.json
│   └── ...
├── S2ORC_JSONL_OUT/
│   ├── base/                              # Citation JSONL (S2ORC format)
│   │   ├── paper_1.jsonl
│   │   ├── paper_2.jsonl
│   │   └── ...
│   └── intents/                           # Citation JSONL with intent predictions
│       ├── paper_1_with_intent.jsonl
│       ├── paper_2_with_intent.jsonl
│       └── ...
└── logs/                                  # Execution logs
    ├── dataset_generator_intents_20241028_143022.log
    └── dataset_generator_references_20241028_150145.log
```

---

## Statistics Tracking

The generator tracks comprehensive statistics in MongoDB:

```json
{
  "key": "statistics",
  "total_files_checked": 150,
  "total_refs_checked": 2847,
  "total_refs_skipped": 342,
  "total_dois_matched": 1823,
  "total_dois_dblp": 156,
  "total_dblp_keys_matched": 2505,
  "total_contexts_added": 4521,         // Intents mode only
  "papers_with_contexts": 2341,         // Intents mode only
  "papers_without_contexts": 164        // Intents mode only
}
```

Statistics are saved to MongoDB collection: `stats_YYYYMMDD_HHMMSS`

---

## Citation Intent Categories

### Production: SciCite 3-Class Taxonomy

When using an external API in production, citations are classified using the **SciCite 3-class taxonomy**:

| Intent Category | Definition | Example Context |
|--------|-------------|-----------------|
| **background information** | Citations providing context, background, or foundational information about a problem, concept, approach, topic, or field importance | "Previous research [1] established the theoretical foundation..." |
| **method** | Citations of methods, tools, approaches, datasets, or frameworks being used, extended, or adapted | "Following the approach of [2], we extract features using..." |
| **results comparison** | Citations comparing the paper's results or findings with results/findings from other work | "Our results outperform the baseline [3] by 15%..." |

**Reference:** Cohan et al. "Structural Scaffolds for Citation Intent Classification in Scientific Publications" (NAACL 2019)

### Testing: Mock API 6-Class Scheme

The `MockCitationIntentAPI` uses a richer 6-class scheme for detailed testing:

| Intent | Description |
|--------|-------------|
| **Background** | Foundational work or context |
| **Motivation** | Work that motivates the current research |
| **Methods** | Methodologies or techniques being used |
| **Results** | Comparative results or findings |
| **Future** | Future work directions |
| **Extension** | Extending previous work |

This allows for more nuanced heuristics during development and testing. Replace with the [BIP! Citation Intent Classifier](https://github.com/athenarc/bip-citation-classifier) for production use.

---

## Workflow Diagrams

### Intents Mode Workflow

```
TEI XML Files
    ↓
Convert to S2ORC JSON (with DBLP enrichment)
    ↓
Generate Citation JSONL (citing → cited relationships)
    ↓
Enrich with Citation Intents (MockCitationIntentAPI)
    ↓
Load Citation Contexts into Memory
    ↓
Process JSON Reference Files
    ↓
Match Citation Contexts by DBLP ID
    ↓
Save Enriched Dataset to MongoDB
```

### References Mode Workflow

```
JSON Reference Files
    ↓
Parse Bibliography Entries
    ↓
Lookup DBLP IDs (DOI → Title fallback)
    ↓
Save Bibliography Relationships to MongoDB
```

---

## Troubleshooting

### Issue: Missing MongoDB Connection

```
Error: Missing required environment variables: MONGO_IP, MONGO_DB, PAPERS_COL
```

**Solution:** Create `.env` file with MongoDB configuration:
```bash
MONGO_IP=localhost
MONGO_DB=DBLP
PAPERS_COL=manuscript_metadata
```

---

### Issue: No Citation Contexts Loaded

```
Loaded 0 citation contexts for 0 citing papers
```

**Solution:** Verify TEI XML files were processed successfully:
```bash
ls -l {S2ORC_JSONL_PATH}/intents/*_with_intent.jsonl
```

If no files exist, check:
1. TEI XML files are valid and contain `<ref>` elements
2. Grobid processed PDFs correctly
3. No errors in log file
4. Citation JSONL files were generated in the base/ folder first

---

### Issue: DBLP ID Mismatches

```
Papers without contexts: 450
Papers with contexts: 12
```

**Possible Causes:**
1. DBLP IDs in citation contexts don't match bibliography
2. Papers not in DBLP database
3. Title/DOI matching failed

**Solution:** Check logs for matching statistics:
```bash
grep "DBLP KEY" output/logs/*.log | wc -l
grep "No DOI or Title match" output/logs/*.log | wc -l
```

---

### Issue: Permission Denied on MongoDB

```
pymongo.errors.OperationFailure: Authentication failed
```

**Solution:** Add MongoDB credentials to `.env`:
```bash
MONGO_USER=your_username
MONGO_PASS=your_password
```

---

## Performance Considerations

### Processing Speed

| Mode | Files/Hour | Notes |
|------|-----------|-------|
| Intents | ~100-150 | Depends on file size, citation density |
| References | ~500-1000 | Only bibliography processing |

### Memory Usage

- **Intents Mode:** ~2-4 GB (loads all citation contexts)
- **References Mode:** ~500 MB - 1 GB

For large datasets (>10,000 files):
- Process in batches
- Monitor memory usage
- Consider streaming approach for citation contexts

---

## Exporting Results

### Export from MongoDB to JSONL

```python
from pymongo import MongoClient
import json

client = MongoClient('localhost', 27017)
db = client['DBLP']
collection = db['dblp_dataset_20241028_143022']

with open('final_dataset.jsonl', 'w', encoding='utf-8') as f:
    for doc in collection.find():
        doc.pop('_id', None)  # Remove MongoDB ID
        f.write(json.dumps(doc, ensure_ascii=False) + '\n')

print(f"Exported {collection.count_documents({})} documents")
```

### Query Statistics

```python
from pymongo import MongoClient

client = MongoClient('localhost', 27017)
db = client['DBLP']

# Get statistics
stats = db['stats_20241028_143022'].find_one({"key": "statistics"})
print(json.dumps(stats, indent=2))

# Count papers with citation contexts
dataset = db['dblp_dataset_20241028_143022']
papers_with_contexts = dataset.count_documents({
    "cited_papers.citation_contexts": {"$exists": True, "$ne": []}
})
print(f"Papers with contexts: {papers_with_contexts}")
```

---

## Advanced Usage

### Custom Citation Intent API

Replace `MockCitationIntentAPI` with your own implementation:

```python
# In dataset_generator.py, replace:
intent_api = MockCitationIntentAPI()

# With:
from my_intent_api import CustomCitationIntentAPI
intent_api = CustomCitationIntentAPI(api_url="https://api.example.com/intent")
```

Your API must implement:
```python
class CustomCitationIntentAPI:
    def predict_intent(self, citation_string: str, section: str) -> str:
        """Return one of: Background, Methods, Results, Motivation, Future, Other"""
        pass
    
    def batch_predict(self, citations: List[Dict]) -> List[str]:
        """Batch prediction for efficiency"""
        pass
```

---

### Parallel Processing

For large batches, process files in parallel:

```bash
# Split input files into batches
split -n l/4 file_list.txt batch_

# Run in parallel
python dataset_generator.py --mode intents --tei-input batch1/ --output output1/ &
python dataset_generator.py --mode intents --tei-input batch2/ --output output2/ &
python dataset_generator.py --mode intents --tei-input batch3/ --output output3/ &
python dataset_generator.py --mode intents --tei-input batch4/ --output output4/

# Wait for all to complete
wait

# Merge results in MongoDB
python merge_collections.py output1/ output2/ output3/ output4/
```

---

## Integration with Existing Workflows

### Use with Grobid Processing

```bash
# 1. Setup Grobid
bash scripts/setup_grobid.sh

# 2. Process PDFs to TEI XML
bash scripts/run_grobid.sh

# 3. Run dataset generator
python dataset_generator.py \
    --mode intents \
    --tei-input tests/pdf/FullText_darko_Batch1/TEI_XML_IN \
    --output output/$(date +%Y%m%d)
```

### Use with Existing JSON Files

If you already have JSON reference files from a previous Grobid run:

```bash
python dataset_generator.py \
    --mode references \
    --json-input /path/to/existing/json \
    --output output/references_$(date +%Y%m%d)
```

---

## Validation

### Verify Output Quality

```python
import json
from pymongo import MongoClient

client = MongoClient('localhost', 27017)
db = client['DBLP']
collection = db['dblp_dataset_20241028_143022']

# Sample random documents
sample_docs = list(collection.aggregate([{"$sample": {"size": 10}}]))

for doc in sample_docs:
    print(f"\nCiting Paper: {doc['citing_paper']['dblp_id']}")
    print(f"Cited Papers: {len(doc['cited_papers'])}")
    
    # Check citation contexts
    with_contexts = [p for p in doc['cited_papers'] if 'citation_contexts' in p]
    print(f"Papers with contexts: {len(with_contexts)}")
    
    if with_contexts:
        # Show first citation context
        first_context = with_contexts[0]['citation_contexts'][0]
        print(f"Sample context:")
        print(f"  Section: {first_context['section']}")
        print(f"  Intent: {first_context['intent']}")
        print(f"  Text: {first_context['text'][:100]}...")
```

---

## Post-Processing: Dataset Stripping

For legal/copyright compliance, you can create a **stripped version** of the dataset that removes citation text snippets while preserving intent labels and citation graph structure.

```bash
# Strip the dataset for publication
python strip_dataset.py --source-collection dataset --target-collection dataset_stripped

# Preview before stripping
python strip_dataset.py --source-collection dataset --target-collection dataset_stripped --dry-run
```

⚠️ **Important**: This is a ONE-WAY transformation. Always keep the full dataset privately for research.

**See**: [DATASET_STRIPPING_GUIDE.md](DATASET_STRIPPING_GUIDE.md) for complete documentation.

---

## FAQ

**Q: Can I run both modes on the same dataset?**

A: Yes, but they create separate MongoDB collections. Intents mode includes everything from references mode plus citation contexts.

**Q: How long does processing take?**

A: For intents mode, expect ~30-60 seconds per file (depends on citations). References mode is much faster (~1-5 seconds per file).

**Q: Can I resume a failed run?**

A: Yes, the script checks `reference_file_parsed` status in MongoDB. Already processed papers are skipped. Use `reset_papers_collection()` to reprocess.

**Q: What's the difference between the two modes?**

A:
- **Intents**: Full citation analysis (where, how, why papers cited)
- **References**: Bibliography only (who cited whom)

**Q: Do I need Grobid installed?**

A: Only for generating TEI XML files. If you have pre-generated TEI XML or JSON files, you don't need Grobid.

---
