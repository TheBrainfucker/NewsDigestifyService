import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.base import get_session
from app.db.models import DigestRequest
from app.db.schemas import DigestRequestSchema, DigestStatusSchema, DigestResultSchema
from app.services.digestify_service import generate_digest
from uuid import uuid4
from sqlalchemy import select

router = APIRouter(prefix="/digestify", tags=["Digestify"])

@router.post("/", response_model=DigestStatusSchema)
async def create_digest(req: DigestRequestSchema, session: AsyncSession = Depends(get_session)):
    digest_id = str(uuid4())
    digest = DigestRequest(id=digest_id, topics=req.topics)
    session.add(digest)
    await session.commit()
    await session.refresh(digest)

    generate_digest.delay(digest.id, req.topics)
    return DigestStatusSchema(id=digest.id, status=digest.status, created_at=digest.created_at)

@router.get("/{digest_id}", response_model=DigestStatusSchema)
async def get_status(digest_id: str, session: AsyncSession = Depends(get_session)):
    digest = await session.get(DigestRequest, digest_id)
    if not digest:
        raise HTTPException(status_code=404, detail="Digest not found")
    return DigestStatusSchema(
        id=digest.id,
        status=digest.status,
        created_at=digest.created_at,
        updated_at=digest.updated_at,
        error=digest.error_message
    )

@router.get("/{digest_id}/result", response_model=DigestResultSchema)
async def get_result(digest_id: str, session: AsyncSession = Depends(get_session)):
    digest = await session.get(DigestRequest, digest_id)
    if not digest:
        raise HTTPException(status_code=404, detail="Digest not found")
    result = json.loads(digest.result) if digest.result else None
    return DigestResultSchema(
        id=digest.id,
        status=digest.status,
        result=result,
        error=digest.error_message
    )
