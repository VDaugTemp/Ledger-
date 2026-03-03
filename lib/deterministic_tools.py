# lib/deterministic_tools.py
"""Deterministic tools for the controller node.

All functions are pure (no LLM calls, no I/O side effects).
These tools mirror the logic in frontend/src/lib/openQuestions.ts.
"""
from __future__ import annotations

import bisect
import copy
import re
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional

from lib.tax_types import (
    ConfidenceTier,
    DateMathResult,
    DecisionMap,
    NextQuestionItem,
    NextQuestionResult,
    ParseResult,
    PresenceResult,
)

# ── Question catalogue ────────────────────────────────────────────────────────

def _build_catalogue(profile: dict, year: int) -> list[dict]:
    """Build the 17-question catalogue (mirrors openQuestions.ts buildCatalogue)."""
    income = profile.get("incomeTypes") or {}
    has_emp = bool(income.get("employment"))
    has_con = bool(income.get("contractor"))
    has_pas = bool(income.get("passive"))

    base: list[dict] = [
        {
            "id": "presence_trips",
            "fieldPath": "presence.trips",
            "priority": 100,
            "category": "mrd",
            "blocking": True,
            "question": f"What were your entry and exit dates for each trip to Malaysia in {year}? Add all trips.",
            "whyNeeded": "Days in Malaysia determine tax residency status",
            "skipAllowed": True,
        },
        {
            "id": "income_types",
            "fieldPath": "incomeTypes",
            "priority": 95,
            "category": "mrd",
            "blocking": True,
            "question": f"Which income types did you have in {year}? (Employment / Contractor / Passive / Crypto)",
            "whyNeeded": "Income types determine which tax rules apply",
            "skipAllowed": True,
        },
    ]

    if has_emp:
        base += [
            {
                "id": "employment_worked_in_jurisdiction",
                "fieldPath": "employment.workedWhileInJurisdiction",
                "priority": 92,
                "category": "mrd",
                "blocking": True,
                "question": "Did you physically perform any employment work while you were in Malaysia?",
                "whyNeeded": "Determines if income is Malaysia-sourced",
                "skipAllowed": True,
            },
            {
                "id": "employment_foreign_employer",
                "fieldPath": "employment.foreignEmployer",
                "priority": 88,
                "category": "gate",
                "blocking": True,
                "question": "Was your employer foreign (not a Malaysian employer)?",
                "whyNeeded": "Required for DTA assessment",
                "skipAllowed": True,
            },
            {
                "id": "employment_salary_borne_local",
                "fieldPath": "employment.salaryBorneByLocalEntity",
                "priority": 86,
                "category": "gate",
                "blocking": True,
                "question": "Was your salary paid by, recharged to, or borne by a Malaysian entity?",
                "whyNeeded": "Required for DTA assessment",
                "skipAllowed": True,
            },
        ]

    if has_con:
        base += [
            {
                "id": "contractor_services_in_jurisdiction",
                "fieldPath": "contractor.performedServicesInJurisdiction",
                "priority": 92,
                "category": "mrd",
                "blocking": True,
                "question": "Did you physically perform any contractor/freelance services while you were in Malaysia?",
                "whyNeeded": "Determines if income is Malaysia-sourced",
                "skipAllowed": True,
            },
            {
                "id": "contractor_invoiced_local",
                "fieldPath": "contractor.invoicedLocalEntity",
                "priority": 78,
                "category": "advisor",
                "blocking": False,
                "question": "Were any invoices issued to a Malaysian entity?",
                "whyNeeded": "Relevant for compliance risk",
                "skipAllowed": True,
            },
        ]

    if has_pas:
        base += [
            {
                "id": "passive_types",
                "fieldPath": "passive.types",
                "priority": 82,
                "category": "mrd",
                "blocking": True,
                "question": "What passive income did you have? (Dividends / Interest / Rental / Other)",
                "whyNeeded": "Required for FSI branch assessment",
                "skipAllowed": True,
            },
            {
                "id": "passive_remitted",
                "fieldPath": "passive.remittedOrReceivedInJurisdiction",
                "priority": 80,
                "category": "gate",
                "blocking": True,
                "question": "Was any of that passive income received or remitted into Malaysia?",
                "whyNeeded": "Required for FSI guidance",
                "skipAllowed": True,
            },
        ]

    base += [
        {
            "id": "advisor_visa_type",
            "fieldPath": "advisorContext.visaType",
            "priority": 70,
            "category": "advisor",
            "blocking": False,
            "question": "What visa/permit type were you on in Malaysia?",
            "whyNeeded": "Relevant for compliance context",
            "skipAllowed": True,
        },
        {
            "id": "advisor_visa_declared_income",
            "fieldPath": "advisorContext.visaDeclaredIncome",
            "priority": 68,
            "category": "advisor",
            "blocking": False,
            "question": "If applicable: did you declare an annual income on your visa application? If yes, what amount and currency?",
            "whyNeeded": "Relevant for DE Rantau compliance",
            "skipAllowed": True,
        },
        {
            "id": "advisor_files_tax_elsewhere",
            "fieldPath": "advisorContext.filesTaxElsewhere",
            "priority": 60,
            "category": "advisor",
            "blocking": False,
            "question": "Do you currently file or pay tax in another country?",
            "whyNeeded": "Relevant for DTA application",
            "skipAllowed": True,
        },
        {
            "id": "advisor_other_tax_country",
            "fieldPath": "advisorContext.otherTaxCountry",
            "priority": 58,
            "category": "advisor",
            "blocking": False,
            "question": "Which country is that?",
            "whyNeeded": "Identifies applicable DTA",
            "skipAllowed": True,
        },
        {
            "id": "advisor_tax_resident_elsewhere",
            "fieldPath": "advisorContext.taxResidentElsewhere",
            "priority": 56,
            "category": "advisor",
            "blocking": False,
            "question": "Are you considered tax-resident there (to the best of your knowledge)?",
            "whyNeeded": "Relevant for DTA tie-breaker rules",
            "skipAllowed": True,
        },
        {
            "id": "advisor_is_company_director",
            "fieldPath": "advisorContext.isCompanyDirector",
            "priority": 55,
            "category": "advisor",
            "blocking": False,
            "question": "Are you a director of any company?",
            "whyNeeded": "Directors have specific tax obligations",
            "skipAllowed": True,
        },
        {
            "id": "advisor_permanent_home",
            "fieldPath": "advisorContext.permanentHomeInJurisdiction",
            "priority": 45,
            "category": "nice",
            "blocking": False,
            "question": "Did you maintain a home in Malaysia (rent/own/none)?",
            "whyNeeded": "Relevant for habitual residence assessment",
            "skipAllowed": True,
        },
        {
            "id": "advisor_citizenships",
            "fieldPath": "advisorContext.citizenships",
            "priority": 40,
            "category": "nice",
            "blocking": False,
            "question": "What citizenship(s) do you hold?",
            "whyNeeded": "Relevant for nationality-based tax treaties",
            "skipAllowed": True,
        },
    ]

    return base


def _is_field_missing(field_path: str, profile: dict) -> bool:
    """Returns True if the field still needs to be answered."""
    if field_path == "presence.trips":
        trips = (profile.get("presence") or {}).get("trips") or []
        if not trips:
            return True
        return any(not t.get("entryDate") or not t.get("exitDate") for t in trips)

    if field_path == "incomeTypes":
        income = profile.get("incomeTypes") or {}
        return not any(income.values())

    if field_path == "advisorContext.filesTaxElsewhere":
        ctx = profile.get("advisorContext") or {}
        return "filesTaxElsewhere" not in ctx

    if field_path == "advisorContext.otherTaxCountry":
        ctx = profile.get("advisorContext") or {}
        if ctx.get("filesTaxElsewhere") is not True:
            return False
        return not ctx.get("otherTaxCountry")

    if field_path == "advisorContext.visaDeclaredIncome":
        ctx = profile.get("advisorContext") or {}
        vdi = ctx.get("visaDeclaredIncome")
        if vdi is None:
            return True
        return "provided" not in vdi

    if field_path == "advisorContext.citizenships":
        ctx = profile.get("advisorContext") or {}
        return not ctx.get("citizenships")

    if field_path == "passive.types":
        passive = profile.get("passive") or {}
        return not passive.get("types")

    # Generic: resolve by dot-path
    parts = field_path.split(".")
    obj: Any = profile
    for part in parts:
        if not isinstance(obj, dict):
            return True
        obj = obj.get(part)
    if obj is None:
        return True
    if isinstance(obj, str) and obj == "unsure":
        return True
    if isinstance(obj, list) and not obj:
        return True
    return False


def _compute_decision_map(profile: dict) -> DecisionMap:
    income = profile.get("incomeTypes") or {}
    trips = (profile.get("presence") or {}).get("trips") or []
    employment = profile.get("employment") or {}
    passive = profile.get("passive") or {}

    residency_decidable = bool(trips) and all(
        t.get("entryDate") and t.get("exitDate") for t in trips
    )

    income_scope = bool(any(income.values())) and (
        not income.get("employment")
        or employment.get("workedWhileInJurisdiction") in ("yes", "no")
    )

    dta = (
        employment.get("foreignEmployer") in ("yes", "no")
        and employment.get("salaryBorneByLocalEntity") in ("yes", "no")
    ) if income.get("employment") else True

    fsi = (
        bool(passive.get("types"))
        and passive.get("remittedOrReceivedInJurisdiction") in ("yes", "no")
    ) if income.get("passive") else True

    return {
        "residencyDecidable": residency_decidable,
        "incomeScopeDecidable": bool(income_scope),
        "dtaDecidable": bool(dta),
        "fsiDecidable": bool(fsi),
    }


# ── Tool 1: next_question ─────────────────────────────────────────────────────

def next_question(profile: dict, skipped_field_paths: list[str]) -> NextQuestionResult:
    """Deterministically return the highest-priority unanswered question."""
    year = profile.get("assessmentYear") or 2025
    catalogue = _build_catalogue(profile, year)

    missing = [
        q for q in catalogue
        if _is_field_missing(q["fieldPath"], profile)
        and q["fieldPath"] not in skipped_field_paths
    ]
    missing.sort(key=lambda q: q["priority"], reverse=True)

    # Completeness score (blocking questions weighted 2x)
    total_weight = sum(2 if q["blocking"] else 1 for q in catalogue)
    answered_weight = sum(
        2 if q["blocking"] else 1
        for q in catalogue
        if not _is_field_missing(q["fieldPath"], profile)
    )
    completeness = round((answered_weight / total_weight) * 100) if total_weight else 0

    next_q: Optional[NextQuestionItem] = None
    if missing:
        q = missing[0]
        next_q = {
            "id": q["id"],
            "fieldPath": q["fieldPath"],
            "question": q["question"],
            "priority": q["priority"],
        }

    return {
        "nextQuestion": next_q,
        "missingFields": [
            {"id": q["id"], "fieldPath": q["fieldPath"], "question": q["question"], "priority": q["priority"]}
            for q in missing
        ],
        "completenessScore": completeness,
        "decisionMap": _compute_decision_map(profile),
    }


# ── Tool 5: apply_profile_patch ───────────────────────────────────────────────

_NESTED_KEYS = frozenset({"presence", "incomeTypes", "advisorContext", "dataQuality", "employment", "contractor", "passive"})


def apply_profile_patch(profile: dict, patch: dict, meta: dict) -> dict:
    """Deep-merge patch into profile, increment version, update timestamp.
    Does NOT mutate the original profile dict.
    meta is accepted for future audit trail use (not yet persisted).
    """
    result = copy.deepcopy(dict(profile))

    for key, value in patch.items():
        if key in _NESTED_KEYS and value is not None and isinstance(result.get(key), dict):
            result[key] = {**result[key], **value}
        else:
            result[key] = value

    result["profileVersion"] = (result.get("profileVersion") or 0) + 1
    result["updatedAt"] = datetime.now(timezone.utc).isoformat()

    return result


# ── Tool 6: presence_calculator ───────────────────────────────────────────────

def presence_calculator(trips: list[dict], year: int) -> PresenceResult:
    """Count days spent in jurisdiction during the given year.

    rolling12Months is the max trip-days in any 12-month window commencing on a
    trip day that falls within the assessment year — captures the DTA 183-day
    test ("any 12-month period commencing or ending in that year").
    """
    warnings: list[str] = []
    total_days = 0
    year_start = date(year, 1, 1)
    year_end = date(year, 12, 31)

    # Accumulate all trip days (deduplicated) across all years for rolling window
    all_trip_days_set: set[date] = set()

    for trip in trips:
        try:
            entry = date.fromisoformat(trip["entryDate"])
            exit_ = date.fromisoformat(trip["exitDate"])
        except (KeyError, ValueError) as exc:
            warnings.append(f"Trip {trip.get('tripId', '?')} has invalid dates: {exc}")
            continue

        clipped_start = max(entry, year_start)
        clipped_end = min(exit_, year_end)
        if clipped_start <= clipped_end:
            total_days += (clipped_end - clipped_start).days + 1

        d = entry
        while d <= exit_:
            all_trip_days_set.add(d)
            d += timedelta(days=1)

    # For each trip day D in the assessment year, count trip days in [D, D+364]
    all_trip_days = sorted(all_trip_days_set)
    rolling12 = 0
    for d in all_trip_days:
        if not (year_start <= d <= year_end):
            continue
        window_end = d + timedelta(days=364)
        left = bisect.bisect_left(all_trip_days, d)
        right = bisect.bisect_right(all_trip_days, window_end)
        count = right - left
        if count > rolling12:
            rolling12 = count

    return {
        "daysInYear": total_days,
        "near60": 55 <= total_days <= 65,
        "near182": 177 <= total_days <= 182,
        "near183": total_days >= 183,
        "rolling12Months": rolling12,
        "warnings": warnings,
    }


# ── Filing form selector ───────────────────────────────────────────────────────

def filing_form_selector(profile: dict, days_in_year: int) -> dict:
    """Deterministically select the correct Malaysian tax filing form.

    Returns: { "form": "BE"|"B"|"M"|None, "decidable": bool, "reason": str }

    Rules (Malaysian ITA):
      - days_in_year >= 182 → resident
      - Non-resident → Form M
      - Resident + contractor income OR isCompanyDirector → Form B
      - Resident + employment/passive only → Form BE
      - No trip data → decidable=False
    """
    income = profile.get("incomeTypes") or {}
    ctx = profile.get("advisorContext") or {}
    has_trips = bool((profile.get("presence") or {}).get("trips"))

    if not has_trips and days_in_year == 0:
        return {"form": None, "decidable": False, "reason": "No trip data to determine residency"}

    is_resident = days_in_year >= 182

    if not is_resident:
        return {"form": "M", "decidable": True, "reason": f"Non-resident ({days_in_year} days < 182)"}

    has_business = income.get("contractor") or ctx.get("isCompanyDirector")
    if has_business:
        return {"form": "B", "decidable": True, "reason": "Resident with business/contractor income"}

    return {"form": "BE", "decidable": True, "reason": "Resident, employment/passive income only"}


# ── Consistency checker ────────────────────────────────────────────────────────

def consistency_checker(profile: dict, days_in_year: int = 0) -> dict:
    """Flag data contradictions and elevated-risk combinations.

    Returns: { "contradictions": [...], "risk_flags": [...] }
    Each item: { "code": str, "severity": "info"|"warn"|"high", "message": str }
    """
    contradictions: list[dict] = []
    risk_flags: list[dict] = []

    income = profile.get("incomeTypes") or {}
    ctx = profile.get("advisorContext") or {}
    employment = profile.get("employment") or {}
    passive = profile.get("passive") or {}
    trips = (profile.get("presence") or {}).get("trips") or []

    # WORKED_BUT_NO_INCOME_TYPE
    if (employment.get("workedWhileInJurisdiction") == "yes"
            and not income.get("employment")
            and not income.get("contractor")):
        risk_flags.append({
            "code": "WORKED_BUT_NO_INCOME_TYPE",
            "severity": "warn",
            "message": "Worked in jurisdiction but no employment/contractor income type selected",
        })

    # SALARY_BORNE_LOCAL_FOREIGN_EMPLOYER
    if (employment.get("foreignEmployer") == "yes"
            and employment.get("salaryBorneByLocalEntity") == "yes"):
        risk_flags.append({
            "code": "SALARY_BORNE_LOCAL_FOREIGN_EMPLOYER",
            "severity": "warn",
            "message": "Foreign employer with salary borne by local entity — elevated DTA risk",
        })

    # PASSIVE_NO_REMITTANCE_BUT_TYPES_SET
    if passive.get("types") and passive.get("remittedOrReceivedInJurisdiction") == "no":
        risk_flags.append({
            "code": "PASSIVE_NO_REMITTANCE_BUT_TYPES_SET",
            "severity": "info",
            "message": "Passive income types declared but not remitted — FSI exemption may apply",
        })

    # DIRECTOR_NO_EMPLOYMENT
    if ctx.get("isCompanyDirector") is True and not income.get("employment"):
        risk_flags.append({
            "code": "DIRECTOR_NO_EMPLOYMENT",
            "severity": "info",
            "message": "Company director without employment income — director fees may be taxable",
        })

    # TOURIST_VISA_LONG_STAY
    if ctx.get("visaType") == "tourist" and days_in_year >= 60:
        risk_flags.append({
            "code": "TOURIST_VISA_LONG_STAY",
            "severity": "warn",
            "message": f"Tourist visa with {days_in_year} days in jurisdiction — overstay risk",
        })

    # NO_TRIPS_BUT_INCOME_DECLARED
    if not trips and any(income.values()):
        risk_flags.append({
            "code": "NO_TRIPS_BUT_INCOME_DECLARED",
            "severity": "warn",
            "message": "Income types declared but no trip data — presence analysis incomplete",
        })

    return {"contradictions": contradictions, "risk_flags": risk_flags}


# ── Tool 2: intent_classifier ─────────────────────────────────────────────────

_WHAT_IF_RE = re.compile(
    r"\b(what\s+if|suppose|if\s+i\b|imagine|hypothetically|would\s+it\s+be)\b",
    re.IGNORECASE,
)
_DATE_RE = re.compile(
    r"\b(\d{4}-\d{2}-\d{2}|"
    r"\d{1,2}/\d{1,2}/\d{2,4}|"
    r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+\d{4})\b",
    re.IGNORECASE,
)
_FACT_RE = re.compile(
    r"\b(i\s+(am|was|have|earn|work|live|hold|became|got)\b"
    r"|my\s+(visa|employer|income|salary|passport|company)\b"
    r"|\byes\b|\bno\b"
    r"|in\s+malaysia\b)",
    re.IGNORECASE,
)
# Detects genuine questions using first-person phrasing — these are INFO, not PROFILE_INPUT.
# Must be checked before _FACT_RE so "I spent 190 days. Am I resident?" → INFO not PROFILE_INPUT.
_INFO_QUESTION_RE = re.compile(
    r"(\?"                                          # any question mark
    r"|\bam\s+i\b"                                  # "Am I resident?"
    r"|\bdo\s+i\b"                                  # "Do I owe tax?"
    r"|\bdoes\s+(that|it|this|my|the)\b"            # "Does that affect my tax?"
    r"|\bis\s+(my|it|this|that|there|income)\b"     # "Is my salary taxable?"
    r"|\bare\s+(foreign|dividends|they|there)\b"    # "Are foreign dividends taxable?"
    r"|\bwill\s+i\b"                                # "Will I owe?"
    r"|\bwhat\s+(is|are|income|form|happens|changed|counts)\b"  # factual questions
    r"|\bwhich\s+(form|tax|rule|rate)\b"            # "Which form do I use?"
    r"|\bwhen\s+(is|do|should|are)\b"               # "When is the deadline?"
    r"|\bhow\s+(are|is|do|does)\b)",                # "How are they taxed?"
    re.IGNORECASE,
)


def intent_classifier(message: str) -> dict:
    """Rule-based intent classifier. No LLM."""
    if _WHAT_IF_RE.search(message):
        return {"intent": "WHAT_IF"}
    # Questions that use first-person phrasing are INFO requests, not profile data submissions.
    # Check before _FACT_RE to avoid misclassifying "I spent X days. Am I resident?" as PROFILE_INPUT.
    if _INFO_QUESTION_RE.search(message):
        return {"intent": "INFO"}
    if _DATE_RE.search(message) or _FACT_RE.search(message):
        return {"intent": "PROFILE_INPUT"}
    return {"intent": "INFO"}


# ── Tool 4: date_math ─────────────────────────────────────────────────────────

_MONTH_MAP = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6,
    "jul": 7, "july": 7, "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9, "oct": 10, "october": 10,
    "nov": 11, "november": 11, "dec": 12, "december": 12,
}


def _parse_month_year(text: str, today: date) -> Optional[tuple[int, int]]:
    """Returns (year, month) or None."""
    text = text.strip().lower()
    # "November 2024" or "Nov 2024"
    m = re.match(r"(\w+)\s+(\d{4})", text)
    if m:
        month = _MONTH_MAP.get(m.group(1)[:3])
        year = int(m.group(2))
        if month:
            return (year, month)
    # "2024-11"
    m = re.match(r"(\d{4})-(\d{2})", text)
    if m:
        return (int(m.group(1)), int(m.group(2)))
    # "now" / "today" / "present"
    if text in ("now", "today", "present"):
        return (today.year, today.month)
    # Just month name → use today's year
    month = _MONTH_MAP.get(text[:3])
    if month:
        return (today.year, month)
    return None


def date_math(range_text: str, today_iso: str, clip_year: Optional[int] = None) -> DateMathResult:
    """Normalise natural-language date ranges to ISO dates."""
    try:
        today = date.fromisoformat(today_iso)
    except ValueError:
        today = date.today()

    text_lower = range_text.lower().strip()
    warnings: list[str] = []
    entry_date: Optional[str] = None
    exit_date: Optional[str] = None
    confidence: str = "estimated"

    # ISO pair: "2024-11-01 to 2024-12-31"
    iso_m = re.search(r"(\d{4}-\d{2}-\d{2})\s+(?:to|until|-)\s+(\d{4}-\d{2}-\d{2})", range_text)
    if iso_m:
        entry_date = iso_m.group(1)
        exit_date = iso_m.group(2)
        confidence = "exact"
    else:
        # "since <month year>" or "from <month year> [to <month year>]"
        since_m = re.match(
            r"(?:since|from)\s+(.+?)(?:\s+(?:to|until)\s+(.+))?$",
            text_lower,
        )
        if since_m:
            start_str = since_m.group(1).strip()
            end_str = (since_m.group(2) or "").strip()

            start_my = _parse_month_year(start_str, today)
            if start_my:
                entry_date = f"{start_my[0]}-{start_my[1]:02d}-01"

            end_is_now = end_str in ("now", "today", "present", "")
            if end_is_now:
                exit_date = today.isoformat()
            elif end_str:
                end_my = _parse_month_year(end_str, today)
                if end_my:
                    # Last day of end month
                    if end_my[1] == 12:
                        last = date(end_my[0], 12, 31)
                    else:
                        last = date(end_my[0], end_my[1] + 1, 1) - timedelta(days=1)
                    exit_date = last.isoformat()
        elif re.search(r"\b(until\s+now|to\s+now|to\s+today|to\s+present)\b", text_lower):
            exit_date = today.isoformat()

    # Compute days in clip year
    days_in_clip: Optional[int] = None
    if clip_year and entry_date and exit_date:
        try:
            e = date.fromisoformat(entry_date)
            x = date.fromisoformat(exit_date)
            ys = date(clip_year, 1, 1)
            ye = date(clip_year, 12, 31)
            cs = max(e, ys)
            cx = min(x, ye)
            if cs <= cx:
                days_in_clip = (cx - cs).days + 1
        except ValueError:
            warnings.append("Could not compute days in year due to invalid dates")

    if not entry_date and not exit_date:
        warnings.append("Could not parse date range from input")

    result: DateMathResult = {"dateConfidence": confidence, "warnings": warnings}  # type: ignore[typeddict-item]
    if entry_date:
        result["entryDate"] = entry_date
    if exit_date:
        result["exitDate"] = exit_date
    if days_in_clip is not None:
        result["daysInClipYear"] = days_in_clip
    return result


# ── Tool 3: parse_answer_for_field ────────────────────────────────────────────

_SKIP_PHRASES = (
    "prefer not to answer", "prefer not", "rather not", "skip",
    "don't want to say", "do not want to say", "no comment",
)
_YES_RE = re.compile(r"\b(yes|yep|yeah|affirmative|correct|right|indeed)\b", re.IGNORECASE)
_NO_RE = re.compile(r"\b(no|nope|negative|not)\b", re.IGNORECASE)

_PASSIVE_KW = {"dividends": "dividends", "dividend": "dividends", "interest": "interest",
               "rental": "rental", "rent": "rental", "other": "other"}
_INCOME_KW = {"employment": "employment", "employed": "employment", "salary": "employment",
              "payroll": "employment", "contractor": "contractor", "freelance": "contractor",
              "freelancer": "contractor", "consulting": "contractor", "passive": "passive",
              "crypto": "crypto", "cryptocurrency": "crypto", "bitcoin": "crypto"}
_VISA_KW = {"de rantau": "de_rantau", "derantau": "de_rantau",
            "tourist": "tourist", "employment pass": "employment_pass", "mm2h": "other"}

_YNU_FIELDS = {
    "employment.workedWhileInJurisdiction",
    "employment.foreignEmployer",
    "employment.salaryBorneByLocalEntity",
    "contractor.performedServicesInJurisdiction",
    "contractor.invoicedLocalEntity",
    "passive.remittedOrReceivedInJurisdiction",
    "advisorContext.taxResidentElsewhere",
}
_BOOL_FIELDS = {
    "advisorContext.filesTaxElsewhere",
    "advisorContext.isCompanyDirector",
}


def _detect_skip(message: str) -> bool:
    msg = message.lower()
    return any(phrase in msg for phrase in _SKIP_PHRASES)


def _detect_yes_no(message: str) -> Optional[str]:
    if _YES_RE.search(message):
        return "yes"
    if _NO_RE.search(message):
        return "no"
    return None


def _set_nested(parts: list[str], value: Any) -> dict:
    if len(parts) == 1:
        return {parts[0]: value}
    return {parts[0]: _set_nested(parts[1:], value)}


def parse_answer_for_field(
    field_path: str,
    message: str,
    today_iso: str,
    timezone_str: str = "UTC",
) -> ParseResult:
    """Parse user message for a specific field. Returns patch or skip signal."""
    if _detect_skip(message):
        return {"patch": {}, "confidenceTier": "high", "skip": True}

    if field_path == "presence.trips":
        return _parse_trips(message, today_iso)

    if field_path == "incomeTypes":
        return _parse_income_types(message)

    if field_path in _YNU_FIELDS:
        return _parse_yes_no_unsure(field_path, message)

    if field_path in _BOOL_FIELDS:
        return _parse_boolean(field_path, message)

    if field_path == "passive.types":
        return _parse_passive_types(message)

    if field_path == "advisorContext.visaType":
        return _parse_visa_type(message)

    if field_path == "advisorContext.citizenships":
        return _parse_citizenships(message)

    if field_path == "advisorContext.otherTaxCountry":
        cleaned = message.strip()
        if 1 < len(cleaned) < 100:
            return {"patch": {"advisorContext": {"otherTaxCountry": cleaned}}, "confidenceTier": "medium"}
        return {"patch": {}, "confidenceTier": "low",
                "needsClarification": "Which country do you file taxes in?"}

    return {"patch": {}, "confidenceTier": "low",
            "needsClarification": f"Could you be more specific about {field_path}?"}


def _parse_trips(message: str, today_iso: str) -> ParseResult:
    # ISO pair (exact)
    iso_dates = re.findall(r"\d{4}-\d{2}-\d{2}", message)
    if len(iso_dates) >= 2:
        trip = {"tripId": str(uuid.uuid4()), "country": "MY",
                "entryDate": iso_dates[0], "exitDate": iso_dates[1], "dateConfidence": "exact"}
        return {"patch": {"presence": {"trips": [trip]}}, "confidenceTier": "high"}

    # Natural language
    dm = date_math(message, today_iso)
    if dm.get("entryDate") and dm.get("exitDate"):
        trip = {"tripId": str(uuid.uuid4()), "country": "MY",
                "entryDate": dm["entryDate"], "exitDate": dm["exitDate"],
                "dateConfidence": dm.get("dateConfidence", "estimated")}
        tier: ConfidenceTier = "medium" if dm.get("dateConfidence") == "estimated" else "high"
        return {"patch": {"presence": {"trips": [trip]}}, "confidenceTier": tier}

    return {"patch": {}, "confidenceTier": "low",
            "needsClarification": "Could you give me the exact entry and exit dates for your Malaysia trip? (e.g. 2024-01-15 to 2024-03-20)"}


def _parse_income_types(message: str) -> ParseResult:
    msg = message.lower()
    found: dict[str, bool] = {}
    for kw, income_type in _INCOME_KW.items():
        if kw in msg:
            found[income_type] = True
    if found:
        return {"patch": {"incomeTypes": found}, "confidenceTier": "high"}
    return {"patch": {}, "confidenceTier": "low",
            "needsClarification": "Which income types did you have? (Employment / Contractor / Passive / Crypto)"}


_UNSURE_ABOUT_RE = re.compile(r"\bnot\s+sure\s+about\b", re.IGNORECASE)


def _parse_yes_no_unsure(field_path: str, message: str) -> ParseResult:
    msg = message.lower()
    # "not sure about that/it" is hedging, not an explicit "unsure" answer
    if _UNSURE_ABOUT_RE.search(message):
        return {"patch": {}, "confidenceTier": "low",
                "needsClarification": f"Could you answer yes, no, or unsure for: {field_path}?"}
    if "unsure" in msg or "not sure" in msg or "don't know" in msg:
        return {"patch": _set_nested(field_path.split("."), "unsure"), "confidenceTier": "high"}
    ans = _detect_yes_no(message)
    if ans:
        return {"patch": _set_nested(field_path.split("."), ans), "confidenceTier": "high"}
    return {"patch": {}, "confidenceTier": "low",
            "needsClarification": f"Could you answer yes, no, or unsure for: {field_path}?"}


def _parse_boolean(field_path: str, message: str) -> ParseResult:
    ans = _detect_yes_no(message)
    if ans is not None:
        return {"patch": _set_nested(field_path.split("."), ans == "yes"), "confidenceTier": "high"}
    return {"patch": {}, "confidenceTier": "low",
            "needsClarification": f"Could you answer yes or no for: {field_path}?"}


def _parse_passive_types(message: str) -> ParseResult:
    msg = message.lower()
    found: list[str] = []
    for kw, pt in _PASSIVE_KW.items():
        if kw in msg and pt not in found:
            found.append(pt)
    if found:
        return {"patch": {"passive": {"types": found}}, "confidenceTier": "high"}
    return {"patch": {}, "confidenceTier": "low",
            "needsClarification": "What types of passive income? (Dividends / Interest / Rental / Other)"}


def _parse_visa_type(message: str) -> ParseResult:
    msg = message.lower()
    for kw, vt in _VISA_KW.items():
        if kw in msg:
            return {"patch": {"advisorContext": {"visaType": vt}}, "confidenceTier": "high"}
    if "other" in msg:
        return {"patch": {"advisorContext": {"visaType": "other"}}, "confidenceTier": "medium"}
    return {"patch": {}, "confidenceTier": "low",
            "needsClarification": "What visa type were you on? (DE Rantau / Tourist / Employment Pass / Other)"}


def _parse_citizenships(message: str) -> ParseResult:
    codes = re.findall(r"\b([A-Z]{2})\b", message)
    if codes:
        return {"patch": {"advisorContext": {"citizenships": codes}}, "confidenceTier": "high"}
    return {"patch": {}, "confidenceTier": "low",
            "needsClarification": "What citizenship(s) do you hold? Use country codes (e.g. GB, US, MY)"}


# ── Topic classifier ──────────────────────────────────────────────────────────

_DTA_RE = re.compile(
    r"\b(DTA\b|treaty\s+list|which\s+countries|double\s+tax\s+(agreement|treaty)|DTA\s+list|countries.{0,30}(DTA|treaty))",
    re.IGNORECASE,
)
_PR_RE = re.compile(
    r"\b(PR|public\s+ruling|guidelines?|amended|replaced|updated\s+ruling)\b",
    re.IGNORECASE,
)
_FILING_RE = re.compile(
    r"\b(deadline|due\s+date|filing\s+date|Form\s+BE|Form\s+B\b|Form\s+M\b|extension)\b",
    re.IGNORECASE,
)


def topic_classifier(message: str) -> dict:
    """Deterministic topic classifier. No LLM.

    Returns: { "topic": "DTA_COUNTRY_LIST" | "PUBLIC_RULING_UPDATE" | "FILING_DEADLINE_CHANGE" | "OTHER" }
    """
    if _DTA_RE.search(message):
        return {"topic": "DTA_COUNTRY_LIST"}
    if _PR_RE.search(message):
        return {"topic": "PUBLIC_RULING_UPDATE"}
    if _FILING_RE.search(message):
        return {"topic": "FILING_DEADLINE_CHANGE"}
    return {"topic": "OTHER"}


# ── Freshness detector ────────────────────────────────────────────────────────

_FRESHNESS_RE = re.compile(
    r"\b(has\s+this\s+changed|latest\s+(PR|ruling|guideline|DTA|list|rule)|"
    r"still\s+valid|most\s+recent|current\s+rule|updated|has\s+it\s+been|"
    r"any\s+changes?|recently\s+(changed|updated|amended))\b",
    re.IGNORECASE,
)


def freshness_requested(message: str) -> bool:
    """Return True if user message signals a request for fresh/current information."""
    return bool(_FRESHNESS_RE.search(message))
