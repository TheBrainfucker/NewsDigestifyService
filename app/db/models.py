from sqlalchemy import Column, String, DateTime, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.db.base import Base

class DigestRequest(Base):
    __tablename__ = "digestify"

    id = Column(String, primary_key=True)
    topics = Column(JSONB, nullable=False)
    status = Column(String(20), default="pending")
    result = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    error_message = Column(Text, nullable=True)
