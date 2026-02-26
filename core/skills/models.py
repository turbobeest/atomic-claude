"""Pydantic models for the skill subsystem."""

import logging
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class RiskLevel(str, Enum):
    """Skill risk classification."""
    NONE = "None"
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


# Ordered for comparison
_RISK_ORDER = {RiskLevel.NONE: 0, RiskLevel.LOW: 1, RiskLevel.MEDIUM: 2, RiskLevel.HIGH: 3}


def risk_at_most(level: RiskLevel, ceiling: RiskLevel) -> bool:
    """Return True if level <= ceiling in risk ordering."""
    return _RISK_ORDER.get(level, 0) <= _RISK_ORDER.get(ceiling, 0)


class GravityLevel(str, Enum):
    """Task consequence density classification."""
    LIGHT = "light"
    STANDARD = "standard"
    INTENSIVE = "intensive"


class SkillCategory(str, Enum):
    """Skill functional categories."""
    FORMATTING = "formatting"
    VALIDATION = "validation"
    EXTRACTION = "extraction"
    GIT_OPS = "git-ops"
    FILE_OPS = "file-ops"
    PHASE_CHECKS = "phase-checks"
    DOC_GEN = "doc-gen"
    TESTING = "testing"
    SECURITY = "security"
    ARCHITECTURE = "architecture"
    DEPLOYMENT = "deployment"
    MONITORING = "monitoring"
    DATA = "data"
    API = "api"
    PERFORMANCE = "performance"
    ACCESSIBILITY = "accessibility"


class SkillSource(str, Enum):
    """Origin of a skill definition."""
    TACTICAL_BUILTIN = "tactical-builtin"
    COMMUNITY = "community"
    PLAYBOOKS = "playbooks"
    AWESOME_CLAUDE_CODE = "awesome-claude-code"
    ANTHROPIC_OFFICIAL = "anthropic-official"


# Profile names matching core/features/profiles.py
PROFILE_NAMES = ("air_gapped", "enterprise_secure", "cloud_full", "development")

# Profile skill gating rules
PROFILE_SKILL_RULES: Dict[str, Dict[str, Any]] = {
    "air_gapped": {
        "allow_internet": False,
        "allow_saas": False,
        "max_risk": RiskLevel.LOW,
    },
    "enterprise_secure": {
        "allow_internet": True,
        "allow_saas": False,
        "max_risk": RiskLevel.LOW,
    },
    "cloud_full": {
        "allow_internet": True,
        "allow_saas": True,
        "max_risk": RiskLevel.MEDIUM,
    },
    "development": {
        "allow_internet": True,
        "allow_saas": True,
        "max_risk": RiskLevel.HIGH,
    },
}


class SkillMetadata(BaseModel):
    """Single skill from the catalog. Maps 1:1 to a Skill graph node."""
    id: str
    name: str
    description: str = ""
    sdlc_phases: List[int] = Field(default_factory=list)
    category: str = ""
    source: str = ""
    source_url: Optional[str] = None
    requires_internet: bool = False
    requires_saas: bool = False
    saas_dependencies: List[str] = Field(default_factory=list)
    security_scan_needed: bool = False
    risk_level: RiskLevel = RiskLevel.NONE
    risk_notes: str = ""
    well_known: bool = False
    official: bool = False
    license: str = "MIT"
    # Runtime state
    installed: bool = False
    install_path: str = ""
    content_hash: str = ""
    blocked_by_profile: Optional[str] = None
    times_used: int = 0
    avg_success_score: float = 0.0
    last_used_at: Optional[datetime] = None

    model_config = {"extra": "allow"}

    def installable_in_profiles(self) -> List[str]:
        """Compute which environment profiles allow this skill."""
        profiles: List[str] = []
        rl = self.risk_level if isinstance(self.risk_level, RiskLevel) else RiskLevel(self.risk_level)

        for profile_name, rules in PROFILE_SKILL_RULES.items():
            max_risk = rules["max_risk"]
            if self.requires_internet and not rules["allow_internet"]:
                continue
            if self.requires_saas and not rules["allow_saas"]:
                continue
            if not risk_at_most(rl, max_risk):
                continue
            profiles.append(profile_name)

        return profiles


class GravitySignal(BaseModel):
    """Individual signal from the gravity classifier."""
    name: str
    score: float = 0.0
    weight: float = 1.0
    matches: List[str] = Field(default_factory=list)
    floor: Optional[GravityLevel] = None


class GravityAssessment(BaseModel):
    """Result of the gravity classifier."""
    gravity: GravityLevel
    confidence: float = Field(ge=0.0, le=1.0)
    raw_score: float = 0.0
    gravity_floor: GravityLevel = GravityLevel.LIGHT
    method: str = "multi_signal_classifier"
    signals: List[GravitySignal] = Field(default_factory=list)
    reasoning: str = ""


class SkillSelection(BaseModel):
    """Result of the skill selection pipeline."""
    skills: List[SkillMetadata] = Field(default_factory=list)
    workflow: Optional[str] = None
    method: str = ""
    gravity: GravityLevel = GravityLevel.STANDARD
    profile: str = "cloud_full"
