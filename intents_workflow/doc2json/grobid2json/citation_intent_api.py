"""
Citation Intent API Client

This module provides a client for classifying citation intents using the SciCite scheme.

Citation intents follow the SciCite 3-class taxonomy:
- background information: Citations providing context, background, or foundational information
- method: Citations of methods, tools, approaches, or datasets being used
- result comparison: Citations comparing results or findings with other work

Reference: Cohan et al. "Structural Scaffolds for Citation Intent Classification in Scientific Publications" (NAACL 2019)
"""

from typing import Optional, Dict, List
import requests
import json


class CitationIntentAPI:
    """
    Client for classifying citation intents using an external API.
    
    This is a prototype that can be configured to call either:
    1. A real external API (e.g., S2-RL Citation Intent endpoint)
    2. A local mock implementation for testing
    """
    
    # SciCite 3-class scheme (production)
    SCICITE_INTENTS = {
        "background information", 
        "method", 
        "results comparison"
    }
    
    # For backward compatibility
    VALID_INTENTS = SCICITE_INTENTS
    
    def __init__(self, api_url: Optional[str] = None, use_mock: bool = True):
        """
        Initialize the Citation Intent API client.
        
        :param api_url: URL to the citation intent API endpoint
        :param use_mock: If True, use mock implementation instead of API
        """
        self.api_url = api_url
        self.use_mock = use_mock
    
    def predict_intent(self, citation_context: str, cite_start: int = 0, cite_end: int = 0, 
                       cited_title: str = "", citing_section: str = "") -> str:
        """
        Predict the intent of a citation.
        
        :param citation_context: The full text context containing the citation
        :param cite_start: Start position of citation in text (0-indexed)
        :param cite_end: End position of citation in text
        :param cited_title: Title of the cited paper
        :param citing_section: Section where citation appears (e.g., "Introduction", "Methods")
        :return: Citation intent category
        """
        if self.use_mock:
            return self._mock_predict(citation_context, cited_title, citing_section)
        else:
            return self._api_predict(citation_context, cite_start, cite_end, cited_title, citing_section)
    
    def _mock_predict(self, citation_context: str, cited_title: str = "", citing_section: str = "") -> str:
        """
        Mock implementation for testing without API calls.
        Uses heuristics based on section and keywords.
        
        :param citation_context: The full text context containing the citation
        :param cited_title: Title of the cited paper
        :param citing_section: Section where citation appears
        :return: Citation intent category
        """
        # Heuristic rules for intent classification
        context_lower = citation_context.lower()
        
        # Section-based heuristics
        if citing_section.lower() in ["introduction", "related work", "background"]:
            if any(word in context_lower for word in ["survey", "review", "overview", "background"]):
                return "Background"
            elif any(word in context_lower for word in ["motivat", "recently", "growing", "emerging"]):
                return "Motivation"
        
        elif citing_section.lower() in ["methods", "methodology", "approach"]:
            if any(word in context_lower for word in ["use", "employ", "apply", "implement", "method"]):
                return "Methods"
        
        elif citing_section.lower() in ["results", "experiments", "evaluation"]:
            if any(word in context_lower for word in ["comparison", "compared", "result", "outperform", "baseline"]):
                return "Results"
        
        # Keyword-based heuristics
        if any(word in context_lower for word in ["future work", "future research", "ongoing", "plan"]):
            return "Future"
        
        if any(word in context_lower for word in ["method", "algorithm", "technique", "approach", "framework"]):
            return "Methods"
        
        if any(word in context_lower for word in ["result", "show", "find", "outperform", "achieve"]):
            return "Results"
        
        if any(word in context_lower for word in ["motivat", "prompt", "inspire", "address"]):
            return "Motivation"
        
        # Default to Background for foundational papers
        return "Background"
    
    def _api_predict(self, citation_context: str, cite_start: int, cite_end: int, 
                     cited_title: str = "", citing_section: str = "") -> str:
        """
        Make API call to external citation intent service.
        
        The API expects the full text and citation positions. It will preprocess
        the text internally to replace the citation span with @@CITATION@@ tag.
        
        :param citation_context: The full text context containing the citation
        :param cite_start: Start position of citation in text (0-indexed)
        :param cite_end: End position of citation in text
        :param cited_title: Title of the cited paper (not used by current API)
        :param citing_section: Section where citation appears (not used by current API)
        :return: Citation intent category
        """
        try:
            payload = {
                "text": citation_context,
                "cite_start": cite_start,
                "cite_end": cite_end
            }
            
            response = requests.post(
                f"{self.api_url}/classify",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Get predicted class from API response
                predicted_class = result.get("predicted_class")
                is_valid = result.get("valid", False)
                
                if is_valid and predicted_class:
                    return predicted_class
                else:
                    print(f"Invalid prediction from API: {result.get('raw_prediction')}")
                    return "Other"
            else:
                print(f"API Error: {response.status_code} - {response.text}")
                return "Other"
        
        except requests.exceptions.RequestException as e:
            print(f"API Request failed: {e}")
            return "Other"
        except Exception as e:
            print(f"Error predicting intent: {e}")
            return "Other"
    
    def batch_predict(self, citations: List[Dict]) -> List[Dict]:
        """
        Predict intents for multiple citations in batch.
        
        :param citations: List of citation dictionaries with 'string', 'citedTitle', 'sectionName' keys
        :return: Same citations with added 'citationIntent' field
        """
        results = []
        for citation in citations:
            citation_copy = citation.copy()
            intent = self.predict_intent(
                citation_context=citation.get("string", ""),
                cited_title=citation.get("citedTitle", ""),
                citing_section=citation.get("sectionName", "")
            )
            citation_copy["citationIntent"] = intent
            results.append(citation_copy)
        
        return results


class MockCitationIntentAPI(CitationIntentAPI):
    """
    Convenience class for using mock implementation with diverse heuristics.
    
    Uses a richer 6-class scheme for testing and development:
    - Background: Foundational work or context
    - Motivation: Work that motivates the current research
    - Methods: Methodologies or techniques being used
    - Results: Comparative results or findings
    - Future: Future work directions
    - Extension: Extending previous work
    
    Note: Production APIs should use SCICITE_INTENTS (3-class scheme).
    """
    
    # Mock API uses a 6-class scheme for detailed testing
    MOCK_INTENTS = {
        "Background",
        "Motivation", 
        "Methods",
        "Results",
        "Future",
        "Extension"
    }
    
    # Override VALID_INTENTS to use mock scheme
    VALID_INTENTS = MOCK_INTENTS
    
    def __init__(self):
        super().__init__(use_mock=True)


class ExternalCitationIntentAPI(CitationIntentAPI):
    """
    Convenience class for using external API implementation.
    
    Expected to return SciCite 3-class scheme:
    - background information
    - method
    - result comparison
    """
    
    # External API uses SciCite scheme
    VALID_INTENTS = CitationIntentAPI.SCICITE_INTENTS
    
    def __init__(self, api_url: str):
        if not api_url:
            raise ValueError("api_url must be provided for external API")
        super().__init__(api_url=api_url, use_mock=False)
