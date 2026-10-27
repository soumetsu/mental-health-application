from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


SupportState = Literal["support", "gentle", "steady", "calm"]
Valence = Literal["positive", "negative", "neutral"]


class UserResponse(BaseModel):
    id: str
    username: str
    display_name: str
    email: str | None = None
    has_questionnaire: bool = False


class AuthResponse(BaseModel):
    token: str
    user: UserResponse


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32, pattern=r"^[A-Za-z0-9_.-]+$")
    display_name: str = Field(min_length=1, max_length=60)
    email: str | None = Field(default=None, max_length=120)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("username", "display_name", "email", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        return value.lower()

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str | None) -> str | None:
        if not value:
            return None
        value = value.lower()
        if "@" not in value or value.startswith("@") or value.endswith("@"):
            raise ValueError("Enter a valid email address")
        return value


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=32)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        return value.strip().lower()


class QuestionnaireRequest(BaseModel):
    stressors: list[str] = Field(default_factory=list, max_length=6)
    sleep_hours: float = Field(ge=0, le=24)
    support_style: Literal["quiet", "balanced", "encouraging"]

    @field_validator("stressors")
    @classmethod
    def clean_stressors(cls, values: list[str]) -> list[str]:
        clean = []
        for value in values:
            item = value.strip()[:60]
            if item and item not in clean:
                clean.append(item)
        return clean


class QuestionnaireResponse(QuestionnaireRequest):
    updated_at: datetime


class CheckInCreateRequest(BaseModel):
    mood: int = Field(ge=1, le=5)
    energy: int = Field(ge=1, le=5)
    note: str = Field(default="", max_length=600)
    tags: list[str] = Field(default_factory=list, max_length=6)

    @field_validator("note")
    @classmethod
    def clean_note(cls, value: str) -> str:
        return value.strip()

    @field_validator("tags")
    @classmethod
    def clean_tags(cls, values: list[str]) -> list[str]:
        return list(dict.fromkeys(item.strip()[:32] for item in values if item.strip()))


class CheckInResponse(CheckInCreateRequest):
    id: str
    created_at: datetime


class EventCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    details: str = Field(default="", max_length=800)
    valence: Valence
    intensity: int = Field(ge=1, le=5)
    happened_on: date

    @field_validator("title", "details")
    @classmethod
    def clean_text(cls, value: str) -> str:
        return value.strip()


class EventResponse(EventCreateRequest):
    id: str
    created_at: datetime


class DashboardResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str
    support_state: SupportState
    message: str
    affirmation: str
    recommended_exercise_id: str
    today_check_in_complete: bool
    today_event_count: int
    recent_events: list[EventResponse]


class ExerciseResponse(BaseModel):
    id: str
    title: str
    summary: str
    steps: list[str]


class ExerciseHistoryCreateRequest(BaseModel):
    exercise_id: Literal["grounding-54321", "box-breathing"]


class ExerciseHistoryUpdateRequest(BaseModel):
    status: Literal["completed", "stopped"] | None = None
    reflection: str | None = Field(default=None, max_length=400)

    @field_validator("reflection")
    @classmethod
    def clean_reflection(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @model_validator(mode="after")
    def require_change(self) -> "ExerciseHistoryUpdateRequest":
        if self.status is None and self.reflection is None:
            raise ValueError("Provide a status or reflection to update")
        return self


class ExerciseHistoryResponse(BaseModel):
    id: str
    exercise_id: Literal["grounding-54321", "box-breathing"]
    exercise_title: str
    status: Literal["in_progress", "completed", "stopped"]
    reflection: str
    started_at: datetime
    completed_at: datetime | None = None
    updated_at: datetime


class HealthResponse(BaseModel):
    status: Literal["ok"]
    database: Literal["ready"]

