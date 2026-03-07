"""Tests for query builder."""

from geotcha.search.query_builder import (
    build_query,
    expand_disease_terms,
    get_relevance_keywords,
)


class TestExpandDiseaseTerms:
    def test_known_disease_expands(self):
        terms = expand_disease_terms("IBD")
        assert "inflammatory bowel disease" in terms
        assert "ulcerative colitis" in terms
        assert "crohn's disease" in terms

    def test_case_insensitive(self):
        terms = expand_disease_terms("ibd")
        assert len(terms) > 1

    def test_unknown_disease_returns_original(self):
        terms = expand_disease_terms("some rare disease")
        assert terms == ["some rare disease"]

    def test_ambiguous_abbreviations_excluded_from_search(self):
        """Short ambiguous abbreviations like UC, CD should NOT be in search terms."""
        terms = expand_disease_terms("IBD")
        assert "UC" not in terms
        assert "CD" not in terms

    def test_unambiguous_abbreviations_included(self):
        """Longer/unambiguous abbreviations like IBD should be in search terms."""
        terms = expand_disease_terms("IBD")
        assert "IBD" in terms


class TestGetRelevanceKeywords:
    def test_includes_ambiguous_abbreviations(self):
        """Relevance keywords should include all terms, even ambiguous ones."""
        keywords = get_relevance_keywords("IBD")
        assert "UC" in keywords
        assert "CD" in keywords
        assert "inflammatory bowel disease" in keywords

    def test_unknown_query_returns_original(self):
        keywords = get_relevance_keywords("some rare disease")
        assert keywords == ["some rare disease"]

    def test_ulcerative_colitis_keywords(self):
        keywords = get_relevance_keywords("ulcerative colitis")
        assert "ulcerative colitis" in keywords
        assert "UC" in keywords


class TestOntologyAwareExpansion:
    def test_breast_cancer_includes_subtypes(self):
        terms = expand_disease_terms("breast cancer")
        assert "breast cancer" in terms
        assert any("carcinoma" in t for t in terms)
        assert len(terms) > 1

    def test_lung_cancer_includes_carcinoma(self):
        terms = expand_disease_terms("lung cancer")
        assert "lung cancer" in terms
        assert "lung carcinoma" in terms

    def test_melanoma_includes_subtypes(self):
        terms = expand_disease_terms("melanoma")
        assert "melanoma" in terms
        assert len(terms) > 1

    def test_unknown_disease_no_expansion(self):
        terms = expand_disease_terms("completely fictional disease xyz")
        assert terms == ["completely fictional disease xyz"]

    def test_short_term_no_noise(self):
        """Short terms (< 4 chars) should not trigger noisy ontology expansion."""
        terms = expand_disease_terms("flu")
        assert "flu" in terms

    def test_ibd_gets_ontology_subtypes_too(self):
        """Hand-curated + ontology expansions should combine."""
        terms = expand_disease_terms("IBD")
        assert "inflammatory bowel disease" in terms
        assert len(terms) > 5

    def test_expansion_is_cached(self):
        """Second call should use cache."""
        t1 = expand_disease_terms("glioblastoma")
        t2 = expand_disease_terms("glioblastoma")
        assert t1 == t2

    def test_build_query_includes_subtypes(self):
        query = build_query("breast cancer")
        assert "breast carcinoma" in query


class TestBuildQuery:
    def test_builds_entrez_query(self):
        query = build_query("IBD")
        assert "Homo sapiens" in query
        assert "high throughput sequencing" in query
        assert "inflammatory bowel disease" in query

    def test_excludes_ambiguous_abbreviations(self):
        """Built query should not contain ambiguous abbreviations."""
        query = build_query("IBD")
        # CD and UC should not appear as search terms
        assert '"CD"' not in query
        assert '"UC"' not in query

    def test_unknown_term_still_builds(self):
        query = build_query("some disease")
        assert '"some disease"' in query
        assert "Homo sapiens" in query
