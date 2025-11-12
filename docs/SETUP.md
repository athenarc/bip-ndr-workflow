# Setup Guide

This guide provides step-by-step instructions for setting up the BIP! NDR Workflow pipeline on your system.

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Prerequisites Installation](#prerequisites-installation)
3. [Pipeline Installation](#pipeline-installation)
4. [Configuration](#configuration)
5. [Verification](#verification)
6. [First Run](#first-run)
7. [Common Setup Issues](#common-setup-issues)

## System Requirements

### Minimum Requirements

- **CPU**: 4 cores
- **RAM**: 16 GB
- **Storage**: 200 GB available space
- **OS**: Linux (Ubuntu 20.04+ recommended) or macOS

### Recommended Requirements

- **CPU**: 8+ cores
- **RAM**: 32 GB
- **Storage**: 500 GB SSD
- **OS**: Linux server with persistent storage

### Network Requirements

- Stable internet connection for DBLP downloads and PDF retrieval
- Bandwidth: At least 10 Mbps for reasonable download times
- No restrictive firewalls blocking HTTP/HTTPS traffic

## Prerequisites Installation

### 1. Python 3.7+

#### Ubuntu/Debian

```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv
python3 --version  # Should be 3.7 or higher
```

#### macOS

```bash
# Using Homebrew
brew install python3
python3 --version
```

### 2. MongoDB

#### Option A: Local Installation (Ubuntu)

```bash
# Import MongoDB GPG key
wget -qO - https://www.mongodb.org/static/pgp/server-6.0.asc | sudo apt-key add -

# Add MongoDB repository
echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu focal/mongodb-org/6.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-6.0.list

# Install MongoDB
sudo apt update
sudo apt install -y mongodb-org

# Start MongoDB service
sudo systemctl start mongod
sudo systemctl enable mongod

# Verify installation
mongosh --version
```

#### Option B: Docker (All platforms)

```bash
# Pull MongoDB image
docker pull mongo:6.0

# Run MongoDB container
docker run -d \
  --name mongodb \
  -p 27017:27017 \
  -e MONGO_INITDB_ROOT_USERNAME=admin \
  -e MONGO_INITDB_ROOT_PASSWORD=your_password \
  -v mongodb_data:/data/db \
  mongo:6.0

# Verify it's running
docker ps | grep mongodb
```

#### Create Database User

```bash
mongosh "mongodb://localhost:27017" -u admin -p your_password

# In MongoDB shell:
use dblp_citations

db.createUser({
  user: "dblp_user",
  pwd: "secure_password",
  roles: [
    { role: "readWrite", db: "dblp_citations" }
  ]
})

exit
```

### 3. Java and Maven

#### Ubuntu/Debian

```bash
sudo apt install openjdk-11-jdk maven
java -version   # Should show Java 11 or higher
mvn -version    # Should show Maven 3.6+
```

#### macOS

```bash
brew install openjdk@11 maven
java -version
mvn -version
```

### 4. Git with LFS Support

```bash
# Ubuntu/Debian
sudo apt install git git-lfs

# macOS
brew install git git-lfs

# Initialize Git LFS
git lfs install
```

### 5. Grobid

Grobid is required for PDF text extraction. We recommend using Docker for easy setup.

#### Option A: Grobid via Docker (Recommended)

```bash
# Pull Grobid image
docker pull lfoppiano/grobid:0.7.3

# Run Grobid service
docker run -d \
  --name grobid \
  -p 8070:8070 \
  lfoppiano/grobid:0.7.3

# Verify it's running
curl http://localhost:8070/api/version
```

#### Option B: Grobid from Source

See the [official Grobid installation guide](https://grobid.readthedocs.io/en/latest/Install-Grobid/).

## Pipeline Installation

### 1. Clone the Repository

```bash
# Clone with submodules
git clone --recurse-submodules -j8 git@github.com:athenarc/bip-ndr-workflow.git
cd bip-ndr-workflow

# If you already cloned without submodules
git submodule update --init --recursive
```

### 2. Install Python Dependencies

```bash
# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install requirements
pip3 install --upgrade pip
pip3 install -r requirements.txt
```

### 3. Build Java Components

```bash
# Navigate to PublicationsRetriever
cd submodules/PublicationsRetriever

# Build with Maven
mvn clean install

# Verify build success (JAR should exist)
ls -lh target/publications_retriever-*.jar

# Return to project root
cd ../..
```

### 4. Set Up Directory Structure

```bash
# Create necessary directories
mkdir -p data/{corpus,pdfs,tei,json,logs,output}

# Set appropriate permissions
chmod -R 755 data/
```

## Configuration

### 1. Create Environment File

```bash
# Copy template
cp env_file_template .env

# Edit with your favorite editor
nano .env
```

### 2. Configure Environment Variables

Edit `.env` with your specific settings:

```bash
# MongoDB Configuration
MONGO_IP=localhost:27017
MONGO_USER=dblp_user
MONGO_PASS=secure_password
MONGO_DB=dblp_citations

# Collection Names
PAPERS_COL=papers
DBLP_DATASET=dblp_dataset
STATS_COLLECTION=statistics

# File Paths (use absolute paths)
DBLP_CORPUS_PATH=/full/path/to/bip-ndr-workflow/data/corpus
PDF_PATH=/full/path/to/bip-ndr-workflow/data/pdfs
TEI_PATH=/full/path/to/bip-ndr-workflow/data/tei
JSON_PATH=/full/path/to/bip-ndr-workflow/data/json
LOGS_PATH=/full/path/to/bip-ndr-workflow/data/logs
OUTPUT_DATASET_PATH=/full/path/to/bip-ndr-workflow/data/output

# External Tool Paths
GROBID_CONFIG_PATH=/full/path/to/bip-ndr-workflow/submodules/grobid_client_python/config.json
PUB_RETRIEVER_PATH=/full/path/to/bip-ndr-workflow/submodules/PublicationsRetriever
HOME_PATH=/full/path/to/bip-ndr-workflow

# Runtime Configuration
MODE=production
LATEST_DATE=  # Will be auto-populated by download script
```

**Important**: Replace `/full/path/to/` with the actual absolute path to your installation.

### 3. Configure Grobid Client

Edit `submodules/grobid_client_python/config.json`:

```json
{
  "grobid_server": "http://localhost:8070",
  "batch_size": 1000,
  "sleep_time": 5,
  "timeout": 60,
  "coordinates": ["persName", "figure", "ref", "biblStruct", "formula"]
}
```

Adjust `batch_size` and `timeout` based on your system resources.

### 4. Set Up MongoDB Indexes

```bash
# Create indexes for optimal performance
mongosh "mongodb://localhost:27017/dblp_citations" \
  --username dblp_user \
  --password secure_password \
  --file dbscripts/mongodb_indexes.js
```

### 5. Make Scripts Executable

```bash
chmod +x bin/*.sh
```

## Verification

### Test Individual Components

#### 1. Python Environment

```bash
python3 -c "import pymongo, requests, bs4, click, lxml; print('All Python dependencies OK')"
```

#### 2. MongoDB Connection

```bash
python3 -c "
from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()
client = MongoClient(
    host=os.getenv('MONGO_IP'),
    username=os.getenv('MONGO_USER'),
    password=os.getenv('MONGO_PASS')
)
print('MongoDB connection:', 'OK' if client.server_info() else 'FAILED')
"
```

#### 3. Java/Maven

```bash
java -jar submodules/PublicationsRetriever/target/publications_retriever-*.jar --help
```

#### 4. Grobid Service

```bash
curl -X GET http://localhost:8070/api/version
# Should return Grobid version information
```

### Run Integration Test

Test with a small sample:

```bash
# Set test mode
echo "MODE=test" >> .env

# Create test input directory
mkdir -p test_data

# Run minimal pipeline test
python3 src/download_dblp_corpus.py
echo "✓ DBLP download test passed"
```

## First Run

### Option 1: Complete End-to-End Pipeline

**Warning**: This will take several hours to days depending on your system and network.

```bash
# Activate virtual environment if not already active
source venv/bin/activate

# Run complete pipeline
./bin/run_e2e.sh
```

Monitor progress in logs:

```bash
# Watch main log
tail -f data/logs/*/run_e2e.log

# Check current stage
ls -lrt data/logs/*/
```

### Option 2: Step-by-Step Execution

For better control and debugging, run stages individually:

```bash
# Stage 1: Download DBLP
python3 src/download_dblp_corpus.py

# Stage 2: Convert to CSV (wait for Stage 1 to complete)
export $(xargs <.env)
gunzip -k ${DBLP_CORPUS_PATH}/dblp-${LATEST_DATE}/dblp-${LATEST_DATE}.xml.gz
python3 submodules/dblp-to-csv/XMLToCSV.py \
  ${DBLP_CORPUS_PATH}/dblp-${LATEST_DATE}/dblp-${LATEST_DATE}.xml \
  ${DBLP_CORPUS_PATH}/dblp-${LATEST_DATE}/dblp-*.dtd \
  ${DBLP_CORPUS_PATH}/dblp-${LATEST_DATE}/dblp_${LATEST_DATE}.csv

# Stage 3: Import to MongoDB
python3 src/metadata_extractor.py 0

# Continue with remaining stages as needed...
```

## Common Setup Issues

### Issue: MongoDB Connection Refused

**Symptoms**: `pymongo.errors.ServerSelectionTimeoutError`

**Solutions**:

```bash
# Check if MongoDB is running
sudo systemctl status mongod  # Linux
# or
docker ps | grep mongodb      # Docker

# Check firewall
sudo ufw status
sudo ufw allow 27017

# Verify credentials in .env
mongosh "mongodb://${MONGO_IP}/${MONGO_DB}" -u ${MONGO_USER} -p ${MONGO_PASS}
```

### Issue: Java Out of Memory

**Symptoms**: `java.lang.OutOfMemoryError`

**Solution**: Increase JVM heap size

```bash
# Edit bin/run_pub_retriever.sh
# Change: java -jar ...
# To:     java -Xmx8G -jar ...
```

### Issue: Grobid Timeout

**Symptoms**: Connection timeout errors during PDF processing

**Solutions**:

```bash
# Increase timeout in grobid_client_python/config.json
{
  "timeout": 120  # Increase from 60
}

# Or reduce batch size
{
  "batch_size": 500  # Decrease from 1000
}

# Check Grobid health
curl http://localhost:8070/api/isalive
```

### Issue: Permission Denied on Scripts

**Symptoms**: `bash: ./bin/run_e2e.sh: Permission denied`

**Solution**:

```bash
chmod +x bin/*.sh
```

### Issue: Disk Space Running Out

**Symptoms**: `No space left on device`

**Solutions**:

```bash
# Check available space
df -h

# Clean up intermediate files after stages complete
rm -rf ${DBLP_CORPUS_PATH}/dblp-${LATEST_DATE}/DL_Object/input/input_batches/

# Compress PDFs after TEI extraction (if space is critical)
tar -czf pdfs_backup.tar.gz ${PDF_PATH}
rm -rf ${PDF_PATH}/*.pdf
```

### Issue: Submodules Not Initialized

**Symptoms**: Empty `submodules/PublicationsRetriever/` directory

**Solution**:

```bash
git submodule update --init --recursive
cd submodules/PublicationsRetriever
mvn clean install
```

### Issue: Python Dependencies Conflicts

**Symptoms**: Import errors or version conflicts

**Solution**:

```bash
# Create fresh virtual environment
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip3 install --upgrade pip
pip3 install -r requirements.txt
```

## Performance Tuning

### For Fast Processing

```bash
# Increase worker threads for PublicationsRetriever
# Edit submodules/PublicationsRetriever/src/main/resources/application.properties

# Increase Grobid concurrency
# Edit submodules/grobid_client_python/config.json
{
  "batch_size": 2000,
  "concurrency": 10
}
```

### For Limited Resources

```bash
# Reduce batch sizes
./bin/split_dl_file.sh ... 500  # Instead of 1000

# Process one batch at a time
./bin/run_pub_retriever.sh --batch 1
# Wait for completion, then:
./bin/run_pub_retriever.sh --batch 2
```

## Next Steps

After successful setup:

1. Read the [README.md](README.md) for usage examples
2. Review [ARCHITECTURE.md](ARCHITECTURE.md) for system design
3. Check `.github/copilot-instructions.md` for development guidelines
4. Join our community (contact info in README)

## Getting Help

If you encounter issues not covered here:

1. Check the logs in `${LOGS_PATH}/${LATEST_DATE}/`
2. Search existing GitHub issues
3. Open a new issue with:
   - Your OS and versions (Python, Java, MongoDB)
   - Full error message and stack trace
   - Relevant log excerpts
   - Steps to reproduce

## Appendix: Production Deployment Checklist

For deploying to production servers:

- [ ] MongoDB has authentication enabled
- [ ] MongoDB backups configured
- [ ] Sufficient disk space allocated (500+ GB)
- [ ] Grobid running as a service (systemd or Docker)
- [ ] Firewall rules configured
- [ ] Monitoring and alerting set up
- [ ] Log rotation configured
- [ ] Cron job for periodic updates (optional)
- [ ] Documentation for team members
- [ ] Backup and recovery procedures documented
