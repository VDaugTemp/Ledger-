import pytest
from lib.deterministic_tools import (
    next_question,
    presence_calculator,
    apply_profile_patch,
)


def _empty_profile() -> dict:
    return {
        "profileVersion": 1,
        "updatedAt": "2025-01-01T00:00:00Z",
        "jurisdiction": "MY",
        "assessmentYear": 2025,
        "presence": {"trips": []},
        "incomeTypes": {"employment": False, "contractor": False, "passive": False, "crypto": False},
        "advisorContext": {
            "filesTaxElsewhere": False,
            "citizenships": [],
            "visaDeclaredIncome": {"provided": False},
        },
        "dataQuality": {"mrdComplete": False, "missingFields": [], "completenessScore": 0},
    }


# ── next_question ─────────────────────────────────────────────────────────────

def test_next_question_empty_profile_returns_trips_first():
    result = next_question(_empty_profile(), [])
    assert result["nextQuestion"]["fieldPath"] == "presence.trips"
    assert result["nextQuestion"]["priority"] == 100


def test_next_question_skips_skipped_fields():
    result = next_question(_empty_profile(), ["presence.trips"])
    assert result["nextQuestion"]["fieldPath"] == "incomeTypes"


def test_next_question_shows_employment_questions_only_when_employment_true():
    profile = _empty_profile()
    profile["incomeTypes"]["employment"] = True
    result = next_question(profile, ["presence.trips", "incomeTypes"])
    assert result["nextQuestion"]["fieldPath"] == "employment.workedWhileInJurisdiction"


def test_next_question_no_employment_questions_when_employment_false():
    profile = _empty_profile()
    profile["incomeTypes"]["employment"] = False
    all_fps = [r["fieldPath"] for r in next_question(profile, [])["missingFields"]]
    assert "employment.workedWhileInJurisdiction" not in all_fps


def test_next_question_completeness_increases_as_fields_filled():
    profile = _empty_profile()
    score_empty = next_question(profile, [])["completenessScore"]
    profile["presence"]["trips"] = [
        {"tripId": "1", "country": "MY", "entryDate": "2025-01-01", "exitDate": "2025-03-01", "dateConfidence": "exact"}
    ]
    score_with_trips = next_question(profile, [])["completenessScore"]
    assert score_with_trips > score_empty


def test_next_question_decision_map_residency_false_without_trips():
    result = next_question(_empty_profile(), [])
    assert result["decisionMap"]["residencyDecidable"] is False


def test_next_question_decision_map_residency_true_with_complete_trips():
    profile = _empty_profile()
    profile["presence"]["trips"] = [
        {"tripId": "1", "country": "MY", "entryDate": "2025-01-01", "exitDate": "2025-06-01", "dateConfidence": "exact"}
    ]
    result = next_question(profile, [])
    assert result["decisionMap"]["residencyDecidable"] is True


def test_next_question_passive_questions_only_when_passive_true():
    profile = _empty_profile()
    profile["incomeTypes"]["passive"] = True
    all_fps = [r["fieldPath"] for r in next_question(profile, [])["missingFields"]]
    assert "passive.types" in all_fps


def test_next_question_no_passive_questions_when_passive_false():
    profile = _empty_profile()
    all_fps = [r["fieldPath"] for r in next_question(profile, [])["missingFields"]]
    assert "passive.types" not in all_fps


# ── presence_calculator ───────────────────────────────────────────────────────

def test_presence_empty_trips():
    result = presence_calculator([], 2025)
    assert result["daysInYear"] == 0
    assert result["near60"] is False
    assert result["near183"] is False


def test_presence_single_trip_31_days():
    trips = [{"tripId": "1", "country": "MY", "entryDate": "2025-01-01", "exitDate": "2025-01-31", "dateConfidence": "exact"}]
    result = presence_calculator(trips, 2025)
    assert result["daysInYear"] == 31


def test_presence_near183_flag():
    trips = [{"tripId": "1", "country": "MY", "entryDate": "2025-01-01", "exitDate": "2025-07-02", "dateConfidence": "exact"}]
    result = presence_calculator(trips, 2025)
    assert result["near183"] is True


def test_presence_clips_to_year():
    trips = [{"tripId": "1", "country": "MY", "entryDate": "2024-12-01", "exitDate": "2025-01-31", "dateConfidence": "exact"}]
    result = presence_calculator(trips, 2025)
    assert result["daysInYear"] == 31  # only Jan 2025


def test_presence_invalid_dates_adds_warning():
    trips = [{"tripId": "1", "country": "MY", "entryDate": "not-a-date", "exitDate": "2025-01-31"}]
    result = presence_calculator(trips, 2025)
    assert result["daysInYear"] == 0
    assert len(result["warnings"]) > 0


def test_presence_near60_flag():
    # 60 days = Jan + Feb + 1 day of March 2025
    trips = [{"tripId": "1", "country": "MY", "entryDate": "2025-01-01", "exitDate": "2025-03-01", "dateConfidence": "exact"}]
    result = presence_calculator(trips, 2025)
    assert result["near60"] is True


# ── apply_profile_patch ───────────────────────────────────────────────────────

def test_apply_patch_increments_version():
    profile = _empty_profile()
    meta = {"source": "chat", "timestampIso": "2025-01-01T00:00:00Z"}
    result = apply_profile_patch(profile, {"assessmentYear": 2024}, meta)
    assert result["profileVersion"] == 2
    assert result["assessmentYear"] == 2024


def test_apply_patch_deep_merges_advisor_context():
    profile = _empty_profile()
    profile["advisorContext"]["filesTaxElsewhere"] = True
    meta = {"source": "chat", "timestampIso": "2025-01-01T00:00:00Z"}
    patch = {"advisorContext": {"visaType": "de_rantau"}}
    result = apply_profile_patch(profile, patch, meta)
    assert result["advisorContext"]["visaType"] == "de_rantau"
    assert result["advisorContext"]["filesTaxElsewhere"] is True  # not erased


def test_apply_patch_does_not_mutate_original():
    profile = _empty_profile()
    meta = {"source": "user_edit", "timestampIso": "2025-01-01T00:00:00Z"}
    apply_profile_patch(profile, {"assessmentYear": 2024}, meta)
    assert profile["assessmentYear"] == 2025  # original unchanged


def test_apply_patch_updates_timestamp():
    profile = _empty_profile()
    meta = {"source": "chat", "timestampIso": "2025-01-01T00:00:00Z"}
    result = apply_profile_patch(profile, {}, meta)
    assert result["updatedAt"] != "2025-01-01T00:00:00Z"  # changed


def test_apply_patch_deep_merges_income_types():
    profile = _empty_profile()
    profile["incomeTypes"]["employment"] = True
    meta = {"source": "chat", "timestampIso": "2025-01-01T00:00:00Z"}
    result = apply_profile_patch(profile, {"incomeTypes": {"contractor": True}}, meta)
    assert result["incomeTypes"]["employment"] is True  # preserved
    assert result["incomeTypes"]["contractor"] is True  # added


# ── intent_classifier ─────────────────────────────────────────────────────────

from lib.deterministic_tools import (
    intent_classifier,
    date_math,
    parse_answer_for_field,
    filing_form_selector,
    consistency_checker,
)


def test_intent_what_if():
    assert intent_classifier("What if I had employment income?")["intent"] == "WHAT_IF"


def test_intent_suppose():
    assert intent_classifier("Suppose I was on a tourist visa")["intent"] == "WHAT_IF"


def test_intent_profile_input_yes():
    assert intent_classifier("Yes, I was working in Malaysia")["intent"] == "PROFILE_INPUT"


def test_intent_profile_input_dates():
    assert intent_classifier("I was there from 2025-01-15 to 2025-03-20")["intent"] == "PROFILE_INPUT"


def test_intent_info():
    assert intent_classifier("How does the 183-day rule work?")["intent"] == "INFO"


# ── date_math ─────────────────────────────────────────────────────────────────

def test_date_math_iso_pair():
    result = date_math("2024-11-01 to 2024-12-31", "2025-01-01")
    assert result["entryDate"] == "2024-11-01"
    assert result["exitDate"] == "2024-12-31"
    assert result["dateConfidence"] == "exact"


def test_date_math_since_month_year():
    result = date_math("since November 2024", "2025-01-01")
    assert result["entryDate"] == "2024-11-01"
    assert result["exitDate"] == "2025-01-01"


def test_date_math_from_to_months():
    result = date_math("from January 2025 to March 2025", "2025-04-01")
    assert result["entryDate"] == "2025-01-01"
    assert result.get("exitDate") is not None


def test_date_math_ambiguous_returns_warning():
    result = date_math("I was there for a while", "2025-01-01")
    assert len(result.get("warnings", [])) > 0


def test_date_math_clip_year_days():
    result = date_math("2025-01-01 to 2025-06-30", "2025-07-01", clip_year=2025)
    assert result.get("daysInClipYear") == 181


# ── parse_answer_for_field ────────────────────────────────────────────────────

def test_parse_skip_phrase():
    result = parse_answer_for_field("incomeTypes", "prefer not to answer", "2025-01-01")
    assert result.get("skip") is True
    assert result["confidenceTier"] == "high"


def test_parse_yes_no_field():
    result = parse_answer_for_field("employment.foreignEmployer", "Yes, my employer is foreign", "2025-01-01")
    assert result["patch"]["employment"]["foreignEmployer"] == "yes"
    assert result["confidenceTier"] == "high"


def test_parse_boolean_field_false():
    result = parse_answer_for_field("advisorContext.filesTaxElsewhere", "No I don't file anywhere else", "2025-01-01")
    assert result["patch"]["advisorContext"]["filesTaxElsewhere"] is False
    assert result["confidenceTier"] == "high"


def test_parse_income_types():
    result = parse_answer_for_field("incomeTypes", "I have employment and some crypto", "2025-01-01")
    assert result["patch"]["incomeTypes"].get("employment") is True
    assert result["patch"]["incomeTypes"].get("crypto") is True


def test_parse_visa_type_de_rantau():
    result = parse_answer_for_field("advisorContext.visaType", "I'm on a DE Rantau visa", "2025-01-01")
    assert result["patch"]["advisorContext"]["visaType"] == "de_rantau"


def test_parse_trips_iso_dates():
    result = parse_answer_for_field("presence.trips", "I was there from 2025-01-15 to 2025-03-20", "2025-04-01")
    trips = result["patch"]["presence"]["trips"]
    assert trips[0]["entryDate"] == "2025-01-15"
    assert trips[0]["exitDate"] == "2025-03-20"
    assert result["confidenceTier"] == "high"


def test_parse_unclear_returns_low_confidence():
    result = parse_answer_for_field("employment.foreignEmployer", "Hmm I'm really not sure about that", "2025-01-01")
    assert result["confidenceTier"] == "low"
    assert "needsClarification" in result


def test_parse_not_director_returns_false():
    """'I am not a director' must NOT return True for isCompanyDirector."""
    result = parse_answer_for_field("advisorContext.isCompanyDirector", "I am not a director", "2025-01-01")
    assert result["patch"].get("advisorContext", {}).get("isCompanyDirector") is not True


def test_parse_employment_pass_not_skipped():
    """'employment pass' must reach visaType parser, not skip handler."""
    result = parse_answer_for_field("advisorContext.visaType", "I'm on an employment pass", "2025-01-01")
    assert result.get("skip") is not True
    assert result["patch"].get("advisorContext", {}).get("visaType") == "employment_pass"


def test_parse_passport_mention_not_skipped():
    """'passports' in message must not trigger skip."""
    result = parse_answer_for_field("advisorContext.citizenships", "I hold US and GB passports", "2025-01-01")
    assert result.get("skip") is not True


def test_parse_other_tax_country_valid():
    result = parse_answer_for_field("advisorContext.otherTaxCountry", "United Kingdom", "2025-01-01")
    assert result["patch"]["advisorContext"]["otherTaxCountry"] == "United Kingdom"
    assert result["confidenceTier"] == "medium"


def test_parse_other_tax_country_too_short():
    result = parse_answer_for_field("advisorContext.otherTaxCountry", "X", "2025-01-01")
    assert result["confidenceTier"] == "low"
    assert "needsClarification" in result


def test_parse_not_director_returns_explicitly_false():
    result = parse_answer_for_field("advisorContext.isCompanyDirector", "I am not a director", "2025-01-01")
    assert result["patch"]["advisorContext"]["isCompanyDirector"] is False


def test_parse_private_equity_not_skipped():
    """'private' as substring should not trigger skip."""
    result = parse_answer_for_field("passive.types", "I have private equity income", "2025-01-01")
    assert result.get("skip") is not True


# ── presence_calculator rolling12Months ───────────────────────────────────────

def test_rolling12_same_as_year_when_all_trips_in_year():
    """Trip entirely within assessment year → rolling12Months == daysInYear."""
    trips = [{"tripId": "1", "country": "MY", "entryDate": "2024-01-01", "exitDate": "2024-06-30"}]
    result = presence_calculator(trips, 2024)
    assert result["rolling12Months"] == result["daysInYear"]


def test_rolling12_higher_than_year_when_spans_years():
    """Trip from 2024-07-01 to 2025-03-31 spans two years.
    daysInYear(2024) = 184 (Jul–Dec), but rolling window starting Jul 1 captures all 274 days.
    """
    trips = [{"tripId": "1", "country": "MY", "entryDate": "2024-07-01", "exitDate": "2025-03-31"}]
    result = presence_calculator(trips, 2024)
    assert result["daysInYear"] == 184
    assert result["rolling12Months"] == 274


# ── filing_form_selector ──────────────────────────────────────────────────────

def test_form_M_non_resident():
    """90 days → non-resident → Form M."""
    profile = _empty_profile()
    profile["presence"]["trips"] = [
        {"tripId": "1", "country": "MY", "entryDate": "2025-01-01", "exitDate": "2025-04-01"}
    ]
    result = filing_form_selector(profile, 90)
    assert result["form"] == "M"
    assert result["decidable"] is True


def test_form_BE_employment_only():
    """200 days, employment income only → Form BE."""
    profile = _empty_profile()
    profile["incomeTypes"]["employment"] = True
    profile["presence"]["trips"] = [
        {"tripId": "1", "country": "MY", "entryDate": "2025-01-01", "exitDate": "2025-07-20"}
    ]
    result = filing_form_selector(profile, 200)
    assert result["form"] == "BE"
    assert result["decidable"] is True


def test_form_B_contractor():
    """200 days, contractor income → Form B."""
    profile = _empty_profile()
    profile["incomeTypes"]["contractor"] = True
    profile["presence"]["trips"] = [
        {"tripId": "1", "country": "MY", "entryDate": "2025-01-01", "exitDate": "2025-07-20"}
    ]
    result = filing_form_selector(profile, 200)
    assert result["form"] == "B"
    assert result["decidable"] is True


def test_form_B_director():
    """200 days, company director → Form B."""
    profile = _empty_profile()
    profile["advisorContext"]["isCompanyDirector"] = True
    profile["presence"]["trips"] = [
        {"tripId": "1", "country": "MY", "entryDate": "2025-01-01", "exitDate": "2025-07-20"}
    ]
    result = filing_form_selector(profile, 200)
    assert result["form"] == "B"
    assert result["decidable"] is True


def test_form_none_no_trips():
    """Empty profile with no trips → decidable=False."""
    profile = _empty_profile()
    result = filing_form_selector(profile, 0)
    assert result["form"] is None
    assert result["decidable"] is False


# ── consistency_checker ───────────────────────────────────────────────────────

def test_no_issues_clean_profile():
    result = consistency_checker(_empty_profile())
    assert result["contradictions"] == []
    assert result["risk_flags"] == []


def test_warns_worked_but_no_income_type():
    profile = _empty_profile()
    profile["employment"] = {"workedWhileInJurisdiction": "yes"}
    result = consistency_checker(profile)
    codes = [f["code"] for f in result["risk_flags"]]
    assert "WORKED_BUT_NO_INCOME_TYPE" in codes


def test_warns_salary_borne_local_foreign_employer():
    profile = _empty_profile()
    profile["employment"] = {"foreignEmployer": "yes", "salaryBorneByLocalEntity": "yes"}
    result = consistency_checker(profile)
    codes = [f["code"] for f in result["risk_flags"]]
    assert "SALARY_BORNE_LOCAL_FOREIGN_EMPLOYER" in codes


def test_tourist_visa_long_stay():
    profile = _empty_profile()
    profile["advisorContext"]["visaType"] = "tourist"
    result = consistency_checker(profile, days_in_year=90)
    codes = [f["code"] for f in result["risk_flags"]]
    assert "TOURIST_VISA_LONG_STAY" in codes


def test_director_no_employment():
    profile = _empty_profile()
    profile["advisorContext"]["isCompanyDirector"] = True
    result = consistency_checker(profile)
    codes = [f["code"] for f in result["risk_flags"]]
    assert "DIRECTOR_NO_EMPLOYMENT" in codes


def test_no_trips_but_income():
    profile = _empty_profile()
    profile["incomeTypes"]["employment"] = True
    result = consistency_checker(profile)
    codes = [f["code"] for f in result["risk_flags"]]
    assert "NO_TRIPS_BUT_INCOME_DECLARED" in codes


# ── topic_classifier ──────────────────────────────────────────────────────────

from lib.deterministic_tools import topic_classifier, freshness_requested


def test_topic_dta_country_list():
    assert topic_classifier("Which countries have a DTA with Malaysia?")["topic"] == "DTA_COUNTRY_LIST"

def test_topic_dta_list_keyword():
    assert topic_classifier("Show me the DTA list")["topic"] == "DTA_COUNTRY_LIST"

def test_topic_double_tax_agreement():
    assert topic_classifier("Is there a double tax agreement with Germany?")["topic"] == "DTA_COUNTRY_LIST"

def test_topic_public_ruling_update():
    assert topic_classifier("Has the public ruling on FSI been amended?")["topic"] == "PUBLIC_RULING_UPDATE"

def test_topic_pr_keyword():
    assert topic_classifier("What's the latest PR on employment income?")["topic"] == "PUBLIC_RULING_UPDATE"

def test_topic_guideline_keyword():
    assert topic_classifier("Are there updated guidelines for contractors?")["topic"] == "PUBLIC_RULING_UPDATE"

def test_topic_filing_deadline():
    assert topic_classifier("What is the deadline for Form BE?")["topic"] == "FILING_DEADLINE_CHANGE"

def test_topic_due_date():
    assert topic_classifier("When is the due date for filing?")["topic"] == "FILING_DEADLINE_CHANGE"

def test_topic_other():
    assert topic_classifier("How does the 183-day rule work?")["topic"] == "OTHER"

def test_topic_case_insensitive():
    assert topic_classifier("what is the dta list?")["topic"] == "DTA_COUNTRY_LIST"


# ── freshness_requested ────────────────────────────────────────────────────────

def test_freshness_has_this_changed():
    assert freshness_requested("Has this changed in 2026?") is True

def test_freshness_latest_pr():
    assert freshness_requested("What's the latest PR?") is True

def test_freshness_still_valid():
    assert freshness_requested("Is this still valid in 2026?") is True

def test_freshness_updated():
    assert freshness_requested("Has it been updated?") is True

def test_freshness_most_recent():
    assert freshness_requested("What is the most recent ruling?") is True

def test_freshness_current():
    assert freshness_requested("Is that the current rule?") is True

def test_freshness_not_triggered():
    assert freshness_requested("How does the 183-day rule work?") is False

def test_freshness_case_insensitive():
    assert freshness_requested("LATEST ruling on DTA?") is True


# ── expand_query_terms ────────────────────────────────────────────────────────

from lib.deterministic_tools import expand_query_terms


def test_expand_query_terms_exact_match():
    result = expand_query_terms("Does the 183 day rule apply to me?")
    assert "physical presence test" in result
    assert "s7(1)(a)" in result
    # original phrasing preserved
    assert "183 day rule" in result


def test_expand_query_terms_case_insensitive():
    result = expand_query_terms("What about the 183 DAY RULE?")
    assert "s7(1)(a)" in result


def test_expand_query_terms_multiple_matches_deduplicated():
    # "remote work" and "work from home" both expand to the same legal text
    result = expand_query_terms("I do remote work and work from home in Malaysia")
    # s4(b) should appear only once despite two informal matches
    assert result.count("s4(b)") == 1


def test_expand_query_terms_no_match_returns_original():
    q = "Hello, how are you?"
    assert expand_query_terms(q) == q


def test_expand_query_terms_no_duplicate_if_already_present():
    # If the legal term is already in the query, don't append it again
    q = "Tell me about s7(1)(a) residence status"
    result = expand_query_terms(q)
    assert result.count("s7(1)(a)") == 1
