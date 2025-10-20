from fastapi import FastAPI
from app.api.digestify_routes import router as digestify_router

app = FastAPI(title="News Digestify Service")
app.include_router(digestify_router)