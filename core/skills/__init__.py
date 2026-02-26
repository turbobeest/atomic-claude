"""
Skill subsystem for atomic-claude.

Provides skill catalog, gravity assessment, graph-aware selection,
episodic learning, installation, and nightly consolidation.
"""

from .models import (
    GravityAssessment,
    GravityLevel,
    GravitySignal,
    PROFILE_NAMES,
    PROFILE_SKILL_RULES,
    RiskLevel,
    SkillCategory,
    SkillMetadata,
    SkillSelection,
    SkillSource,
    risk_at_most,
)
from .catalog import (
    SKILL_CATALOG,
    get_catalog_stats,
    get_skill,
    get_skills_by_category,
    get_skills_for_phase,
    get_skills_for_profile,
)
from .gravity import GravityClassifier, extract_keywords
from .selector import SkillSelector
from .learning import SkillLearning
from .installer import SkillInstaller
from .consolidation import SkillConsolidation

__all__ = [
    # Models
    "GravityAssessment",
    "GravityLevel",
    "GravitySignal",
    "PROFILE_NAMES",
    "PROFILE_SKILL_RULES",
    "RiskLevel",
    "SkillCategory",
    "SkillMetadata",
    "SkillSelection",
    "SkillSource",
    "risk_at_most",
    # Catalog
    "SKILL_CATALOG",
    "get_catalog_stats",
    "get_skill",
    "get_skills_by_category",
    "get_skills_for_phase",
    "get_skills_for_profile",
    # Classifier
    "GravityClassifier",
    "extract_keywords",
    # Selector
    "SkillSelector",
    # Learning
    "SkillLearning",
    # Installer
    "SkillInstaller",
    # Consolidation
    "SkillConsolidation",
]
