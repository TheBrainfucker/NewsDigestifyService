import json
from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.base import get_session
from app.db.models import DigestRequest
from app.db.schemas import DigestRequestSchema, DigestStatusSchema, DigestResultSchema, ErrorResponseSchema
from app.services.digestify_service import generate_digest, test_celery, simple_test
from uuid import UUID, uuid4
from sqlalchemy import select

router = APIRouter(prefix="/digestify", tags=["Digestify"])

@router.post(
    "/", 
    response_model=DigestStatusSchema,
    responses={
        400: {"model": ErrorResponseSchema, "description": "Invalid request data"}
    },
    summary="Create a new digest request",
    description="Submit topics to generate a news digest. The request will be queued for background processing."
)
async def create_digest(req: DigestRequestSchema, session: AsyncSession = Depends(get_session)):
    try:
        digest_id = str(uuid4())
        digest = DigestRequest(id=digest_id, topics=req.topics)
        session.add(digest)
        await session.commit()
        await session.refresh(digest)

        # Test Celery first
        test_task = test_celery.delay()
        print(f"Test Celery task: {test_task.id}")
        
        # Test simple task
        simple_task = simple_test.delay()
        print(f"Simple test task: {simple_task.id}")
        
        # Queue the background task
        task = generate_digest.delay(digest.id, req.topics)
        print(f"Queued Celery task {task.id} for digest {digest.id}")
        
        return DigestStatusSchema(id=digest.id, status=digest.status, created_at=digest.created_at)
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create digest request: {str(e)}")

@router.get(
    "/{digest_id}", 
    response_model=DigestStatusSchema,
    responses={
        404: {"model": ErrorResponseSchema, "description": "Digest not found"}
    },
    summary="Get digest status",
    description="Check the current status of a digest request by its ID."
)
async def get_status(
    digest_id: str = Path(..., description="The unique identifier of the digest request"),
    session: AsyncSession = Depends(get_session)
):
    try:
        UUID(digest_id)
        digest = await session.get(DigestRequest, digest_id)
        if not digest:
            raise HTTPException(status_code=404, detail=f"Digest with ID '{digest_id}' not found")
        
        return DigestStatusSchema(
            id=digest.id,
            status=digest.status,
            created_at=digest.created_at,
            updated_at=digest.updated_at,
            error=digest.error_message
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get(
    "/{digest_id}/result", 
    response_model=DigestResultSchema,
    responses={
        404: {"model": ErrorResponseSchema, "description": "Digest not found"},
        400: {"model": ErrorResponseSchema, "description": "Digest not ready or failed"},
        500: {"model": ErrorResponseSchema, "description": "Digest result is corrupted"}
    },
    summary="Get digest result",
    description="Retrieve the completed digest result. Only available when status is 'completed'."
)
async def get_result(
    digest_id: str = Path(..., description="The unique identifier of the digest request"),
    session: AsyncSession = Depends(get_session)
):
    try:
        UUID(digest_id)
        digest = await session.get(DigestRequest, digest_id)
        if not digest:
            raise HTTPException(status_code=404, detail=f"Digest with ID '{digest_id}' not found")
        
        result = None
        if digest.result:
            try:
                result = json.loads(digest.result)
            except json.JSONDecodeError:
                raise HTTPException(status_code=500, detail="Digest result is corrupted")
        
        return DigestResultSchema(
            id=digest.id,
            status=digest.status,
            result=result,
            error=digest.error_message
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
