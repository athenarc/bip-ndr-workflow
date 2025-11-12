# BIP! NDR Workflow

[![arXiv](https://img.shields.io/badge/arXiv-2307.12794-b31b1b.svg)](https://arxiv.org/abs/2307.12794) [![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.7962019.svg)](https://doi.org/10.5281/zenodo.7962019) [![License: GPL v2](https://img.shields.io/badge/License-GPL_v2-blue.svg)](https://www.gnu.org/licenses/old-licenses/gpl-2.0.en.html)

![Workflow](/img/dataset-creation-workflow.png)

## Overview

**BIP! NDR (NoDoiRefs)** is an automated, reproducible pipeline for building a DBLP-derived citation dataset focused on computer science publications. The pipeline processes DBLP metadata, retrieves full-text publications, extracts bibliographic references using Grobid, and matches citations to DBLP entries to create a comprehensive citation network.

The resulting dataset enriches scientific publication graphs by capturing citation relationships from papers without DOIs, particularly valuable for conference proceedings and workshop papers common in computer science.

### Key Features

- **Automated end-to-end processing**: From DBLP XML download to final dataset export
- **Multi-stage pipeline**: Modular design allows running individual stages or the complete workflow
- **Batch processing**: Handle large-scale data with configurable batch sizes
- **Reference extraction**: Uses Grobid for robust bibliographic reference parsing from PDFs
- **Citation matching**: Intelligent matching of references to DBLP entries via DOI and title
- **MongoDB integration**: Efficient storage and querying of intermediate and final data
- **Comprehensive logging**: Per-stage logs with timestamps for debugging and monitoring

## Table of Contents

- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Pipeline Stages](#pipeline-stages)
- [Usage Examples](#usage-examples)
- [Directory Structure](#directory-structure)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [Citing this Work](#citing-this-work)
- [License](#license)
- [Contact](#contact)

## Quick Start

Clone the repository with submodules:

```bash
git clone --recurse-submodules -j8 git@github.com:athenarc/bip-ndr-workflow.git
cd bip-ndr-workflow
```

Set up your environment:

```bash
# Copy the template and configure your settings
cp env_file_template .env
# Edit .env with your MongoDB credentials and paths
nano .env
```

Install Python dependencies:

```bash
pip3 install -r requirements.txt
```

Run the complete end-to-end pipeline:

```bash
./bin/run_e2e.sh
```

## Architecture

The pipeline consists of 9 sequential stages that transform DBLP XML data into a structured citation dataset:

```text
DBLP XML → CSV → MongoDB → PDF URLs → PDF Download → TEI XML → JSON → Citation Matching → Dataset Export
```

### Component Overview

1. **DBLP Downloader** (`src/download_dblp_corpus.py`): Fetches the latest DBLP release
2. **XML to CSV Converter** (`submodules/dblp-to-csv/`): Converts DBLP XML to CSV format
3. **Metadata Extractor** (`src/metadata_extractor.py`): Multi-function module for import, download object creation, and filename matching
4. **Publications Retriever** (`submodules/PublicationsRetriever/`): Java tool for downloading full-text PDFs
5. **Grobid Integration** (`src/grobid_pdf2tei.py`): Converts PDFs to TEI XML format
6. **TEI to JSON Converter** (`src/teixml2json_converter.py`): Extracts bibliographic references to JSON
7. **Dataset Generator** (`src/dataset_generator.py`): Creates the final citation dataset
8. **Export Scripts** (`bin/run_mongoexport.sh`): Exports data from MongoDB to files

### Data Flow

- **Input**: DBLP XML release (automatically downloaded)
- **Intermediate Storage**: MongoDB collections for papers, dataset, and statistics
- **Output**: JSON dataset with citation relationships, exportable to various formats

## Prerequisites

### Required Software

- **Python 3.7+** with pip
- **MongoDB 4.0+** (running instance with appropriate credentials)
- **Java 8+** and **Maven 3.6+** (for PublicationsRetriever)
- **Grobid** (external service, see [Grobid installation](https://grobid.readthedocs.io/en/latest/Install-Grobid/))
- **Git** with submodule support

### Optional

- **Docker** (for containerized Grobid deployment)

## Installation

### 1. Clone Repository

```bash
git clone --recurse-submodules -j8 git@github.com:athenarc/bip-ndr-workflow.git
cd bip-ndr-workflow
```

If you already cloned without submodules:

```bash
git submodule update --init --recursive
```

### 2. Install Python Dependencies

```bash
pip3 install -r requirements.txt
```

### 3. Build Java Components

The PublicationsRetriever must be compiled:

```bash
cd submodules/PublicationsRetriever
mvn clean install
cd ../..
```

### 4. Set Up Grobid

Follow the [Grobid installation guide](https://grobid.readthedocs.io/en/latest/Install-Grobid/). The easiest method is using Docker:

```bash
docker pull grobid/grobid:0.8.2-full
docker run -t --rm -p 8070:8070 grobid/grobid:0.8.2-full
```

Update the Grobid configuration at `submodules/grobid_client_python/config.json` with your Grobid service URL.

## Configuration

### Environment Variables

Copy the template and configure:

```bash
cp env_file_template .env
```

Edit `.env` with your specific settings:

```bash
# MongoDB Configuration
MONGO_IP=localhost:27017
MONGO_USER=your_username
MONGO_PASS=your_password
MONGO_DB=dblp_citations

# Collection Names
PAPERS_COL=papers
DBLP_DATASET=dblp_dataset
STATS_COLLECTION=statistics

# File Paths (absolute paths recommended)
DBLP_CORPUS_PATH=/path/to/dblp_corpus
PDF_PATH=/path/to/pdfs
TEI_PATH=/path/to/tei_xml
JSON_PATH=/path/to/json_refs
LOGS_PATH=/path/to/logs

# External Tool Paths
GROBID_CONFIG_PATH=/path/to/grobid_client_python/config.json
PUB_RETRIEVER_PATH=/path/to/PublicationsRetriever

# Runtime Configuration
MODE=production  # or 'test' for smaller batches
LATEST_DATE=  # Auto-populated by download script
```

### MongoDB Indexes

For optimal performance, create indexes:

```bash
mongosh "mongodb://localhost:27017/dblp_citations" --username your_username --file dbscripts/mongodb_indexes.js
```

## Pipeline Stages

The complete pipeline (`./bin/run_e2e.sh`) executes these stages in order:

### Stage 1: Download DBLP Corpus

```bash
python3 src/download_dblp_corpus.py
```

Downloads the latest DBLP XML release and updates `LATEST_DATE` in `.env`.

### Stage 2: Convert XML to CSV

```bash
python3 submodules/dblp-to-csv/XMLToCSV.py \
  ${DBLP_CORPUS_PATH}/dblp-${LATEST_DATE}/dblp-${LATEST_DATE}.xml \
  ${DBLP_CORPUS_PATH}/dblp-${LATEST_DATE}/dblp-*.dtd \
  ${DBLP_CORPUS_PATH}/dblp-${LATEST_DATE}/dblp_${LATEST_DATE}.csv
```

Generates separate CSV files for each DBLP element type (articles, inproceedings, etc.).

### Stage 3: Import to MongoDB

```bash
python3 src/metadata_extractor.py 0
```

Imports CSV data into MongoDB with normalized fields:

- `key_norm`: Normalized DBLP key (slashes → underscores)
- `title_concat`: Title with all non-alphanumeric characters removed (for matching)
- `ee`: Array of electronic edition URLs
- `PDF_downloaded`, `reference_file_parsed`: Processing flags

### Stage 4: Create Download Object

```bash
python3 src/metadata_extractor.py 1
```

Queries MongoDB for open-access publications and generates `input_urls.jsonl` for PDF download.

### Stage 5: Download PDFs

```bash
# Split into batches
./bin/split_dl_file.sh ${DBLP_CORPUS_PATH}/dblp-${LATEST_DATE}/DL_Object/input \
  "input_urls.jsonl" "urls_batch_" 1000

# Run PublicationsRetriever
./bin/run_pub_retriever.sh --all  # or --batch N for specific batch
```

Downloads PDFs using the Java PublicationsRetriever tool with politeness delays.

### Stage 6: Convert PDFs to TEI XML

```bash
python3 src/grobid_pdf2tei.py 1 --batch all --config 1
```

Uses Grobid to extract structured bibliographic data from PDFs.

### Stage 7: Convert TEI to JSON

```bash
./bin/run_tei2json.sh --all  # or --batch N
```

Extracts reference lists from TEI XML to JSON format.

### Stage 8: Match Citations

```bash
python3 src/metadata_extractor.py 2 --batch all
```

Matches references to DBLP entries:

1. Try matching by DOI
2. Fall back to title matching (case-insensitive, alphanumeric only)
3. Record match statistics

### Stage 9: Generate and Export Dataset

```bash
# Merge batches
./bin/merge_batches.sh

# Generate dataset
python3 src/dataset_generator.py

# Export from MongoDB
./bin/run_mongoexport.sh

# Calculate citation counts
./bin/run_total_citations_calculation.sh

# Package final dataset
./bin/rename_compress_dataset.sh
```

## Usage Examples

### Running Individual Stages

Run specific pipeline stages for debugging or partial processing:

```bash
# Only download DBLP corpus
python3 src/download_dblp_corpus.py

# Only import to MongoDB
python3 src/metadata_extractor.py 0

# Process specific batch for TEI conversion
python3 src/teixml2json_converter.py --in_path ${TEI_PATH}/batch_5 --out_path ${JSON_PATH}/batch_5
```

### Batch Processing

Process specific batches for incremental updates:

```bash
# Run PublicationsRetriever for batch 3
./bin/run_pub_retriever.sh --batch 3

# Convert batch 3 PDFs to TEI
python3 src/grobid_pdf2tei.py 1 --batch 3 --config 1

# Match citations for batch 3
python3 src/metadata_extractor.py 2 --batch 3
```

### Query the Database

Use MongoDB shell to explore data:

```bash
mongosh "mongodb://localhost:27017/dblp_citations" --username your_username

# Count papers with PDFs
db.papers.countDocuments({PDF_downloaded: true})

# Find papers with parsed references
db.papers.find({reference_file_parsed: true}).limit(5)

# Check citation statistics
db.statistics_2024-01-15.findOne({key: "statistics"})
```

### Directory Structure

```text
bip-ndr-workflow/
├── bin/                          # Shell scripts for pipeline orchestration
│   ├── run_e2e.sh               # Main end-to-end pipeline
│   ├── run_pub_retriever.sh     # PDF download wrapper
│   ├── run_tei2json.sh          # TEI to JSON conversion
│   └── ...                       # Other utility scripts
├── src/                          # Python source code
│   ├── download_dblp_corpus.py  # DBLP downloader
│   ├── metadata_extractor.py    # Multi-function processor
│   ├── dataset_generator.py     # Final dataset creation
│   ├── teixml2json_converter.py # Reference extraction
│   ├── grobid_pdf2tei.py        # Grobid integration
│   ├── utils/
│   │   └── helper_utils.py      # Environment and MongoDB utilities
│   └── submodules/              # Git submodules
│       ├── dblp-to-csv/         # XML to CSV converter
│       ├── PublicationsRetriever/ # PDF downloader (Java)
│       └── grobid_client_python/  # Grobid client
├── dbscripts/                    # MongoDB scripts
│   ├── mongodb_indexes.js       # Index creation
│   └── calculate_total_citations_mongo.js
├── .env                          # Configuration (create from template)
├── env_file_template            # Environment variable template
├── requirements.txt             # Python dependencies
└── README.md                    # This file
```

## Troubleshooting

### Common Issues

#### MongoDB Connection Errors

```bash
# Verify MongoDB is running
sudo systemctl status mongod

# Test connection
mongosh "mongodb://${MONGO_IP}/${MONGO_DB}" --username ${MONGO_USER}
```

#### Java/Maven Build Failures

```bash
# Check Java version (need 8+)
java -version

# Rebuild PublicationsRetriever
cd submodules/PublicationsRetriever
mvn clean install -U
```

#### Grobid Timeouts

```bash
# Check Grobid service
curl http://localhost:8070/api/version

# Increase timeout in grobid_client_python/config.json
# Reduce batch size or concurrency
```

#### Missing PDFs

```bash
# Check PublicationsRetriever logs
tail -f ${DBLP_CORPUS_PATH}/dblp-${LATEST_DATE}/DL_Object/output/urls_batch_*_output.jsonl

# Retry specific batch
./bin/run_pub_retriever.sh --batch N
```

#### Out of Disk Space

```bash
# Check sizes
du -sh ${PDF_PATH} ${TEI_PATH} ${JSON_PATH}

# Clean intermediate files after successful runs
rm -rf ${DBLP_CORPUS_PATH}/dblp-${LATEST_DATE}/DL_Object/input/input_batches/
```

### Logging

Each stage writes detailed logs to `${LOGS_PATH}/${LATEST_DATE}/`:

```bash
# View metadata extractor logs
tail -f ${LOGS_PATH}/${LATEST_DATE}/metadata_extractor.log

# Search for errors across all logs
grep -i error ${LOGS_PATH}/${LATEST_DATE}/*.log
```

### Performance Tuning

- **Batch Size**: Adjust in `bin/split_dl_file.sh` (default 1000)
- **Worker Threads**: Configure in PublicationsRetriever (see its README)
- **MongoDB Indexes**: Ensure indexes from `dbscripts/mongodb_indexes.js` are created
- **Grobid Concurrency**: Configure in `grobid_client_python/config.json`

## Contributing

We welcome contributions! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes following the existing code style
4. Test your changes on a small dataset first
5. Commit with clear messages (`git commit -m 'Add amazing feature'`)
6. Push to your branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

### Code Conventions

- Use `src/utils/helper_utils.py:get_keys()` for environment variables
- Preserve MongoDB collation: `collation={'locale': 'en', 'strength': 2}`
- Keep database field names consistent: `key_norm`, `title_concat`, `ee`, etc.
- Add logging with timestamps for all significant operations
- For new scripts, prefer Click for CLI over `sys.argv`

See `.github/copilot-instructions.md` for detailed guidance for AI coding agents.

## License

Released under [GNU GPL v2.0](LICENSE.txt).

## Contact

This repository is maintained by **Paris Koloveas** from Athena RC

- Email: <pkoloveas@athenarc.gr>

## Citing this Work

If you utilize any of the processes and scripts in this repository, please cite us in the following way:

```bibtex
@inproceedings{10.1007/978-3-031-43849-3_9,
  author    = {Koloveas, Paris
               and Chatzopoulos, Serafeim
               and Tryfonopoulos, Christos
               and Vergoulis, Thanasis},
  editor    = {Alonso, Omar
               and Cousijn, Helena
               and Silvello, Gianmaria
               and Marrero, M{\'o}nica
               and Teixeira Lopes, Carla
               and Marchesin, Stefano},
  title     = {BIP! NDR (NoDoiRefs): A Dataset of Citations from Papers Without DOIs in Computer Science Conferences and Workshops},
  booktitle = {Linking Theory and Practice of Digital Libraries},
  year      = {2023},
  publisher = {Springer Nature Switzerland},
  address   = {Cham},
  pages     = {99--105},
  isbn      = {978-3-031-43849-3}
}
```
