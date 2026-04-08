from pydantic import BaseModel, Field
from typing import Any, List
class RetrieveDiseaseInput(BaseModel):
	query: str = Field(..., min_length=1, description="Cau hoi benh ly cua nguoi dung")
	top_k: int = Field(default=3, ge=1, le=10, description="So ket qua lay tu FAISS")


class DiseaseArticle(BaseModel):
	disease_id: int
	title: str
	summary: str
	detail_sections: str
	source_url: str
	score: float


class DiseaseRetrievalResult(BaseModel):
	query: str
	total_hits: int
	articles: List[DiseaseArticle]
	warning: str | None = None


class DiseaseQARequest(BaseModel):
    question: str = Field(..., min_length=1)


class DiseaseQAResponse(BaseModel):
    answer: str
    sources: List[str]