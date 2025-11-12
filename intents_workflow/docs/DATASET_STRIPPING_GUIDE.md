# Dataset Stripping Guide

## Overview

The `strip_dataset.py` utility creates a **stripped version** of the citation intent dataset for publication, removing citation text snippets and position information due to legal/copyright concerns.

⚠️ **IMPORTANT**: This is a **ONE-WAY transformation**. Always maintain the full dataset privately for experiments and validation. The stripped version has limited research value but may be required for legal compliance in public releases.

## Why Strip the Dataset?

Scientific publishers and copyright holders may have legal concerns about distributing citation contexts (text snippets) even though they constitute fair use for research purposes. The stripped version addresses these concerns by:

- **Removing citation text**: No actual paper content is distributed
- **Removing position information**: No `cite_start` and `cite_end` fields
- **Preserving structure**: Citation IDs maintain the citation graph structure
- **Keeping intents**: Intent labels remain for citation classification research

## What Gets Stripped?

### Full Version (Private)
```json
{
  "citing_paper": {
    "dblp_id": "conf/acl/Smith20"
  },
  "cited_papers": [
    {
      "dblp_id": "conf/acl/Johnson07",
      "bibliographic_reference": "Johnson, M. (2007). Example paper...",
      "citation_contexts": [
        {
          "citation_id": "conf_acl_Smith20_conf_acl_Johnson07_CIT0",
          "section": "Introduction",
          "text": "Recent work on parsing (Johnson, 2007) has shown...",
          "cite_start": 24,
          "cite_end": 38,
          "intent": "background information"
        },
        {
          "citation_id": "conf_acl_Smith20_conf_acl_Johnson07_CIT1",
          "section": "Methods",
          "text": "We use the approach from Johnson (2007) to...",
          "cite_start": 29,
          "cite_end": 43,
          "intent": "method"
        }
      ]
    }
  ]
}
```

### Stripped Version (Public)
```json
{
  "citing_paper": {
    "dblp_id": "conf/acl/Smith20"
  },
  "cited_papers": [
    {
      "dblp_id": "conf/acl/Johnson07",
      "bibliographic_reference": "Johnson, M. (2007). Example paper...",
      "citations": [
        {
          "citation_id": "conf_acl_Smith20_conf_acl_Johnson07_CIT0",
          "section": "Introduction",
          "intent": "background information"
        },
        {
          "citation_id": "conf_acl_Smith20_conf_acl_Johnson07_CIT1",
          "section": "Methods",
          "intent": "method"
        }
      ]
    }
  ]
}
```

## Citation ID Format

Citation IDs use S2ORC-style notation:

```
{citing_paper_id}_{cited_paper_id}_CIT{index}
```

**Example**: `conf_acl_Smith20_conf_acl_Johnson07_CIT0`

- `conf_acl_Smith20`: Citing paper (DBLP ID converted to underscores)
- `conf_acl_Johnson07`: Cited paper (DBLP ID converted to underscores)
- `CIT0`: Citation instance index (0-based)

This format:
- Maintains unique identification for each citation instance
- Preserves the relationship between citing and cited papers
- Allows citation graph reconstruction without text snippets
- Is consistent with S2ORC JSONL notation

**Important**: Citation IDs are now included in **both** the full and stripped versions. This ensures:
- Easy cross-referencing between full and stripped datasets
- Consistent identifiers across versions
- Ability to map stripped citations back to full contexts (when you have access to both)

## Usage

### Basic Usage

```bash
# Strip the dataset
python strip_dataset.py --source-collection dataset --target-collection dataset_stripped
```

### Preview (Dry Run)

```bash
# Preview what will be stripped without making changes
python strip_dataset.py --source-collection dataset --target-collection dataset_stripped --dry-run
```

### Show Example

```bash
# Show before/after comparison
python strip_dataset.py --source-collection dataset --target-collection dataset_stripped --show-example
```

## Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `--source-collection` | Yes | Source MongoDB collection (full dataset) |
| `--target-collection` | Yes | Target MongoDB collection (stripped dataset) |
| `--dry-run` | No | Preview without making changes |
| `--show-example` | No | Show before/after comparison example |

## Safety Features

### Collection Name Validation

The script **requires different collection names** for source and target:

```bash
# ✗ ERROR - This will be rejected
python strip_dataset.py --source-collection dataset --target-collection dataset

# ✓ CORRECT
python strip_dataset.py --source-collection dataset --target-collection dataset_stripped
```

### Target Collection Clearing

The target collection is **automatically cleared** before stripping to ensure a clean slate. The script will:

1. Delete all documents in the target collection
2. Process and strip all entries from source
3. Insert stripped entries into target

⚠️ **Warning**: Any existing data in the target collection will be lost.

## Workflow Integration

The stripping utility operates as a **post-processing step** outside the core workflow:

```
┌─────────────────────────────────────────────┐
│         CORE WORKFLOW (INTENTS MODE)        │
├─────────────────────────────────────────────┤
│                                             │
│  TEI XML → JSON → JSONL → Intents → MongoDB│
│                                             │
│  Result: Full dataset with citation contexts│
│          (Always keep this privately!)      │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
         ┌────────────────────┐
         │  POST-PROCESSING   │
         │  (strip_dataset.py)│
         └────────┬───────────┘
                  │
                  ▼
         ┌────────────────────┐
         │  Stripped Dataset  │
         │  (For publication) │
         └────────────────────┘
```

**Key Points**:
- The workflow always produces the **full dataset** in MongoDB
- Stripping is a **separate manual step** after the workflow completes
- You can generate stripped versions **multiple times** from the full dataset
- **Never run the workflow to produce only the stripped version** (no going back)

## Statistics Output

The script provides detailed statistics:

```
================================================================================
STRIPPING COMPLETE
================================================================================

Statistics:
  Total citing papers: 1250
    - With citation contexts: 1200
    - Without citation contexts: 50

  Total cited papers: 15680
    - With citation contexts: 12340
    - Without citation contexts: 3340

  Total citations stripped: 45678

✓ Stripped dataset saved to collection: dataset_stripped
================================================================================
```

## Example Comparison

When using `--show-example`, you'll see a comparison:

```
================================================================================
EXAMPLE COMPARISON: Before and After Stripping
================================================================================

Citing Paper: conf/acl/Smith20

Cited Paper: conf/acl/Johnson07

BEFORE (Full Version):
--------------------------------------------------------------------------------
  Context 0:
    Section: Introduction
    Text: Recent work on parsing (Johnson, 2007) has shown significant improvements...
    Positions: [24, 38]
    Intent: background information

  Context 1:
    Section: Methods
    Text: We use the approach from Johnson (2007) to parse the sentences...
    Positions: [29, 43]
    Intent: method

AFTER (Stripped Version):
--------------------------------------------------------------------------------
  Citation 0:
    Citation ID: conf_acl_Smith20_conf_acl_Johnson07_CIT0
    Section: Introduction
    Intent: background information

  Citation 1:
    Citation ID: conf_acl_Smith20_conf_acl_Johnson07_CIT1
    Section: Methods
    Intent: method

================================================================================
```

## Research Impact

### What You Can Still Do

With the stripped version, you can:

- ✓ Build citation graphs (who cites whom)
- ✓ Analyze citation intent distributions
- ✓ Study citation patterns by section
- ✓ Compare intent usage across papers
- ✓ Validate citation intent classifiers (structure-based)

### What You Cannot Do

Without the full version, you cannot:

- ✗ Train new citation intent classifiers (no text features)
- ✗ Analyze citation context language
- ✗ Study citation placement in text
- ✗ Reproduce intent predictions
- ✗ Validate against original papers

**Bottom Line**: The stripped version is useful for **citation graph analysis** and **intent statistics**, but has **severely limited value** for **machine learning** and **deep citation analysis**.

## Best Practices

1. **Always Keep the Full Dataset**: Store it securely for your research
2. **Generate Stripped Version Only When Needed**: For publication/sharing
3. **Document What Was Stripped**: Include this in your data release documentation
4. **Consider Alternatives**: Check if your institution's legal team approves fair use
5. **Provide Access to Full Dataset**: Via data use agreements if possible

## Legal Considerations

⚠️ **Disclaimer**: This tool is provided to help with legal compliance concerns. However:

- Citation contexts may constitute **fair use** under copyright law (research/educational purpose)
- Legal requirements vary by jurisdiction and publisher
- Consult your institution's legal counsel before deciding to strip the dataset
- Consider data use agreements as an alternative to public stripping

## Environment Configuration

The script uses the same `.env` configuration as the main workflow:

```bash
# MongoDB connection
MONGO_IP=localhost
MONGO_PORT=27017
MONGO_DB=citation_intents

# Logging (optional)
LOGS_PATH=logs
```

No additional configuration needed!

## Troubleshooting

### "Source and target collections must be different"

**Cause**: You specified the same collection name for both source and target.

**Solution**: Use different names to prevent accidental data loss:
```bash
python strip_dataset.py --source-collection dataset --target-collection dataset_stripped
```

### "No entries with citation contexts found"

**Cause**: The source collection doesn't have citation contexts (not generated with intents mode).

**Solution**: Make sure you ran the workflow with `--mode intents` first.

### Connection Errors

**Cause**: MongoDB not running or wrong credentials in `.env`.

**Solution**: Check MongoDB is running and `.env` settings are correct:
```bash
# Start MongoDB (if using local installation)
mongod --dbpath /path/to/data

# Or use Docker
docker run -d -p 27017:27017 mongo:latest
```

## Files Generated

- **Log File**: `logs/strip_dataset_YYYYMMDD_HHMMSS.log`
- **MongoDB Collection**: Specified target collection (e.g., `dataset_stripped`)

## Performance

- **Processing Speed**: ~100-500 entries/second (depends on context count)
- **Memory Usage**: Minimal (processes entries one at a time)
- **Database Impact**: Clears target collection, then bulk inserts

For large datasets (>10K papers), expect processing time of several minutes.

## Related Documentation

- [DATASET_GENERATOR_CLI.md](DATASET_GENERATOR_CLI.md) - Main workflow documentation
- [QUICKSTART.md](QUICKSTART.md) - Getting started guide
- [CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md) - Environment setup
