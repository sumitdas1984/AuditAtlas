import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from .citation import SourceType


class Topic(str, Enum):
    AUDIT_STANDARDS = "audit_standards"
    RISK_FACTORS = "risk_factors"
    FINANCIALS = "financials"
    INTERNAL_CONTROLS = "internal_controls"
    AUDIT_FINDINGS = "audit_findings"
    RISK_REGISTER = "risk_register"
    POLICY_PROCEDURE = "policy_procedure"
    COMPLIANCE = "compliance"
    UNCLASSIFIED = "unclassified"


class Intent(str, Enum):
    DEFINITION = "definition"
    REQUIREMENT = "requirement"
    FINDING = "finding"
    EXAMPLE = "example"
    COMPARISON = "comparison"
    UNCLASSIFIED = "unclassified"


class Scope(str, Enum):
    SPECIFIC = "specific"
    GENERAL = "general"


@dataclass
class ClassificationResult:
    topic: Topic
    intent: Intent
    scope: Scope
    confidence: float
    reasoning: str


@dataclass
class RoutingResult:
    sources: list[SourceType]
    confidence: float
    reasoning: str


TOPIC_KEYWORDS = {
    Topic.AUDIT_STANDARDS: ["pcaob", "standard", "auditing standard", "as ", "qc ", "ei "],
    Topic.RISK_FACTORS: ["risk factor", "risk factor", "item 1a"],
    Topic.FINANCIALS: ["financial statement", "md&a", "item 7", "item 8", "revenue", "balance sheet"],
    Topic.INTERNAL_CONTROLS: ["internal control", "internal controls", "control matrix", "control deficiency", "control exist", "controls", "item 9a"],
    Topic.AUDIT_FINDINGS: ["audit finding", "finding", "observation", "internal audit report", "ia-"],
    Topic.RISK_REGISTER: ["risk register", "risk rating", "risk category", "likelihood", "impact"],
    Topic.POLICY_PROCEDURE: ["policy", "sop", "standard operating procedure", "procedure manual"],
    Topic.COMPLIANCE: ["compliance", "regulatory", "sox", "sec requirement"],
}

INTENT_PATTERNS = {
    Intent.DEFINITION: [r"^what is\b", r"^what are\b", r"^define\b", r"^explain\b", r"^how does\b", r"^what does\b"],
    Intent.REQUIREMENT: [r"^what (does|must|should|shall)\b", r"^require", r"^mandate"],
    Intent.FINDING: [r"^show me\b", r"^findings\b", r"^observations\b", r"^audit findings\b"],
    Intent.EXAMPLE: [r"^example\b", r"^for example\b", r"^such as\b", r"^illustrate"],
    Intent.COMPARISON: [r"^compare\b", r"^difference\b", r"^versus\b", r"^vs\b"],
}

SCOPE_SPECIFIC_PATTERNS = [
    r"\b(AS|QC|EI)\s*\d+\b",
    r"\b[A-Z]{2,5}\s+10-K\b",
    r"\b[A-Z]{1,5}\s+10-K\b",
    r"\b[A-Z]{2,5}\s+10Q\b",
    r"\bIA-\d+-\d+\b",
    r"\bCTL-\w+\b",
    r"\bRISK-\w+\b",
    r"\b[A-Z][a-z]+'s\b",  # Possessive company names: Apple's, Microsoft's
]


class QueryClassifier:
    def classify(self, query: str) -> ClassificationResult:
        topic = self._classify_topic(query)
        intent = self._classify_intent(query)
        scope = self._classify_scope(query)
        confidence = self._calculate_confidence(topic, intent, scope)

        reasoning = f"Topic: {topic.value} (query mentions: {self._extract_topic_evidence(query)}), "
        reasoning += f"Intent: {intent.value}, Scope: {scope.value}"

        return ClassificationResult(
            topic=topic,
            intent=intent,
            scope=scope,
            confidence=confidence,
            reasoning=reasoning,
        )

    def _classify_topic(self, query: str) -> Topic:
        query_lower = query.lower()
        scores = {}

        for topic, keywords in TOPIC_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in query_lower)
            if score > 0:
                scores[topic] = score

        if not scores:
            return Topic.UNCLASSIFIED

        return max(scores, key=scores.get)

    def _classify_intent(self, query: str) -> Intent:
        query_lower = query.lower()

        for intent, patterns in INTENT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    return intent

        return Intent.UNCLASSIFIED

    def _classify_scope(self, query: str) -> Scope:
        for pattern in SCOPE_SPECIFIC_PATTERNS:
            if re.search(pattern, query, re.IGNORECASE):
                return Scope.SPECIFIC
        return Scope.GENERAL

    def _calculate_confidence(self, topic: Topic, intent: Intent, scope: Scope) -> float:
        confidence = 0.5

        if topic != Topic.UNCLASSIFIED:
            confidence += 0.2
        if intent != Intent.UNCLASSIFIED:
            confidence += 0.15
        if scope == Scope.SPECIFIC:
            confidence += 0.15

        return min(confidence, 1.0)

    def _extract_topic_evidence(self, query: str) -> str:
        query_lower = query.lower()
        evidence = []
        for topic, keywords in TOPIC_KEYWORDS.items():
            for kw in keywords:
                if kw in query_lower:
                    evidence.append(kw)
                    break
        return ", ".join(evidence[:3])


class Router:
    ROUTING_TABLE = {
        Topic.AUDIT_STANDARDS: ([SourceType.SOURCE_A], []),
        Topic.RISK_FACTORS: ([SourceType.SOURCE_B], [SourceType.SOURCE_C]),
        Topic.FINANCIALS: ([SourceType.SOURCE_B], []),
        Topic.INTERNAL_CONTROLS: ([SourceType.SOURCE_A, SourceType.SOURCE_C], []),
        Topic.AUDIT_FINDINGS: ([SourceType.SOURCE_C], []),
        Topic.RISK_REGISTER: ([SourceType.SOURCE_C], []),
        Topic.POLICY_PROCEDURE: ([SourceType.SOURCE_C], []),
        Topic.COMPLIANCE: ([SourceType.SOURCE_A, SourceType.SOURCE_B, SourceType.SOURCE_C], []),
        Topic.UNCLASSIFIED: ([SourceType.SOURCE_A, SourceType.SOURCE_B, SourceType.SOURCE_C], []),
    }

    # Strong intent overrides - always apply regardless of topic
    STRONG_INTENT_OVERRIDES = {
        Intent.REQUIREMENT: [SourceType.SOURCE_A],
        Intent.FINDING: [SourceType.SOURCE_C],
    }

    # Weak intent overrides - only apply when topic is UNCLASSIFIED
    WEAK_INTENT_OVERRIDES = {
        Intent.DEFINITION: [SourceType.SOURCE_A, SourceType.SOURCE_C],
        Intent.EXAMPLE: [SourceType.SOURCE_C, SourceType.SOURCE_B],
        Intent.COMPARISON: [SourceType.SOURCE_A, SourceType.SOURCE_B, SourceType.SOURCE_C],
    }

    def route(self, query: str, classifier: Optional[QueryClassifier] = None) -> RoutingResult:
        if classifier is None:
            classifier = QueryClassifier()

        classification = classifier.classify(query)
        topic = classification.topic
        intent = classification.intent

        primary: list[SourceType] = []
        secondary: list[SourceType] = []

        # Strong intent overrides always apply
        if intent in self.STRONG_INTENT_OVERRIDES:
            sources = self.STRONG_INTENT_OVERRIDES[intent]
            primary = list(sources)
            secondary = []
        # Weak intent overrides only apply when topic is unclassified
        elif topic == Topic.UNCLASSIFIED and intent in self.WEAK_INTENT_OVERRIDES:
            sources = self.WEAK_INTENT_OVERRIDES[intent]
            primary = list(sources)
            secondary = []
        elif topic in self.ROUTING_TABLE:
            primary, secondary = self.ROUTING_TABLE[topic]
        # Fallback: use weak intent override if topic routing didn't match
        elif intent in self.WEAK_INTENT_OVERRIDES:
            sources = self.WEAK_INTENT_OVERRIDES[intent]
            primary = list(sources)
            secondary = []

        all_sources = primary + [s for s in secondary if s not in primary]

        reasoning = f"Topic '{topic.value}' with intent '{intent.value}' -> "
        reasoning += f"primary sources: {[s.value for s in primary]}"
        if secondary:
            reasoning += f", secondary: {[s.value for s in secondary]}"

        confidence = classification.confidence if primary else 0.3

        return RoutingResult(
            sources=all_sources,
            confidence=confidence,
            reasoning=reasoning,
        )
