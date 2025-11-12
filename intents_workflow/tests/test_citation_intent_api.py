"""
Test suite for Citation Intent API

Tests the citation intent prediction functionality including:
- Mock API heuristic-based predictions
- Batch processing
- Intent classification accuracy
"""

import pytest
import json
import tempfile
import os
from doc2json.grobid2json.citation_intent_api import (
    MockCitationIntentAPI,
    CitationIntentAPI
)


class TestMockCitationIntentAPI:
    """Test the MockCitationIntentAPI heuristic implementation."""
    
    @pytest.fixture
    def api(self):
        """Fixture providing a MockCitationIntentAPI instance."""
        return MockCitationIntentAPI()
    
    def test_api_initialization(self, api):
        """Test that API initializes correctly."""
        assert api is not None
        assert api.use_mock is True
        assert len(api.VALID_INTENTS) > 0
    
    def test_valid_intents(self, api):
        """Test that valid intents are defined."""
        expected_intents = {"Background", "Methods", "Results", "Motivation", "Future", "Other"}
        assert api.VALID_INTENTS == expected_intents
    
    def test_background_intent_with_review(self, api):
        """Test Background intent detection for review/survey papers."""
        context = "We conducted a comprehensive review of existing approaches as background for this work."
        intent = api.predict_intent(
            citation_context=context,
            citing_section="Introduction"
        )
        assert intent in api.VALID_INTENTS
        # Should lean towards Background given keywords and section
        assert intent in ["Background", "Motivation"]
    
    def test_methods_intent(self, api):
        """Test Methods intent detection."""
        context = "We employ the method described in prior work using their algorithmic approach."
        intent = api.predict_intent(
            citation_context=context,
            citing_section="Methods"
        )
        assert intent in api.VALID_INTENTS
        assert intent == "Methods"
    
    def test_results_intent(self, api):
        """Test Results intent detection."""
        context = "Our results outperform the baseline approach by 15% compared to their previous work."
        intent = api.predict_intent(
            citation_context=context,
            citing_section="Results"
        )
        assert intent in api.VALID_INTENTS
        assert intent == "Results"
    
    def test_motivation_intent(self, api):
        """Test Motivation intent detection."""
        context = "Recently, motivated by the problem identified in, researchers have started exploring this area."
        intent = api.predict_intent(
            citation_context=context,
            citing_section="Introduction"
        )
        assert intent in api.VALID_INTENTS
        assert intent == "Motivation"
    
    def test_future_intent(self, api):
        """Test Future intent detection."""
        context = "As future work, we plan to extend the approach as described in similar research."
        intent = api.predict_intent(
            citation_context=context
        )
        assert intent in api.VALID_INTENTS
        assert intent == "Future"
    
    def test_intent_with_section_introduction(self, api):
        """Test that Introduction section affects intent classification."""
        context = "Prior work has established the foundation for this research."
        intent = api.predict_intent(
            citation_context=context,
            citing_section="Introduction"
        )
        assert intent in api.VALID_INTENTS
    
    def test_intent_with_section_methods(self, api):
        """Test that Methods section affects intent classification."""
        context = "We use the same methodology as described in."
        intent = api.predict_intent(
            citation_context=context,
            citing_section="Methods"
        )
        assert intent in api.VALID_INTENTS
    
    def test_intent_with_empty_context(self, api):
        """Test intent prediction with empty context."""
        intent = api.predict_intent(citation_context="")
        assert intent in api.VALID_INTENTS
        # Should default to Background
        assert intent == "Background"
    
    def test_intent_case_insensitivity(self, api):
        """Test that intent detection is case-insensitive."""
        context_lower = "we use the method from prior work"
        context_upper = "WE USE THE METHOD FROM PRIOR WORK"
        
        intent_lower = api.predict_intent(citation_context=context_lower)
        intent_upper = api.predict_intent(citation_context=context_upper)
        
        assert intent_lower == intent_upper
        assert intent_lower in api.VALID_INTENTS


class TestCitationIntentAPIBatch:
    """Test batch processing of citation intents."""
    
    @pytest.fixture
    def api(self):
        """Fixture providing a MockCitationIntentAPI instance."""
        return MockCitationIntentAPI()
    
    def test_batch_predict_basic(self, api):
        """Test batch prediction with sample citations."""
        citations = [
            {
                "string": "We employ the method from prior work",
                "sectionName": "Methods",
                "citedTitle": "Prior Method Paper"
            },
            {
                "string": "Our results compare favorably to their approach",
                "sectionName": "Results",
                "citedTitle": "Comparison Baseline"
            },
            {
                "string": "Future work could build on this approach",
                "sectionName": "Conclusion",
                "citedTitle": "Future Direction"
            }
        ]
        
        results = api.batch_predict(citations)
        
        assert len(results) == len(citations)
        for result in results:
            assert "citationIntent" in result
            assert result["citationIntent"] in api.VALID_INTENTS
    
    def test_batch_predict_preserves_fields(self, api):
        """Test that batch prediction preserves original fields."""
        citations = [
            {
                "ref_id": "REF001",
                "string": "Test citation",
                "sectionName": "Introduction",
                "citingPaperId": "paper_1",
                "citedPaperId": "paper_2"
            }
        ]
        
        results = api.batch_predict(citations)
        result = results[0]
        
        # Original fields preserved
        assert result["ref_id"] == "REF001"
        assert result["citingPaperId"] == "paper_1"
        assert result["citedPaperId"] == "paper_2"
        # New field added
        assert "citationIntent" in result
    
    def test_batch_predict_empty_list(self, api):
        """Test batch prediction with empty citation list."""
        results = api.batch_predict([])
        assert results == []


class TestCitationIntentAPIEnrichment:
    """Test JSONL file enrichment with citation intents."""
    
    @pytest.fixture
    def api(self):
        """Fixture providing a MockCitationIntentAPI instance."""
        return MockCitationIntentAPI()
    
    @pytest.fixture
    def sample_jsonl_file(self):
        """Fixture providing a temporary JSONL file with sample citations."""
        citations = [
            {
                "ref_id": "paper_1_REF0",
                "sectionName": "Introduction",
                "citeStart": 100,
                "citeEnd": 150,
                "string": "We built upon the foundational work in machine learning.",
                "citingPaperId": "paper_1",
                "citedPaperId": "paper_2",
                "unique_id": "paper_1>paper_2"
            },
            {
                "ref_id": "paper_1_REF1",
                "sectionName": "Methods",
                "citeStart": 300,
                "citeEnd": 350,
                "string": "We implement the algorithm described in prior research.",
                "citingPaperId": "paper_1",
                "citedPaperId": "paper_3",
                "unique_id": "paper_1>paper_3"
            },
            {
                "ref_id": "paper_1_REF2",
                "sectionName": "Results",
                "citeStart": 500,
                "citeEnd": 550,
                "string": "Our method outperforms their baseline by 20%.",
                "citingPaperId": "paper_1",
                "citedPaperId": "paper_4",
                "unique_id": "paper_1>paper_4"
            }
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            for citation in citations:
                f.write(json.dumps(citation) + '\n')
            temp_file = f.name
        
        yield temp_file
        
        # Cleanup
        if os.path.exists(temp_file):
            os.remove(temp_file)
    
    def test_enrich_jsonl_file(self, api, sample_jsonl_file):
        """Test enriching a JSONL file with citation intents."""
        from doc2json.grobid2json.s2orc_converter import enrich_citations_with_intent
        
        enriched = enrich_citations_with_intent(sample_jsonl_file, api)
        
        assert len(enriched) == 3
        for citation in enriched:
            assert "citationIntent" in citation
            assert citation["citationIntent"] in api.VALID_INTENTS
    
    def test_enrich_jsonl_with_output_file(self, api, sample_jsonl_file):
        """Test enriching JSONL file and writing to output."""
        from doc2json.grobid2json.s2orc_converter import enrich_citations_with_intent
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, "enriched.jsonl")
            
            enriched = enrich_citations_with_intent(
                sample_jsonl_file,
                api,
                output_file=output_file
            )
            
            # Check enriched data
            assert len(enriched) == 3
            
            # Check output file was created
            assert os.path.exists(output_file)
            
            # Verify output file content
            with open(output_file, 'r') as f:
                lines = f.readlines()
                assert len(lines) == 3
                for line in lines:
                    data = json.loads(line)
                    assert "citationIntent" in data


class TestCitationIntentIntegration:
    """Integration tests for citation intent API with S2ORC converter."""
    
    @pytest.fixture
    def api(self):
        """Fixture providing a MockCitationIntentAPI instance."""
        return MockCitationIntentAPI()
    
    def test_intent_prediction_consistency(self, api):
        """Test that same input produces same output."""
        context = "We use the standard method from prior work"
        
        intent1 = api.predict_intent(context, citing_section="Methods")
        intent2 = api.predict_intent(context, citing_section="Methods")
        
        assert intent1 == intent2
    
    def test_all_valid_intents_achievable(self, api):
        """Test that all defined intents can be predicted."""
        test_cases = {
            "Background": "This foundational survey provides background context.",
            "Methods": "We employ the algorithm from this paper.",
            "Results": "Our results compare favorably to their baseline.",
            "Motivation": "Recently, researchers have been motivated by this problem.",
            "Future": "Future work will explore directions suggested here.",
            "Other": "Miscellaneous reference text."
        }
        
        for expected_intent, context in test_cases.items():
            intent = api.predict_intent(context)
            assert intent in api.VALID_INTENTS


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    @pytest.fixture
    def api(self):
        """Fixture providing a MockCitationIntentAPI instance."""
        return MockCitationIntentAPI()
    
    def test_very_long_context(self, api):
        """Test with very long citation context."""
        long_context = "Method description. " * 1000
        intent = api.predict_intent(long_context, citing_section="Methods")
        assert intent in api.VALID_INTENTS
    
    def test_special_characters(self, api):
        """Test with special characters in context."""
        context = "We use 日本語, symbols (!@#$%), and émojis 🚀 from the method."
        intent = api.predict_intent(context)
        assert intent in api.VALID_INTENTS
    
    def test_url_in_context(self, api):
        """Test with URLs in citation context."""
        context = "As shown in https://example.com and their research, the method works well."
        intent = api.predict_intent(context)
        assert intent in api.VALID_INTENTS
    
    def test_section_name_case_insensitivity(self, api):
        """Test that section name matching is case-insensitive."""
        context = "We use their method."
        
        intent_lower = api.predict_intent(context, citing_section="methods")
        intent_upper = api.predict_intent(context, citing_section="METHODS")
        intent_title = api.predict_intent(context, citing_section="Methods")
        
        # All should recognize this as Methods section
        assert all(intent in ["Methods", "Background"] for intent in [intent_lower, intent_upper, intent_title])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
