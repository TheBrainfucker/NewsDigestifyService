from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import List, Dict, Optional, Literal
from datetime import datetime
import re

class DigestRequestSchema(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid"
    )
    
    topics: List[str] = Field(
        ..., 
        min_length=1, 
        max_length=10,
        description="List of news topics to include in the digest"
    )
    
    @field_validator('topics')
    @classmethod
    def validate_topics(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError('At least one topic is required')
        
        # Clean and validate each topic
        cleaned_topics = []
        for topic in v:
            # Remove extra whitespace and validate
            cleaned_topic = topic.strip()
            if not cleaned_topic:
                raise ValueError('Topics cannot be empty or just whitespace')
            if len(cleaned_topic) > 100:
                raise ValueError('Each topic must be 100 characters or less')
            if not re.match(r'^[a-zA-Z0-9\s\-_.,!?]+$', cleaned_topic):
                raise ValueError('Topics can only contain letters, numbers, spaces, and basic punctuation')
            cleaned_topics.append(cleaned_topic)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_topics = []
        for topic in cleaned_topics:
            if topic.lower() not in seen:
                seen.add(topic.lower())
                unique_topics.append(topic)
        
        return unique_topics

# Base schema with common fields
class DigestBaseSchema(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid"
    )
    
    id: str = Field(..., description="Unique identifier for the digest request")
    status: Literal["pending", "processing", "completed", "failed"] = Field(
        ..., 
        description="Current status of the digest generation"
    )
    error: Optional[str] = Field(None, description="Error message if the request failed")

class DigestStatusSchema(DigestBaseSchema):
    created_at: Optional[datetime] = Field(None, description="When the request was created")
    updated_at: Optional[datetime] = Field(None, description="When the status was last updated")

class DigestResultSchema(DigestBaseSchema):
    result: Optional[Dict[str, List[str]]] = Field(
        None, 
        description="The generated digest organized by topic"
    )

# Error response schemas
class ErrorResponseSchema(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid"
    )
    
    detail: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(None, description="Specific error code")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When the error occurred")
