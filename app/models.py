import re
from typing import Literal
from pydantic import BaseModel, Field, field_validator, model_validator
from .aliases import canonical


def normalize_course(value):
    code = re.sub(r"[\s-]", "", value).upper()
    if code.startswith("CS") and not code.startswith("CSCI"):
        code = "CSCI"+code[2:]
    if code.isdigit() or re.fullmatch(r"\d{3}[A-Z]{0,2}", code):
        code = "CSCI"+code
    if not re.fullmatch(r"[A-Z]{2,5}\d{3}[A-Z]{0,2}", code):
        raise ValueError("Use a course code such as CSCI 570")
    return canonical(code)


class Credentials(BaseModel):
    email: str = Field(min_length=6, max_length=254)
    password: str = Field(min_length=12, max_length=128)

    @field_validator("email")
    @classmethod
    def usc_email(cls, value):
        value = value.strip().lower()
        if not re.fullmatch(r"[^\s@]+@usc\.edu", value):
            raise ValueError("Use your @usc.edu email; verification is deferred in this demo")
        return value


class Registration(Credentials):
    name: str = Field(min_length=2, max_length=80)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value):
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Enter your name")
        return value


class CourseInput(BaseModel):
    code: str = Field(max_length=20)
    status: Literal["completed", "current"]
    term: str = Field(min_length=4, max_length=30, pattern=r"^(Spring|Summer|Fall) 20\d{2}$")
    instructor: str = Field(min_length=2, max_length=100)

    @field_validator("instructor")
    @classmethod
    def instructor_required(cls, value):
        value = value.strip()
        if len(value) < 2:
            raise ValueError("An instructor name is required")
        return value

    @field_validator("code")
    @classmethod
    def code_format(cls, value):
        return normalize_course(value)


class ProfileInput(BaseModel):
    program_id: str
    start_date: str = Field(pattern=r"^20\d{2}-(0[1-9]|1[0-2])$")
    graduation_date: str = Field(pattern=r"^20\d{2}-(0[1-9]|1[0-2])$")
    courses: list[CourseInput] = Field(default_factory=list, max_length=50)

    @model_validator(mode="after")
    def validate_history(self):
        if self.graduation_date <= self.start_date:
            raise ValueError("Graduation must follow your start date")
        codes = [c.code for c in self.courses]
        if len(codes) != len(set(codes)):
            raise ValueError("List each course once; repeated-course credit needs manual review")
        return self


class Question(BaseModel):
    question: str = Field(min_length=5, max_length=2000)
    courses: list[str] = Field(default_factory=list, max_length=5)
    term: str = Field(default="", max_length=30)
    instructor: str = Field(default="", max_length=100)
    section: Literal["requirements", "workload", "preparation", "learning", "combinations"] = "requirements"
    summarize: bool = False
    history: list[dict[str, str]] = Field(default_factory=list, max_length=6)

    @field_validator("history")
    @classmethod
    def bounded_history(cls, value):
        for item in value:
            if set(item) != {"role", "content"} or item["role"] not in ("user", "assistant") or len(item["content"]) > 6000:
                raise ValueError("Invalid conversation history")
        return value

    @field_validator("courses")
    @classmethod
    def format_courses(cls, value):
        return list(dict.fromkeys(normalize_course(x) for x in value))


class ReviewInput(BaseModel):
    course_code: str = Field(max_length=20)
    answers: list = Field(min_length=6, max_length=6)
    previous_id: int | None = None
    consent: bool = False

    @field_validator("course_code")
    @classmethod
    def code_format(cls, value):
        return normalize_course(value)


class DraftInput(BaseModel):
    course_code: str = Field(max_length=20)
    answers: dict[str, object] = Field(default_factory=dict)
    position: int = Field(ge=0, le=6)
    previous_id: int | None = None

    @field_validator("course_code")
    @classmethod
    def code_format(cls, value):
        return normalize_course(value)
