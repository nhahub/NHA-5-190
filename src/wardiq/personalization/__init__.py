"""Personalization and wardrobe optimization modules for Milestone 4."""

from wardiq.personalization.gap_analysis import (
    CompatibilityEvidence,
    GapCandidateRecord,
    RedundancyAssessment,
    RejectedGapCandidate,
    WardrobeGapAnalysisResult,
    analyze_wardrobe_gaps,
    load_gap_analysis_config,
)

__all__ = [
    "CompatibilityEvidence",
    "GapCandidateRecord",
    "RedundancyAssessment",
    "RejectedGapCandidate",
    "WardrobeGapAnalysisResult",
    "analyze_wardrobe_gaps",
    "load_gap_analysis_config",
]
