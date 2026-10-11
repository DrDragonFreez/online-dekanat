from enum import nonmember
from typing import Literal, Optional

import option
from pydantic import BaseModel, field
doctype=literal[
    "study_certificate",
    "academic_leave_application",
    "internship_certificate",
]
class ValidationOut(BaseModel):
    status: Literal["document_ok","missing_fields"]
    missing_fields: list[str]
    sources: list[str]
class AnswerOut(BaseModel):
    question_id: option[str]= None
    question: Optional[str]= None
    answerable: bool
    value: Optional[str]= None
    answer: str
    sourcces: list[str]
class askrequest(BaseModel):
    question:str=field(...,min_length=1,max_length=1000)
    doc_type:Optional[DocType]= None
class Askrespone(BaseModel):
    doc_type:doctype
    fields: dict
    validation: ValidationOut
    answer: AnswerOut
class batchRequest(BaseModel):
    manifest_path:str
    questions_path:str
    out_path:str="results/results.json"
class batchResponse(BaseModel):
    documents:int
    questions:int
    out_path:str