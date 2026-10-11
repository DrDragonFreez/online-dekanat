from typing import Literal, Optional
from pydantic import BaseModel, Field
DocType = Literal[
    "study_certificate",
    "academic_leave_application",
    "internship_certificate",
]
class ValidationOut(BaseModel):
    status: Literal["document_ok", "missing_fields"]
    missing_fields: list[str]
    sources: list[str]
class AnswerOut(BaseModel):
    question_id: Optional[str] = None
    question: Optional[str] = None
    answerable: bool
    value: Optional[str] = None
    answer: str
    sources: list[str]
class AnalyzeResponse(BaseModel):
    document_id: str
    doc_type: DocType
    doc_type_auto: bool
    kind: Literal["pdf", "image"]
    text: str
    fields: dict
    validation: ValidationOut
    answer: Optional[AnswerOut] = None
class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)
    doc_type: Optional[DocType] = None
class AskResponse(BaseModel):
    doc_type: DocType
    fields: dict
    validation: ValidationOut
    answer: AnswerOut
class BatchRequest(BaseModel):
    manifest_path: str
    questions_path: str
    out_path: str = "results/results_closed.json"
class BatchResponse(BaseModel):
    documents: int
    questions: int
    out_path: str