import asyncio
import httpx
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any
from app.core.celery_app import celery_app
from app.core.config import settings
from app.db.base import async_session
from app.db.models import DigestRequest
from app.db.schemas import NewsArticle, TopicDigest, DigestResult
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

@celery_app.task
def test_celery():
    """Test task to verify Celery is working"""
    print("Celery task is working!")
    return "Celery is working!"

@celery_app.task
def simple_test():
    """Simple test task"""
    print("Simple test task is working!")
    return "Simple test task completed!"

@celery_app.task
def generate_digest(digest_id: str, topics: list[str]):
    """Generate news digest for given topics using NewsAPI"""
    print(f"MAIN TASK: Starting digest generation for {digest_id} with topics: {topics}")
    try:
        # Update status to processing
        _update_digest_status_sync(digest_id, "processing")
        
        # Run the async digest generation
        result = asyncio.run(_generate_digest_async_simple(digest_id, topics))
        print(f"MAIN TASK: Digest generation completed for {digest_id}")
        return result
    except Exception as e:
        print(f"MAIN TASK: Error in digest generation for {digest_id}: {str(e)}")
        _update_digest_error_sync(digest_id, str(e))
        import traceback
        traceback.print_exc()
        return {"status": "failed", "error": str(e)}

async def _generate_digest_async_simple(digest_id: str, topics: list[str]):
    """Async function to generate digest without database operations"""
    print(f"Starting digest generation for {digest_id} with topics: {topics}")
    try:
        # Fetch news for each topic
        topic_digests = []
        all_sources = set()
        total_articles = 0
        
        for topic in topics:
            articles = await _fetch_news_for_topic(topic)
            if articles:
                # Extract sources
                for article in articles:
                    source_name = article.get('source', 'Unknown')
                    if isinstance(source_name, dict):
                        source_name = source_name.get('name', 'Unknown')
                    all_sources.add(source_name)
                
                # Create topic digest
                topic_digest = TopicDigest(
                    topic=topic,
                    articles=[NewsArticle(**article) for article in articles],
                    summary=await _generate_topic_summary(articles),
                    key_points=await _extract_key_points(articles)
                )
                topic_digests.append(topic_digest)
                total_articles += len(articles)
        
        # Create final result
        result = DigestResult(
            topics=topic_digests,
            generated_at=datetime.utcnow(),
            total_articles=total_articles,
            sources=list(all_sources)
        )
        
        # Convert to dict and handle datetime serialization
        result_dict = result.model_dump()
        # Convert datetime to string for JSON serialization
        if 'generated_at' in result_dict:
            result_dict['generated_at'] = result_dict['generated_at'].isoformat()
        
        # Also handle datetime in topics/articles
        for topic in result_dict.get('topics', []):
            for article in topic.get('articles', []):
                if 'published_at' in article and article['published_at']:
                    article['published_at'] = article['published_at'].isoformat()
        
        # Update database with result using sync operation
        _update_digest_result_sync(digest_id, result_dict)
        
        return {"status": "completed", "digest_id": digest_id}
        
    except Exception as e:
        # Update status to failed using sync operation
        _update_digest_error_sync(digest_id, str(e))
        return {"status": "failed", "error": str(e)}

async def _fetch_news_for_topic(topic: str) -> List[Dict[str, Any]]:
    """Fetch news articles for a specific topic using NewsAPI"""
    if not settings.news_api_key:
        raise ValueError("NewsAPI key not configured")
    
    async with httpx.AsyncClient() as client:
        # Get articles from the last 7 days
        from_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        
        url = "https://newsapi.org/v2/everything"
        params = {
            "q": topic,
            "from": from_date,
            "sortBy": "publishedAt",
            "language": "en",
            "pageSize": 10,
            "apiKey": settings.news_api_key
        }
        
        response = await client.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        articles = data.get('articles', [])
        
        # Transform articles to our format
        transformed_articles = []
        for article in articles:
            # Handle published_at datetime conversion
            published_at = article.get('publishedAt')
            if published_at:
                try:
                    # Parse the ISO datetime string
                    published_at = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                except:
                    published_at = None
            
            transformed_articles.append({
                "title": article.get('title', ''),
                "url": article.get('url', ''),
                "source": article.get('source', {}).get('name', 'Unknown'),
                "published_at": published_at,
                "summary": article.get('description', ''),
                "image_url": article.get('urlToImage')
            })
        
        return transformed_articles

async def _generate_topic_summary(articles: List[Dict[str, Any]]) -> str:
    """Generate topic summary using NewsAPI descriptions"""
    if not articles:
        return "No recent articles found for this topic."
    
    # Collect descriptions from articles
    descriptions = []
    for article in articles[:3]:  # Use first 3 articles
        description = article.get('summary', '')
        if description and len(description.strip()) > 20:
            descriptions.append(description.strip())
    
    if descriptions:
        # Use the first good description as the topic summary
        return f"Recent developments: {descriptions[0]}"
    else:
        return f"Found {len(articles)} recent articles covering this topic."

async def _extract_key_points(articles: List[Dict[str, Any]]) -> List[str]:
    """Extract key points from article titles"""
    if not articles:
        return []
    
    # Extract key points from article titles (first 3 articles)
    key_points = []
    for article in articles[:3]:
        title = article.get('title', '')
        if title:
            # Clean up title and make it a key point
            clean_title = title.replace(' - ', ': ').split(':')[0]
            key_points.append(clean_title)
    
    return key_points

def _update_digest_status_sync(digest_id: str, status: str):
    """Update digest status in database using sync connection"""
    print(f"Updating digest {digest_id} status to: {status}")
    try:
        # Create sync database connection for Celery tasks
        sync_database_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
        engine = create_engine(sync_database_url)
        Session = sessionmaker(bind=engine)
        
        with Session() as session:
            digest = session.get(DigestRequest, digest_id)
            if digest:
                digest.status = status
                digest.updated_at = datetime.utcnow()
                session.commit()
                print(f"Updated digest {digest_id} status to: {status}")
            else:
                print(f"Digest {digest_id} not found in database")
    except Exception as e:
        print(f"Error updating digest status: {e}")

def _update_digest_result_sync(digest_id: str, result: Dict[str, Any]):
    """Update digest with final result using sync connection"""
    print(f"Saving result for digest {digest_id}")
    try:
        # Create sync database connection for Celery tasks
        sync_database_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
        engine = create_engine(sync_database_url)
        Session = sessionmaker(bind=engine)
        
        with Session() as session:
            digest = session.get(DigestRequest, digest_id)
            if digest:
                digest.status = "completed"
                digest.result = json.dumps(result)
                digest.updated_at = datetime.utcnow()
                session.commit()
                print(f"Saved result for digest {digest_id}")
            else:
                print(f"Digest {digest_id} not found when saving result")
    except Exception as e:
        print(f"Error saving digest result: {e}")

def _update_digest_error_sync(digest_id: str, error_message: str):
    """Update digest with error using sync connection"""
    try:
        # Create sync database connection for Celery tasks
        sync_database_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
        engine = create_engine(sync_database_url)
        Session = sessionmaker(bind=engine)
        
        with Session() as session:
            digest = session.get(DigestRequest, digest_id)
            if digest:
                digest.status = "failed"
                digest.error_message = error_message
                digest.updated_at = datetime.utcnow()
                session.commit()
    except Exception as e:
        print(f"Error updating digest error: {e}")