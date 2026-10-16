from typing import Literal, Optional
from pydantic import BaseModel, Field
DocType = str
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
    doc_type: str
    doc_type_auto: bool
    kind: Literal["pdf", "image"]
    text: str
    fields: dict
    validation: ValidationOut
    answer: Optional[AnswerOut] = None
class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)
    doc_type: Optional[str] = None
class AskResponse(BaseModel):
    doc_type: str
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