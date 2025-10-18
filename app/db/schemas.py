from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime

class DigestRequestSchema(BaseModel):
    topics: List[str]

class DigestStatusSchema(BaseModel):
    id: str
    status: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    error: Optional[str] = None

class DigestResultSchema(BaseModel):
    id: str
    status: str
    result: Optional[Dict[str, List[str]]] = None
    error: Optional[str] = None
