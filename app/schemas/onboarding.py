"""P-220 — Pydantic schemas for the onboarding questionnaire.

Contract source: docs/P-220-onboarding-questionnaire-copy.md (the
"For BE — implementation pointers" section). Slug values match exactly
so the FE has a stable contract.
"""
from __future__ import annotations

from datetime import date
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


# ── Slug literals (i.e. closed-enum domains) ─────────────────────

CurrentLevelSlug = Literal["a2", "b1", "b2", "c1", "not_sure"]
TargetLevelSlug = Literal["b1", "b2", "c1", "c2", "not_sure"]

MotivationSlug = Literal[
    "immigration", "professional", "studies", "personal", "prefer_not_to_say"
]

# Q5 — raw skill identifiers + opt-out.
StrongestSkillSlug = Literal[
    "speaking", "listening", "reading", "writing", "all_equally_weak"
]
# Q6 — DIFFERENT domain from Q5: blocker types, not raw skills.
WeakestSkillSlug = Literal[
    "speaking_under_pressure",
    "listening_fast",
    "reading_complex",
    "writing_essays",
    "grammar_accuracy",
    "vocabulary_depth",
]

HoursPerWeekSlug = Literal["less_than_2", "2_to_5", "5_to_10", "more_than_10"]

TcfThemeSlug = Literal[
    "vie_quotidienne", "societe", "education", "travail",
    "loisirs_voyages", "sante", "environnement", "culture_medias",
]

NativeLanguageSlug = Literal[
    "english", "arabic", "spanish", "portuguese", "mandarin",
    "hindi", "russian", "german", "italian", "other",
]

PriorExamHistorySlug = Literal["never", "recent_6mo", "recent_12mo", "older"]

FeedbackModeSlug = Literal["calm", "method"]

PersonaSlug = Literal["foundation", "acceleration", "cram"]


# ── GET /onboarding/questions response ──────────────────────────


class I18n(BaseModel):
    """`{en, fr}` localized string pair. FE reads user's ui_language
    preference and renders the matching key."""

    model_config = ConfigDict(extra="forbid")

    en: str
    fr: str


class OnboardingQuestionOption(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: str
    label: I18n


class OnboardingQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    order: int
    type: Literal["single_select", "multi_select", "date_input", "text_input"]
    required: bool
    skip_condition: Optional[dict] = None
    heading: I18n
    helper: I18n
    # None for date_input. Otherwise non-empty.
    options: Optional[List[OnboardingQuestionOption]] = None


class OnboardingQuestionsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    questions: List[OnboardingQuestion]


# ── POST /onboarding/submit request ─────────────────────────────


class OnboardingSubmitRequest(BaseModel):
    """Payload shape per docs/P-220-onboarding-questionnaire-copy.md."""

    model_config = ConfigDict(extra="forbid")

    q1_current_level: CurrentLevelSlug
    q2_target_level: TargetLevelSlug

    # Q3 is XOR: either a date OR no_exam_scheduled=True.
    q3_exam_date: Optional[date] = None
    q3_no_exam_scheduled: bool = False

    q4_motivation: Optional[MotivationSlug] = None
    q5_strongest_skill: Optional[StrongestSkillSlug] = None
    q6_weakest_skill: Optional[WeakestSkillSlug] = None

    q7_hours_per_week: HoursPerWeekSlug
    q8_topics_tested_on: List[TcfThemeSlug] = Field(default_factory=list)

    q9_native_language: NativeLanguageSlug
    q9_native_language_other: Optional[str] = None

    q10_prior_exam_history: PriorExamHistorySlug
    q11_feedback_mode: FeedbackModeSlug

    # FE FR/EN toggle. Maps to User.ui_language column (same convention as
    # the legacy /api/users/onboarding endpoint). Optional so legacy clients
    # that don't send it keep working unchanged; absent value means "leave
    # ui_language as-is".
    interface_language: Optional[Literal["en", "fr"]] = None

    @model_validator(mode="after")
    def _exam_date_xor_no_exam(self) -> "OnboardingSubmitRequest":
        if not self.q3_no_exam_scheduled and self.q3_exam_date is None:
            raise ValueError(
                "Provide q3_exam_date, or set q3_no_exam_scheduled=true"
            )
        if self.q3_no_exam_scheduled and self.q3_exam_date is not None:
            raise ValueError(
                "Cannot set q3_exam_date and q3_no_exam_scheduled=true together"
            )
        return self

    @model_validator(mode="after")
    def _other_language_text_when_other(self) -> "OnboardingSubmitRequest":
        if self.q9_native_language == "other" and not (
            self.q9_native_language_other and self.q9_native_language_other.strip()
        ):
            raise ValueError(
                "q9_native_language_other is required when q9_native_language='other'"
            )
        return self

    @model_validator(mode="after")
    def _topics_skipped_when_no_exam(self) -> "OnboardingSubmitRequest":
        # Per copy doc Q8 skip_condition: if Q3 = no_exam, Q8 should be empty.
        # Don't error — silently empty so the FE skip-condition flow doesn't
        # have to police it. Just normalize.
        if self.q3_no_exam_scheduled and self.q8_topics_tested_on:
            self.q8_topics_tested_on = []
        return self


# ── POST /onboarding/submit response ────────────────────────────


class CapacityWarning(BaseModel):
    model_config = ConfigDict(extra="forbid")

    weeks_to_exam: int
    hours_per_week_selected: HoursPerWeekSlug
    recommended_minimum_hours: HoursPerWeekSlug


class OnboardingSubmitResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path_slug: Optional[str]
    persona: Optional[PersonaSlug]
    redirect_to_diagnostic: bool
    waitlist: bool
    capacity_warning: Optional[CapacityWarning] = None
    user_path_enrollment_id: Optional[int] = None
    waitlist_reason: Optional[str] = None
    fallback_path_offered: Optional[str] = None
