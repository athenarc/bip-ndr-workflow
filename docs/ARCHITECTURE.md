# Architecture Documentation

## System Overview

The BIP! NDR Workflow is a distributed data processing pipeline that transforms DBLP bibliographic metadata into a rich citation network dataset. The architecture follows a staged ETL (Extract, Transform, Load) pattern with MongoDB as the central data store.

## High-Level Architecture

```text
┌─────────────────┐
│  DBLP Release   │
│   (XML + DTD)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  XML → CSV      │
│  Converter      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────────┐
│    MongoDB      │◄─────┤  Metadata        │
│   Collections   │      │  Extractor       │
└────────┬────────┘      └──────────────────┘
         │
         ▼
┌─────────────────┐
│  PDF Download   │      ┌──────────────────┐
│    Object       │─────►│ Publications     │
│  (JSONL URLs)   │      │  Retriever (Java)│
└─────────────────┘      └────────┬─────────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │   PDF Files     │
                         └────────┬────────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │     Grobid      │
                         │  (TEI Extract)  │
                         └────────┬────────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │   TEI → JSON    │
                         │   Converter     │
                         └────────┬────────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │  Citation       │
                         │  Matching       │
                         └────────┬────────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │   Final         │
                         │   Dataset       │
                         └─────────────────┘
```

## Component Details

### 1. Download & Preprocessing Layer

#### DBLP Downloader (`src/download_dblp_corpus.py`)

**Purpose**: Automatically fetches the latest DBLP XML release from Dagstuhl Drops.

**Key Functions**:
- Web scraping to identify latest release date
- Downloads compressed XML and DTD files
- Updates `.env` with `LATEST_DATE` for downstream processing
- Creates necessary directory structure

**Technologies**: Python, requests, BeautifulSoup

**Configuration**: 
- Release URL: `https://drops.dagstuhl.de/entities/collection/10.4230/dblp.xml`
- Storage: `${DBLP_CORPUS_PATH}/dblp-${LATEST_DATE}/`

#### XML to CSV Converter (`submodules/dblp-to-csv/`)

**Purpose**: Transforms DBLP's complex XML structure into normalized CSV files.

**Key Features**:
- Element-specific output files (article, inproceedings, etc.)
- Array handling for multi-valued fields (authors, URLs)
- DTD-based parsing for schema validation
- Optional type annotation for downstream processing

**Technologies**: Python, lxml

**Output Format**:
- Delimiter: semicolon (`;`)
- Array notation: `[value1|value2|...|valueN]`
- Separate CSV per DBLP element type

### 2. Storage Layer

#### MongoDB Collections

**papers** (`PAPERS_COL`)
- Primary collection for DBLP metadata
- Schema:
  ```javascript
  {
    key: String,              // Original DBLP key
    key_norm: String,         // Normalized key (/ → _)
    title: String,
    title_concat: String,     // Alphanumeric only, for matching
    author: [String],
    year: Number,
    ee: [String],            // Electronic edition URLs
    ee-type: [String],       // URL types (oa, doi, etc.)
    PDF_downloaded: Boolean,
    filename_norm: String,
    reference_file_parsed: Boolean,
    import_date: String      // YYYY-MM-DD
  }
  ```

**dblp_dataset_{date}** (`DBLP_DATASET`)
- Citation relationships
- Schema:
  ```javascript
  {
    citing_paper: {
      dblp_id: String,
      doi: String          // Optional
    },
    cited_papers: [{
      dblp_id: String,     // If matched
      doi: String,         // If available
      bibliographic_reference: String
    }]
  }
  ```

**statistics_{date}** (`STATS_COLLECTION`)
- Processing metrics
- Real-time statistics updates
- Fields: files_checked, refs_checked, refs_skipped, dois_matched, etc.

**Indexes**:
- `key` (unique, collation strength 2)
- `key_norm` (collation strength 2)
- `title_concat` (collation strength 2)
- `ee` (array index)
- `PDF_downloaded`, `reference_file_parsed` (boolean flags)

### 3. PDF Acquisition Layer

#### Publications Retriever (Java)

**Purpose**: Multi-threaded PDF downloader with domain politeness.

**Architecture**:
- Java 8+ application
- Maven-based build
- Configurable thread pool
- Per-domain rate limiting
- Retry logic with exponential backoff

**Input**: JSONL files with `{id, url}` pairs

**Output**: 
- Downloaded PDFs named by ID
- JSONL log with download results
- Optional S3 upload

**Key Features**:
- Custom user agents
- Cookie handling
- Redirect following
- Content-type validation
- MD5 hash computation

**Configuration**:
- Thread count: Configurable via environment
- Storage: Local filesystem or S3
- Batch size: Split by `bin/split_dl_file.sh`

### 4. Text Extraction Layer

#### Grobid Integration

**Purpose**: Structured extraction of bibliographic references from PDFs.

**Workflow**:
1. `src/grobid_pdf2tei.py` sends PDFs to Grobid service
2. Grobid returns TEI XML with parsed references
3. TEI files stored in `${TEI_PATH}`

**TEI Structure** (relevant sections):
```xml
<TEI>
  <text>
    <back>
      <div type="references">
        <listBibl>
          <biblStruct>
            <analytic>
              <title>...</title>
              <author>...</author>
              <idno type="DOI">...</idno>
            </analytic>
            <monogr>...</monogr>
            <note type="raw_reference">...</note>
          </biblStruct>
        </listBibl>
      </div>
    </back>
  </text>
</TEI>
```

**Grobid Configuration**:
- Service URL in `grobid_client_python/config.json`
- Concurrency settings
- Timeout configuration

#### TEI to JSON Converter (`src/teixml2json_converter.py`)

**Purpose**: Extract reference lists from TEI XML to simpler JSON format.

**Technology**: Python, xmltodict, Click CLI

**Output Format**:
```json
{
  "biblStruct": [
    {
      "analytic": {
        "title": {"#text": "..."},
        "idno": {"@type": "DOI", "#text": "..."}
      },
      "monogr": {...},
      "note": {"#text": "raw reference string"}
    }
  ]
}
```

**Transformations**:
- Whitespace normalization
- Newline removal
- Hyphenation fix (removes `- ` at line breaks)

### 5. Citation Matching Layer

#### Reference Parser & Matcher (`src/dataset_generator.py`)

**Purpose**: Link extracted references to DBLP entries.

**Matching Strategy**:

1. **DOI Matching** (Primary):
   - Extract DOI from reference JSON
   - Query MongoDB: `{ee: "https://doi.org/{DOI}"}`
   - Case-insensitive collation
   
2. **Title Matching** (Fallback):
   - Normalize title: remove all non-alphanumeric characters
   - Query MongoDB: `{title_concat: normalized_title}`
   - Case-insensitive collation
   
3. **Result Recording**:
   - Matched: Record DBLP key, retrieve DOI if missing
   - Unmatched: Log for future analysis

**Statistics Tracking**:
- Real-time updates to `statistics` collection
- Per-batch and cumulative metrics
- Success rates for matching strategies

### 6. Export & Packaging Layer

**Dataset Generator** (`src/dataset_generator.py`):
- Aggregates citation data
- Formats for export
- Generates summary statistics

**Export Scripts**:
- `bin/run_mongoexport.sh`: MongoDB → JSON/CSV export
- `bin/run_total_citations_calculation.sh`: Citation counts using aggregation pipeline
- `bin/rename_compress_dataset.sh`: Final packaging

## Data Flow Patterns

### Batch Processing

The pipeline uses batch processing for scalability:

1. **Input Splitting**: 
   - `bin/split_dl_file.sh` divides URL lists into batches
   - Default: 1000 URLs per batch
   
2. **Parallel Processing**:
   - Multiple batches can run concurrently on different machines
   - Batch numbers identify independent processing units
   
3. **Merging**:
   - `bin/merge_batches.sh` consolidates results
   - MongoDB as merge point for citation data

### State Management

**Database Flags**:
- `PDF_downloaded`: Prevents re-downloading
- `reference_file_parsed`: Avoids duplicate processing
- `import_date`: Tracks data versioning

**Idempotency**:
- All stages check for existing work
- Safe to re-run failed batches
- Logs preserve processing history

### Error Handling

**Retry Strategy**:
- PublicationsRetriever: Built-in retry with backoff
- Grobid: Timeout and connection retry
- MongoDB: Connection pooling with auto-reconnect

**Logging**:
- Per-stage log files: `${LOGS_PATH}/${LATEST_DATE}/`
- Timestamped entries for debugging
- Separate logs for each script

## Configuration Management

### Environment Variables (`src/utils/helper_utils.py`)

**Centralized Configuration**:
```python
def get_keys():
    return {
        "mongo_ip": os.getenv('MONGO_IP'),
        "mongo_user": os.getenv('MONGO_USER'),
        # ... all other config
    }
```

**Benefits**:
- Single source of truth
- Easy to modify across pipeline
- Supports multiple environments (dev/prod)

### Runtime Modes

**MODE Variable**:
- `production`: Full dataset processing
- `test`: Smaller batches, limited scope

## Scalability Considerations

### Horizontal Scaling

**Parallelizable Stages**:
- PDF download (by batch)
- Grobid processing (by batch)
- TEI to JSON conversion (by batch)

**Coordination**:
- MongoDB prevents duplicate work via flags
- Batch numbering ensures no overlap

### Performance Optimization

**MongoDB**:
- Indexes on match fields (`key_norm`, `title_concat`, `ee`)
- Case-insensitive collation avoids duplicate lookups
- Connection pooling reduces overhead

**File I/O**:
- Streaming processing where possible
- Batch commits to database
- Compressed storage for archives

### Resource Requirements

**Disk Space**:
- DBLP XML: ~3-4 GB compressed, ~30-40 GB uncompressed
- PDFs: Variable, typically 50-200 GB for full dataset
- TEI XML: ~1.5-2x PDF size
- JSON references: ~10-20% of TEI size
- MongoDB: ~30-50 GB for complete collections

**Memory**:
- Python scripts: 2-4 GB per instance
- PublicationsRetriever: 4-8 GB JVM heap
- Grobid: 8-16 GB recommended
- MongoDB: 8-16 GB for working set

**Network**:
- DBLP download: 3-4 GB one-time
- PDF downloads: Bandwidth-intensive, rate-limited
- Grobid: Local network preferred

## Security Considerations

### Credentials Management

- `.env` file excluded from version control
- MongoDB credentials required for all stages
- S3 credentials (optional) in separate file

### External Services

**Grobid**:
- Local deployment recommended
- No sensitive data leaves infrastructure
- Can run in isolated network segment

**PDF Sources**:
- Respects robots.txt
- Implements politeness delays
- User agent identification

## Monitoring & Observability

### Logging

**Per-Stage Logs**:
- Standard format: `%(asctime)s \t %(message)s`
- Date-based organization: `${LOGS_PATH}/${LATEST_DATE}/`
- Both file and console handlers

### Statistics

**Real-Time Metrics** (in MongoDB):
- Files processed
- References extracted
- Matching success rates
- DOI retrieval statistics

**Performance Metrics**:
- Stage completion times (from logs)
- Throughput (URLs/min, PDFs/min)
- Error rates per batch

## Future Architecture Considerations

### Potential Improvements

1. **Message Queue Integration**:
   - Replace file-based batching with Kafka/RabbitMQ
   - Better load balancing and retry logic

2. **Containerization**:
   - Docker containers for each component
   - Kubernetes orchestration for scaling

3. **Incremental Updates**:
   - Delta processing for DBLP updates
   - Change detection and selective re-processing

4. **Caching Layer**:
   - Redis for frequently accessed metadata
   - Reduce MongoDB query load

5. **API Layer**:
   - REST API for dataset access
   - Query interface for researchers

## References

- [DBLP XML](https://dblp.org/xml/)
- [Grobid Documentation](https://grobid.readthedocs.io/)
- [BIP! NDR Paper (arXiv:2307.12794)](https://arxiv.org/abs/2307.12794)
