from sqlalchemy import Column, String, DateTime, Text, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.db.base import Base

class DigestRequest(Base):
    __tablename__ = "digest_requests"

    id = Column(String(36), primary_key=True, comment="UUID of the digest request")
    topics = Column(JSONB, nullable=False, comment="List of topics for the digest")
    status = Column(
        String(20), 
        nullable=False, 
        default="pending",
        comment="Current status: pending, processing, completed, failed"
    )
    result = Column(Text, nullable=True, comment="JSON string containing the digest results")
    created_at = Column(
        DateTime(timezone=True), 
        nullable=False,
        server_default=func.now(),
        comment="When the request was created"
    )
    updated_at = Column(
        DateTime(timezone=True), 
        nullable=True,
        onupdate=func.now(),
        comment="When the request was last updated"
    )
    error_message = Column(Text, nullable=True, comment="Error message if the request failed")

    __table_args__ = (
        Index('idx_digest_status', 'status'),
        Index('idx_digest_created_at', 'created_at'),
        Index('idx_digest_status_created', 'status', 'created_at'),
    )
