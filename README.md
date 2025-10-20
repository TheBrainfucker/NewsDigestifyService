# News Digestify Service (FastAPI + Celery + Redis + PostgreSQL)

## Redis
### Instatll Redis if not installed
sudo apt install redis-server

### Option A: Start Redis as service
sudo systemctl start redis-server
   
### Option B: Start Redis anually
redis-server

celery -A app.core.celery_app worker --loglevel=info