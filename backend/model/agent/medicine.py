"""
Pydantic models for medicine data and queries.
"""
from pydantic import BaseModel, Field

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class MedicineBase(BaseModel):
	"""Base model for medicine information"""
	id: int
	name: str
	url: Optional[str] = None
	form: Optional[str] = None
	drug_group: Optional[str] = None
	tag: Optional[str] = None


class MedicineDetailed(MedicineBase):
	"""Detailed medicine information with all fields"""
	indications: Optional[str] = None
	contraindications: Optional[str] = None
	precautions: Optional[str] = None
	side_effects: Optional[str] = None
	dosage: Optional[str] = None
	notes: Optional[str] = None
	search_text: Optional[str] = None
	similarity_score: Optional[float] = None


class DosageInfo(BaseModel):
	"""Dosage information for a medicine"""
	medicine_id: int
	medicine_name: str
	form: Optional[str] = None
	dosage: Optional[str] = None
	url: Optional[str] = None


class MedicineIndicationResult(BaseModel):
	"""Medicine found for a specific indication"""
	medicine_id: int
	medicine_name: str
	form: Optional[str] = None
	drug_group: Optional[str] = None
	indications: Optional[str] = None
	url: Optional[str] = None
	relevance_score: Optional[float] = None


class DrugSearchInput(BaseModel):
	"""Input schema for get_drug_info tool"""
	name: str = Field(..., min_length=1, description="Tên thuốc cần tìm")
	top_k: int = Field(default=5, ge=1, le=20, description="Số kết quả trả về")


class DosageSearchInput(BaseModel):
	"""Input schema for get_dosage tool"""
	medicine_name: str = Field(..., min_length=1, description="Tên thuốc cần tìm liều lượng")


class IndicationSearchInput(BaseModel):
	"""Input schema for get_drugs_by_indication tool"""
	indication: str = Field(..., min_length=1, description="Chỉ định bệnh cần tìm thuốc")
	top_k: int = Field(default=5, ge=1, le=20, description="Số kết quả trả về")


class ContraindicationInput(BaseModel):
	"""Input schema for get_contraindications tool"""
	medicine_name: str = Field(..., min_length=1, description="Tên thuốc cần tìm chống chỉ định")


class SideEffectsInput(BaseModel):
	"""Input schema for get_side_effects tool"""
	medicine_name: str = Field(..., min_length=1, description="Tên thuốc cần tìm tác dụng phụ")


class MedicineRetrievalResult(BaseModel):
	"""Result structure for medicine retrieval operations"""
	query: str
	total_hits: int
	medicines: List[MedicineDetailed] = []
	warning: Optional[str] = None


class DosageRetrievalResult(BaseModel):
	"""Result structure for dosage retrieval"""
	query: str
	medicines: List[DosageInfo] = []
	warning: Optional[str] = None


class IndicationRetrievalResult(BaseModel):
	"""Result structure for indication-based medicine retrieval"""
	indication: str
	total_hits: int
	medicines: List[MedicineIndicationResult] = []
	warning: Optional[str] = None


class MedicineQARequest(BaseModel):
	"""Request model for medicine questions"""
	question: str = Field(..., min_length=1, description="Câu hỏi về thuốc")


class MedicineQAResponse(BaseModel):
	"""Response model for medicine QA"""
	answer: str = Field(..., description="Câu trả lời về thuốc")
	sources: List[str] = Field(default_factory=list, description="Danh sách URL nguồn")
