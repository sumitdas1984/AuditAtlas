import pytest
from src.knowledge_engineering.router import QueryClassifier, Router, Topic, Intent, Scope, SourceType


class TestQueryClassifier:
    def setup_method(self):
        self.classifier = QueryClassifier()

    def test_classify_pcaob_standards_query(self):
        result = self.classifier.classify("What does PCAOB say about auditor independence?")
        assert result.topic == Topic.AUDIT_STANDARDS
        assert result.intent in [Intent.DEFINITION, Intent.UNCLASSIFIED]
        assert result.confidence > 0.5

    def test_classify_risk_factors_query(self):
        result = self.classifier.classify("What are Apple's risk factors?")
        assert result.topic == Topic.RISK_FACTORS
        assert result.scope == Scope.SPECIFIC

    def test_classify_finding_query(self):
        result = self.classifier.classify("Show me audit findings for the e-commerce process")
        assert result.topic == Topic.AUDIT_FINDINGS
        assert result.intent == Intent.FINDING

    def test_classify_policy_query(self):
        result = self.classifier.classify("What is the policy on data retention?")
        assert result.topic == Topic.POLICY_PROCEDURE

    def test_classify_control_query(self):
        result = self.classifier.classify("What controls exist for payment processing?")
        assert result.topic == Topic.INTERNAL_CONTROLS

    def test_classify_intent_requirement(self):
        result = self.classifier.classify("What must auditors do under AS 2201?")
        assert result.intent == Intent.REQUIREMENT

    def test_classify_intent_definition(self):
        result = self.classifier.classify("What is audit evidence?")
        assert result.intent == Intent.DEFINITION

    def test_classify_intent_finding(self):
        result = self.classifier.classify("Show me findings about vendor onboarding")
        assert result.intent == Intent.FINDING

    def test_classify_intent_comparison(self):
        result = self.classifier.classify("Compare AAPL and AMZN risk factors")
        assert result.intent == Intent.COMPARISON

    def test_classify_scope_specific_ticker(self):
        result = self.classifier.classify("AAPL 10-K risk factors")
        assert result.scope == Scope.SPECIFIC

    def test_classify_scope_specific_standard(self):
        result = self.classifier.classify("AS 1105 requirements")
        assert result.scope == Scope.SPECIFIC

    def test_classify_scope_general(self):
        result = self.classifier.classify("What are auditing standards?")
        assert result.scope == Scope.GENERAL

    def test_classify_unclassified_fallback(self):
        result = self.classifier.classify("asdfghjkl random text")
        assert result.topic == Topic.UNCLASSIFIED


class TestRouter:
    def setup_method(self):
        self.router = Router()
        self.classifier = QueryClassifier()

    def test_route_pcaob_query_returns_source_a(self):
        result = self.router.route("What does PCAOB say about independence?", self.classifier)
        assert SourceType.SOURCE_A in result.sources
        assert len(result.sources) >= 1

    def test_route_risk_factors_returns_source_b(self):
        result = self.router.route("What are Apple's risk factors?", self.classifier)
        assert SourceType.SOURCE_B in result.sources

    def test_route_audit_findings_returns_source_c(self):
        result = self.router.route("Show me audit findings for e-commerce", self.classifier)
        assert SourceType.SOURCE_C in result.sources

    def test_route_policy_returns_source_c(self):
        result = self.router.route("What is the policy on vendor onboarding?", self.classifier)
        assert SourceType.SOURCE_C in result.sources

    def test_route_requirement_intent_overrides_to_source_a(self):
        result = self.router.route("What must auditors do?", self.classifier)
        assert SourceType.SOURCE_A in result.sources

    def test_route_finding_intent_overrides_to_source_c(self):
        result = self.router.route("Show me findings about controls", self.classifier)
        assert SourceType.SOURCE_C in result.sources

    def test_route_compliance_routes_to_all_sources(self):
        result = self.router.route("What are the compliance requirements?", self.classifier)
        assert SourceType.SOURCE_A in result.sources
        assert SourceType.SOURCE_B in result.sources
        assert SourceType.SOURCE_C in result.sources

    def test_route_unclassified_routes_to_all_sources(self):
        result = self.router.route("Tell me about everything", self.classifier)
        assert len(result.sources) == 3

    def test_route_specific_scope_narrows_sources(self):
        result = self.router.route("AS 1105 § .12", self.classifier)
        assert result.sources == [SourceType.SOURCE_A]

    def test_route_without_classifier_uses_default(self):
        result = self.router.route("What are risk factors?")
        assert len(result.sources) >= 1

    def test_routing_result_has_confidence(self):
        result = self.router.route("Show me audit findings")
        assert result.confidence > 0
        assert result.confidence <= 1

    def test_routing_result_has_reasoning(self):
        result = self.router.route("What are risk factors?")
        assert len(result.reasoning) > 0
