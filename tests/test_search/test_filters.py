"""Tests for search result filtering, including relevance checks."""

from geotcha.search.filters import _is_relevant_to_query


class TestIsRelevantToQuery:
    def test_ibd_dataset_is_relevant(self):
        """A dataset about inflammatory bowel disease should pass relevance check."""
        summary = {
            "title": "Gene expression in ulcerative colitis patients",
            "summary": "RNA-seq of colon biopsies from IBD patients and healthy controls.",
        }
        assert _is_relevant_to_query(summary, "IBD") is True

    def test_unrelated_dataset_rejected(self):
        """A dataset about cladoniamide D (matching 'CD' as substring) should fail."""
        summary = {
            "title": "Cladoniamide D biosynthesis gene cluster",
            "summary": "Characterization of cladoniamide D production in Streptomyces.",
        }
        assert _is_relevant_to_query(summary, "IBD") is False

    def test_short_abbreviation_word_boundary(self):
        """Short abbreviations should require word-boundary matching."""
        # "CD" inside "encoded" should NOT match
        summary = {
            "title": "Analysis of encoded proteins",
            "summary": "Study of CDA gene expression.",
        }
        assert _is_relevant_to_query(summary, "crohn's disease") is False

    def test_short_abbreviation_standalone_matches(self):
        """Standalone 'CD' as a word should match for Crohn's disease."""
        summary = {
            "title": "CD patient transcriptome analysis",
            "summary": "RNA-seq of CD and UC patients.",
        }
        assert _is_relevant_to_query(summary, "IBD") is True

    def test_full_disease_name_matches(self):
        """Full disease names should always match (case-insensitive substring)."""
        summary = {
            "title": "Study of Crohn's Disease",
            "summary": "Analysis of gene expression.",
        }
        assert _is_relevant_to_query(summary, "IBD") is True

    def test_case_insensitive_matching(self):
        """Matching should be case-insensitive."""
        summary = {
            "title": "INFLAMMATORY BOWEL DISEASE study",
            "summary": "",
        }
        assert _is_relevant_to_query(summary, "IBD") is True

    def test_unknown_query_uses_literal(self):
        """Unknown queries should match literally."""
        summary = {
            "title": "Psoriasis transcriptome",
            "summary": "Gene expression in psoriasis patients.",
        }
        assert _is_relevant_to_query(summary, "psoriasis") is True

    def test_no_match_returns_false(self):
        """Completely unrelated dataset should return False."""
        summary = {
            "title": "Yeast fermentation study",
            "summary": "Saccharomyces cerevisiae growth curves.",
        }
        assert _is_relevant_to_query(summary, "IBD") is False
