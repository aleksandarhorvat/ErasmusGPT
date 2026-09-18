from __future__ import annotations

from pydantic import BaseModel, Field


class ProgrammeSummary(BaseModel):
    programme_id: str
    institution_name: str
    programme_name: str
    country: str
    level: str
    course_count: int
    total_ects: float | None = None


class CourseSummary(BaseModel):
    course_uid: str
    code: str
    title: str
    ects: float
    year: int | None = None
    semester: int | None = None
    mandatory: bool = False
    module: str | None = None
    url: str | None = None
    description: str = Field(default="", repr=False)
