"""F-080a — pydantic schemas for the remediation module library.

Shapes match the authored JSON seed files under seeds/modules/*.json.
The seed loader validates each file against ``RemediationModule`` before
upserting into the DB; the CRUD router (app/routers/modules.py) returns
the same shape after hydrating JSON-blob columns.

Category + severity enums mirror the migration DDL's CHECK constraints
— if you add a category here, add it there too (and vice versa).

All multi-language fields ship FR + EN today. ES is deferred to V2 of
the authoring pipeline; the frontend (F-080c) falls back to EN for ES
users rather than forcing a translation round on every module.
"""
from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


ModuleCategory = Literal[
    "vocab_calque",
    "grammar_interference",
    "discourse_structure",
    "pronunciation",
    "register_mismatch",
    "word_order",
    "verb_aspect",
    "other",
]


ContentRefType = Literal[
    "inline_markdown",
    "document",
    "audio",
    "external_link",
]


class ContentRef(BaseModel):
    """One piece of learning content attached to a module.

    Fields are conditional on ``type``:
      - inline_markdown → content_fr / content_en populated
      - document         → locator + description populated
      - audio            → url + duration_seconds (+ optional description)
      - external_link    → url + description

    Validation is intentionally loose at this layer (V1 has only
    inline_markdown content; stricter conditional validation lands when
    the authoring pipeline supports the other types).
    """

    model_config = ConfigDict(extra="forbid")

    type: ContentRefType
    display_order: int = Field(ge=0)
    content_fr: Optional[str] = None
    content_en: Optional[str] = None
    locator: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    duration_seconds: Optional[int] = Field(default=None, ge=0)


class ExampleEntry(BaseModel):
    """A wrong/right pair with bilingual rationale, rendered on the
    diagnostic page's "See examples" expand (F-080c).
    """

    model_config = ConfigDict(extra="forbid")

    context: str
    wrong_utterance: str
    corrected_utterance: str
    explanation_fr: str
    explanation_en: str


class DetectionCriteria(BaseModel):
    """Prompt-facing detection signals. Serialized compactly into the
    Claude analysis prompt (F-080b) so the model can match candidate
    transcripts against the module library without pulling the full
    authored descriptions into the context window.
    """

    model_config = ConfigDict(extra="forbid")

    keywords_wrong: List[str]
    grammatical_signals: List[str]
    contextual_triggers: List[str]


class RemediationModule(BaseModel):
    """Authored module shape. Matches seeds/modules/<id>.json exactly."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=64)
    name_fr: str = Field(max_length=200)
    name_en: str = Field(max_length=200)
    category: ModuleCategory
    severity: int = Field(ge=1, le=5)
    active: bool = True

    L1_interference_description_fr: str
    L1_interference_description_en: str

    detection_criteria: DetectionCriteria
    examples: List[ExampleEntry]
    content_refs: List[ContentRef] = Field(default_factory=list)
    drill_ids: List[int] = Field(default_factory=list)
    prerequisite_module_ids: List[str] = Field(default_factory=list)
    ecole_lesson_id: Optional[int] = None

    @field_validator("id")
    @classmethod
    def _id_shape(cls, v: str) -> str:
        # Ids are used in URLs and in the filename of the seed JSON.
        # Lock them to a conservative slug shape so the seeder can
        # confidently match filename ↔ id.
        stripped = v.strip()
        if not stripped:
            raise ValueError("id must not be empty")
        if not all(c.isalnum() or c in ("_", "-") for c in stripped):
            raise ValueError(
                f"id {stripped!r} must be alnum + underscore/hyphen only "
                "(matches the seed filename's stem)"
            )
        return stripped


class DetectedModule(BaseModel):
    """Per-session detection — Claude analysis output line (F-080b).

    Persisted into ``session_detected_modules``; the CRUD-hydrated
    diagnostic response (F-080c) joins the module_id back to
    ``RemediationModule`` for the full shape.
    """

    model_config = ConfigDict(extra="forbid")

    module_id: str
    confidence: float = Field(ge=0.0, le=1.0)
    supporting_quote: Optional[str] = None
    is_primary: bool = False
