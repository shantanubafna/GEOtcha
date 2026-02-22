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
