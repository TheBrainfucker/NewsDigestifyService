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

# News article schema
class NewsArticle(BaseModel):
    title: str = Field(..., description="Article headline")
    url: str = Field(..., description="Article URL")
    source: str = Field(..., description="News source (e.g., 'BBC', 'CNN')")
    published_at: Optional[datetime] = Field(None, description="When the article was published")
    summary: Optional[str] = Field(None, description="Brief summary of the article")
    image_url: Optional[str] = Field(None, description="Article thumbnail image URL")

# Topic digest schema
class TopicDigest(BaseModel):
    topic: str = Field(..., description="The news topic")
    articles: List[NewsArticle] = Field(..., description="List of articles for this topic")
    summary: Optional[str] = Field(None, description="AI-generated summary of the topic")
    key_points: List[str] = Field(default_factory=list, description="Key points from the articles")

# Main digest result schema
class DigestResult(BaseModel):
    topics: List[TopicDigest] = Field(..., description="Digest organized by topics")
    generated_at: datetime = Field(default_factory=datetime.utcnow, description="When the digest was generated")
    total_articles: int = Field(..., description="Total number of articles in the digest")
    sources: List[str] = Field(..., description="List of unique news sources used")

class DigestResultSchema(DigestBaseSchema):
    result: Optional[DigestResult] = Field(
        None, 
        description="The complete news digest with articles and summaries"
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
