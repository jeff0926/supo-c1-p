from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models import JobStatus, VariantStatus


class WordTimestamp(BaseModel):
    word: str
    start: float
    end: float


class Transcript(BaseModel):
    text: str
    words: list[WordTimestamp]


class ClipCandidate(BaseModel):
    title: str
    start_time: float = Field(ge=0)
    end_time: float = Field(gt=0)
    virality_score: int = Field(ge=0, le=100)
    reasoning: str


class CurationResult(BaseModel):
    clips: list[ClipCandidate]


class VideoCreate(BaseModel):
    """Payload accepted when initiating a video upload."""
    use_llm: bool = True


class TemplateInfo(BaseModel):
    id: str
    name: str
    description: str


class VariantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    clip_id: int
    template_id: str
    status: VariantStatus
    output_md5: str | None = None
    output_url: str | None = None
    error_message: str | None = None
    created_at: datetime


class BatchRenderRequest(BaseModel):
    clip_ids: list[int] = Field(min_length=1)
    template_ids: list[str] = Field(min_length=1)


class BatchRenderResponse(BaseModel):
    variant_ids: list[int]


class VideoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    duration_seconds: float | None
    created_at: datetime


class ClipOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    start_time: float
    end_time: float
    virality_score: int
    reasoning: str
    rendered: bool
    output_url: str | None = None
    variants: list[VariantOut] = []


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    video_id: int
    status: JobStatus
    error_message: str | None
    created_at: datetime
    updated_at: datetime
    has_transcript: bool = False
    clips: list[ClipOut] = []
