"""Tests for search result filtering, including relevance and single-cell checks."""

from geotcha.search.filters import _is_relevant_to_query, _is_single_cell


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


class TestIsSingleCell:
    def test_scrna_in_title(self):
        """Title containing 'scRNA-seq' should be detected as single-cell."""
        summary = {
            "title": "scRNA-seq of human colon in IBD",
            "summary": "We profiled gene expression at single-cell resolution.",
        }
        assert _is_single_cell(summary) is True

    def test_10x_genomics_in_summary(self):
        """Summary mentioning '10x Genomics Chromium' should be detected."""
        summary = {
            "title": "Immune cell atlas of ulcerative colitis",
            "summary": "Libraries were prepared using 10x Genomics Chromium platform.",
        }
        assert _is_single_cell(summary) is True

    def test_single_cell_in_title(self):
        """Title with 'single-cell' should be detected."""
        summary = {
            "title": "Single-cell transcriptomics of Crohn's disease",
            "summary": "Analysis of intestinal immune cells.",
        }
        assert _is_single_cell(summary) is True

    def test_single_nucleus_detected(self):
        """'single-nucleus' should be detected as single-cell."""
        summary = {
            "title": "Single-nucleus RNA-seq of brain tissue",
            "summary": "snRNA-seq profiling.",
        }
        assert _is_single_cell(summary) is True

    def test_dropseq_detected(self):
        """'Drop-seq' should be detected as single-cell."""
        summary = {
            "title": "Drop-seq analysis of gut epithelium",
            "summary": "Droplet-based single-cell sequencing.",
        }
        assert _is_single_cell(summary) is True

    def test_bulk_rnaseq_not_flagged(self):
        """Normal bulk RNA-seq should NOT be flagged as single-cell."""
        summary = {
            "title": "Bulk RNA-seq of IBD colon biopsies",
            "summary": "Transcriptomic analysis of paired biopsies from UC patients.",
        }
        assert _is_single_cell(summary) is False

    def test_standard_rnaseq_not_flagged(self):
        """Standard RNA-seq dataset without single-cell keywords passes."""
        summary = {
            "title": "Gene expression in pediatric IBD",
            "summary": "RNA-seq of whole blood samples from IBD patients and controls.",
        }
        assert _is_single_cell(summary) is False
