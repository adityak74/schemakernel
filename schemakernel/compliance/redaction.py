from typing import Any, List, Optional
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine


class RedactionEngine:
    """
    PII Detection and Redaction engine using Microsoft Presidio.
    """

    def __init__(self, entities: Optional[List[str]] = None):
        """
        Initialize the Redaction Engine.

        Args:
            entities: List of PII entities to redact.
                     Defaults to PERSON, EMAIL_ADDRESS, PHONE_NUMBER, LOCATION, URL, IP_ADDRESS.
        """
        self.analyzer = AnalyzerEngine()
        self.anonymizer = AnonymizerEngine()
        self.entities = entities or [
            "PERSON",
            "EMAIL_ADDRESS",
            "PHONE_NUMBER",
            "LOCATION",
            "URL",
            "IP_ADDRESS",
        ]

    def redact_text(self, text: str) -> str:
        """
        Detect and redact PII from a single string.
        """
        if not text:
            return text

        # Analyze text for PII
        results = self.analyzer.analyze(text=text, entities=self.entities, language="en")

        # Anonymize text
        anonymized_result = self.anonymizer.anonymize(
            text=text, analyzer_results=results
        )

        return anonymized_result.text

    def redact_data(self, data: Any) -> Any:
        """
        Recursively redact PII from strings within dictionaries and lists.
        """
        if isinstance(data, str):
            return self.redact_text(data)
        elif isinstance(data, dict):
            return {k: self.redact_data(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self.redact_data(item) for item in data]
        else:
            return data
