# Citation Dataset Generator with Intent Classification

A comprehensive pipeline for generating citation datasets from scientific papers with optional citation intent classification. This tool processes scientific literature to extract citation relationships, context strings, and classify citation intents (Background, Methods, Results, etc.).

## Overview

This repository provides a complete end-to-end CLI tool for building citation datasets from scientific papers. The pipeline enriches bibliographic data with DBLP identifiers, extracts citation contexts from full text, and optionally classifies the intent behind each citation.

**Key Features:**
- 🔄 **Two Processing Modes**: Full intent analysis or fast bibliography-only extraction
- 🎯 **Citation Intent Classification**: Classify citations into 6 categories (Background, Methods, Results, etc.)
- 🗄️ **MongoDB Integration**: Scalable storage with automatic indexing and statistics tracking
- 📊 **Cumulative Statistics**: Track dataset growth across multiple runs
- 🔍 **DBLP Enrichment**: Automatic lookup and linking to DBLP bibliographic database
- ⚡ **Performance Optimized**: Early duplicate detection, MongoDB indexes, incremental processing
- 🔧 **Dataset Stripping**: Remove sensitive information for publication

> **Note:** Some helper functions have been partially adapted from [github.com/allenai/s2orc-doc2json](https://github.com/allenai/s2orc-doc2json).

## Quick Start

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/s2orc-doc2json.git
cd s2orc-doc2json

# Create virtual environment (Python 3.8+)
conda create -n doc2json python=3.8 pytest
conda activate doc2json

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy example configuration
cp .env.example .env

# Edit .env with your settings
nano .env
```

**Minimum required configuration:**
```bash
MONGO_IP=localhost
MONGO_DB=DBLP
PAPERS_COL=manuscript_metadata
DATASET_COL=dblp_dataset
STATS_COL=parsing_statistics
```

### 3. Run Dataset Generator

**Option A: Full workflow with citation intents (recommended)**
```bash
python dataset_generator.py --mode intents --output output/
```

**Option B: Bibliography only (faster)**
```bash
python dataset_generator.py --mode references --output output/
```

**For detailed setup and troubleshooting, see [docs/QUICKSTART.md](docs/QUICKSTART.md)**

## Core Scripts

### Primary Tools

| Script | Purpose | Usage |
|--------|---------|-------|
| **`dataset_generator.py`** | Main pipeline for generating citation datasets | `python dataset_generator.py --mode [intents\|references]` |
| **`strip_dataset.py`** | Remove sensitive information from datasets for publication | `python strip_dataset.py --source-collection dataset --target-collection dataset_stripped` |
| **`test_installation.py`** | Validate installation and configuration | `python test_installation.py` |

### Dataset Generator Modes

#### Intents Mode (Full Pipeline)

Processes TEI XML → S2ORC JSON → Citation JSONL → Intent Classification → MongoDB

```bash
python dataset_generator.py --mode intents --fresh-start
```

**Output includes:**
- Converted JSON files (full text and metadata from TEI XML)
- Citation JSONL files in S2ORC format
- Intent-enriched citation JSONL files
- Complete MongoDB dataset with statistics

**Use case:** Building comprehensive citation datasets with intent analysis

#### References Mode (Fast Processing)

Processes existing JSON files → Bibliography extraction → MongoDB

```bash
python dataset_generator.py --mode references
```

**Output includes:**
- Bibliography entries with DBLP IDs
- Citation relationships (no contexts)
- MongoDB dataset with statistics

**Use case:** Quick citation graph generation without intent analysis

### Dataset Stripping

Remove sensitive information before publishing datasets:

```bash
python strip_dataset.py \
    --source-collection dblp_dataset_20241102 \
    --target-collection dblp_dataset_public \
    --strip-citations
```

**What "stripped" means:**
A stripped dataset is a version created by `strip_dataset.py` that removes:
- Citation context text strings
- Cite positions (start/end character indices)
- Raw bibliographic reference strings

**Preserves:**
- Paper identifiers (DBLP IDs, DOIs)
- Citation relationships (who cites whom)
- Intent classifications
- Citation counts and statistics

## Features

### Citation Intent Classification

**Production uses the [BIP! Citation Intent Classifier](https://github.com/athenarc/bip-citation-classifier)**, which implements the SciCite 3-class taxonomy (Cohan et al., NAACL 2019):

| Intent Category | Definition | Example |
|--------|-------------|---------|
| **background information** | Citations providing context, background, or foundational information about a problem, concept, approach, topic, or importance | "Previous work [1] has established the theoretical foundation..." |
| **method** | Citations of methods, tools, approaches, datasets, or frameworks being used or extended | "We use the approach of [2] to extract features..." |
| **results comparison** | Citations comparing the paper's results or findings with results from other work | "Unlike [3], our results show a 15% improvement..." |

**Mock API (for testing) uses a richer 6-class scheme:**
- Background, Motivation, Methods, Results, Future, Extension

This allows for more detailed testing while production uses the BIP! Citation Intent Classifier.

### MongoDB Schema

**Dataset Collection:**
```json
{
  "citing_paper": {
    "dblp_id": "conf/example/Paper2024",
    "doi": "10.xxxx/xxxxx"
  },
  "cited_papers": [
    {
      "dblp_id": "conf/example/Cited2023",
      "doi": "10.yyyy/yyyyy",
      "bibliographic_reference": "Author et al., Title, Venue 2023",
      "citation_contexts": [
        {
          "citation_id": "conf_example_Paper2024>conf_example_Cited2023_CIT0",
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

**Statistics Collection:**
```json
{
  "key": "statistics",
  "total_papers": 1580,
  "total_citations": 45230,
  "total_refs_checked": 52180,
  "total_contexts_added": 38450,
  "last_run_papers_checked": 200,
  "last_run_papers_inserted": 180,
  "total_runs": 5,
  "run_history": [...]
}
```

### Performance Features

- **Incremental Processing**: Automatically detects and skips existing papers
- **Early Duplicate Detection**: Checks MongoDB before file I/O
- **Automatic Indexing**: 5 MongoDB indexes for optimal query performance
- **Cumulative Statistics**: Track dataset growth across multiple runs
- **Run History**: Complete audit trail of all processing runs

## Documentation

- **[docs/QUICKSTART.md](docs/QUICKSTART.md)** - Get up and running in 5 minutes
- **[docs/DATASET_GENERATOR_CLI.md](docs/DATASET_GENERATOR_CLI.md)** - Complete CLI reference with examples
- **[docs/DATASET_STRIPPING_GUIDE.md](docs/DATASET_STRIPPING_GUIDE.md)** - Prepare datasets for publication

## Project Structure

```
s2orc-doc2json/
├── dataset_generator.py          # Main pipeline script
├── strip_dataset.py               # Dataset stripping utility
├── test_installation.py           # Installation validator
├── doc2json/
│   ├── grobid2json/               # Grobid TEI processing
│   │   ├── tei_to_json.py         # TEI XML to S2ORC JSON
│   │   ├── s2orc_converter.py     # Citation extraction
│   │   └── citation_intent_api.py # Intent classification
│   └── utils/                     # Utility modules
│       ├── stats_util.py          # Statistics management
│       ├── dataset_util.py        # Dataset operations
│       ├── dblp_lookup_util.py    # DBLP lookups
│       ├── mongo_util.py          # MongoDB connections
│       └── citation_util.py       # Citation processing
├── docs/                          # Comprehensive documentation
├── tests/                         # Unit and integration tests
└── scripts/                       # Helper scripts
```

## Requirements

- **Python**: 3.8+
- **MongoDB**: 4.0+ (local or remote)
- **Grobid**: 0.7.3+ (for TEI XML processing in intents mode)
- **DBLP Data**: MongoDB collection with paper metadata (optional but recommended)

**Python packages:**
```
pymongo
python-dotenv
beautifulsoup4
requests
```

See `requirements.txt` for complete list.

## Acknowledgments

This tool builds upon and extends work from:

- **S2ORC**: [github.com/allenai/s2orc-doc2json](https://github.com/allenai/s2orc-doc2json) - Some helper functions for TEI XML parsing and bibliography extraction have been partially adapted from this project
- **Grobid**: [github.com/kermitt2/grobid](https://github.com/kermitt2/grobid) - PDF to TEI XML conversion
- **DBLP**: [dblp.org](https://dblp.org/) - Computer science bibliography

## License

See [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Submit a pull request

## Troubleshooting

**Common issues:**

1. **MongoDB connection failed**: Ensure MongoDB is running and credentials in `.env` are correct
2. **Missing citation contexts**: Verify TEI XML files are valid and contain `<ref>` elements
3. **DBLP lookup failures**: Check MongoDB collection name and ensure DBLP data is loaded
4. **Statistics look wrong**: Run with `--fresh-start` to reset statistics

**For detailed troubleshooting, see [docs/QUICKSTART.md](docs/QUICKSTART.md#troubleshooting)**

## Citation

If you use this tool in your research, please cite the original S2ORC work:

```bibtex
@inproceedings{lo-wang-2020-s2orc,
    title = "{S}2{ORC}: The Semantic Scholar Open Research Corpus",
    author = "Lo, Kyle  and Wang, Lucy Lu  and Neumann, Mark  and Kinney, Rodney  and Weld, Daniel",
    booktitle = "Proceedings of the 58th Annual Meeting of the Association for Computational Linguistics",
    month = jul,
    year = "2020",
    address = "Online",
    publisher = "Association for Computational Linguistics",
    url = "https://www.aclweb.org/anthology/2020.acl-main.447",
    doi = "10.18653/v1/2020.acl-main.447",
    pages = "4969--4983"
}
```

