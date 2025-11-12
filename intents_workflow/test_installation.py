#!/usr/bin/env python
"""
Test script for dataset generator CLI

Run this to verify your installation is working correctly.
"""

import sys
import os

def test_imports():
    """Test that all required modules can be imported."""
    print("Testing imports...")
    
    try:
        from doc2json.grobid2json.tei_to_json import convert_tei_xml_file_to_s2orc_json
        print("✓ doc2json.grobid2json.tei_to_json")
    except ImportError as e:
        print(f"✗ doc2json.grobid2json.tei_to_json: {e}")
        return False
    
    try:
        from doc2json.grobid2json.s2orc_converter import metadata_strip, generate_s2orc_jsonl
        print("✓ doc2json.grobid2json.s2orc_converter")
    except ImportError as e:
        print(f"✗ doc2json.grobid2json.s2orc_converter: {e}")
        return False
    
    try:
        from doc2json.grobid2json.citation_intent_api import MockCitationIntentAPI
        print("✓ doc2json.grobid2json.citation_intent_api")
    except ImportError as e:
        print(f"✗ doc2json.grobid2json.citation_intent_api: {e}")
        return False
    
    try:
        from doc2json.utils.mongo_util import connect_to_mongo_collection, get_keys
        print("✓ doc2json.utils.mongo_util")
    except ImportError as e:
        print(f"✗ doc2json.utils.mongo_util: {e}")
        return False
    
    try:
        from dotenv import load_dotenv
        print("✓ python-dotenv")
    except ImportError as e:
        print(f"✗ python-dotenv: {e}")
        return False
    
    try:
        from pymongo import MongoClient
        print("✓ pymongo")
    except ImportError as e:
        print(f"✗ pymongo: {e}")
        return False
    
    return True


def test_env_config():
    """Test environment configuration."""
    print("\nTesting environment configuration...")
    
    from dotenv import load_dotenv
    load_dotenv()
    
    required_vars = ['MONGO_IP', 'MONGO_DB', 'PAPERS_COL']
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"✓ {var} = {value}")
        else:
            print(f"✗ {var} is not set")
            return False
    
    optional_vars = ['MONGO_USER', 'MONGO_PASS']
    for var in optional_vars:
        value = os.getenv(var)
        if value:
            print(f"  {var} = {'*' * len(value)} (set)")
        else:
            print(f"  {var} = (not set - optional)")
    
    return True


def test_mongodb_connection():
    """Test MongoDB connection."""
    print("\nTesting MongoDB connection...")
    
    from dotenv import load_dotenv
    from doc2json.utils.mongo_util import connect_to_mongo_collection, get_keys
    
    load_dotenv()
    keys = get_keys()
    
    try:
        collection = connect_to_mongo_collection(
            db_name=keys['mongo_db'],
            collection_name=keys['papers_coll'],
            ip=keys['mongo_ip'],
            username=keys.get('mongo_user'),
            password=keys.get('mongo_pass'),
            auth=bool(keys.get('mongo_user'))
        )
        
        # Try to count documents
        count = collection.count_documents({})
        print(f"✓ Connected to MongoDB successfully")
        print(f"  Database: {keys['mongo_db']}")
        print(f"  Collection: {keys['papers_coll']}")
        print(f"  Document count: {count}")
        return True
        
    except Exception as e:
        print(f"✗ MongoDB connection failed: {e}")
        return False


def test_citation_intent_api():
    """Test citation intent API."""
    print("\nTesting Citation Intent API...")
    
    from doc2json.grobid2json.citation_intent_api import MockCitationIntentAPI
    
    try:
        api = MockCitationIntentAPI()
        
        # Test single prediction
        test_context = "Previous research [1] has shown that deep learning models..."
        test_section = "Introduction"
        
        intent = api.predict_intent(test_context, test_section)
        print(f"✓ Single prediction: intent = '{intent}'")
        
        # Test batch prediction
        test_batch = [
            {"string": "We follow the methodology from [2]...", "sectionName": "Methods"},
            {"string": "Our results align with [3]...", "sectionName": "Results"}
        ]
        
        intents = api.batch_predict(test_batch)
        print(f"✓ Batch prediction: {len(intents)} intents returned")
        
        return True
        
    except Exception as e:
        print(f"✗ Citation Intent API test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 80)
    print("Dataset Generator - Installation Test")
    print("=" * 80)
    print()
    
    results = []
    
    # Test imports
    results.append(("Imports", test_imports()))
    
    # Test environment configuration
    results.append(("Environment Config", test_env_config()))
    
    # Test MongoDB connection
    results.append(("MongoDB Connection", test_mongodb_connection()))
    
    # Test Citation Intent API
    results.append(("Citation Intent API", test_citation_intent_api()))
    
    # Summary
    print()
    print("=" * 80)
    print("Test Summary")
    print("=" * 80)
    
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status:8} {name}")
    
    print()
    
    if all(passed for _, passed in results):
        print("✓ All tests passed! You're ready to use the dataset generator.")
        return 0
    else:
        print("✗ Some tests failed. Please check the errors above.")
        print()
        print("Common fixes:")
        print("  1. Install dependencies: pip install -r requirements.txt")
        print("  2. Configure environment: cp .env.example .env && edit .env")
        print("  3. Start MongoDB: systemctl start mongod")
        return 1


if __name__ == "__main__":
    sys.exit(main())
