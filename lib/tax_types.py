# lib/tax_types.py
"""Python type aliases mirroring frontend/src/lib/types.ts.
Used by deterministic tools and LangGraph state.
"""
from __future__ import annotations
from typing import Any, Literal, Optional, TypedDict

# ── Enum literals ─────────────────────────────────────────────────────────────
Intent = Literal["INFO", "PROFILE_INPUT", "WHAT_IF"]
ConfidenceTier = Literal["high", "medium", "low"]
YesNoUnsure = Literal["yes", "no", "unsure"]


# ── Profile sub-types ─────────────────────────────────────────────────────────
class Trip(TypedDict, total=False):
    tripId: str
    country: str
    entryDate: str           # ISO "YYYY-MM-DD"
    exitDate: str            # ISO "YYYY-MM-DD"
    dateConfidence: Literal["exact", "estimated"]
    notes: str


class IncomeTypes(TypedDict, total=False):
    employment: bool
    contractor: bool
    passive: bool
    crypto: bool


class AdvisorContext(TypedDict, total=False):
    filesTaxElsewhere: bool
    otherTaxCountry: str
    taxResidentElsewhere: YesNoUnsure
    citizenships: list[str]
    visaType: Literal["de_rantau", "tourist", "employment_pass", "other"]
    visaDeclaredIncome: dict[str, Any]
    isCompanyDirector: bool
    permanentHomeInJurisdiction: Literal["rent", "own", "none"]


class NextQuestionItem(TypedDict):
    id: str
    fieldPath: str
    question: str
    priority: int


class DataQuality(TypedDict, total=False):
    mrdComplete: bool
    intakeCompleted: bool
    missingFields: list[NextQuestionItem]
    completenessScore: float


class Profile(TypedDict, total=False):
    profileVersion: int
    updatedAt: str
    jurisdiction: str
    assessmentYear: int
    presence: dict[str, Any]        # {"trips": list[Trip]}
    incomeTypes: IncomeTypes
    employment: Optional[dict[str, Any]]
    contractor: Optional[dict[str, Any]]
    passive: Optional[dict[str, Any]]
    advisorContext: AdvisorContext
    dataQuality: DataQuality


# ── Tool output types ─────────────────────────────────────────────────────────
class DecisionMap(TypedDict):
    residencyDecidable: bool
    incomeScopeDecidable: bool
    dtaDecidable: bool
    fsiDecidable: bool


class NextQuestionResult(TypedDict):
    nextQuestion: Optional[NextQuestionItem]
    missingFields: list[NextQuestionItem]
    completenessScore: float
    decisionMap: DecisionMap


class ParseResult(TypedDict, total=False):
    patch: dict[str, Any]           # Partial<Profile>
    confidenceTier: ConfidenceTier
    needsClarification: Optional[str]
    skip: bool


class DateMathResult(TypedDict, total=False):
    entryDate: Optional[str]
    exitDate: Optional[str]
    dateConfidence: Literal["exact", "estimated"]
    daysInClipYear: Optional[int]
    warnings: list[str]


class PresenceResult(TypedDict):
    daysInYear: int
    near60: bool
    near182: bool
    near183: bool
    rolling12Months: int   # max days in any 12-month window commencing in the assessment year
    warnings: list[str]


class PatchMeta(TypedDict, total=False):
    source: Literal["wizard", "chat", "user_edit"]
    fieldPath: Optional[str]
    questionId: Optional[str]
    confidenceTier: Optional[ConfidenceTier]
    rawUserText: Optional[str]
    timestampIso: str


# ── TaskPacket ────────────────────────────────────────────────────────────────
class RetrievalFilters(TypedDict, total=False):
    jurisdiction: str
    doc_type: list[str]
    topic_tags: list[str]
    min_authority_rank: int


class Flag(TypedDict):
    code: str
    severity: Literal["info", "warn", "high"]
    message: str


class TaskPacket(TypedDict, total=False):
    intent: Intent
    nextQuestion: Optional[NextQuestionItem]
    profileSummary: str
    retrievalQuery: Optional[str]
    retrievalFilters: Optional[RetrievalFilters]
    decisionMap: DecisionMap
    flags: list[Flag]
