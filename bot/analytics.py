from typing import Dict, Any, Optional
import time
from datetime import datetime, timedelta
import logging

from prometheus_client import Counter, Histogram, Gauge, start_http_server
import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration

from config import Config
from database import Database

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Sentry
sentry_sdk.init(
    dsn=Config.SENTRY_DSN,
    integrations=[
        LoggingIntegration(
            level=logging.INFO,
            event_level=logging.ERROR
        )
    ],
    traces_sample_rate=1.0,
)

class Analytics:
    """Analytics and monitoring class"""
    
    def __init__(self, db: Database):
        """Initialize analytics"""
        self.db = db
        
        # Prometheus metrics
        self.message_counter = Counter(
            'bot_messages_total',
            'Total number of messages processed',
            ['platform', 'type']
        )
        
        self.request_duration = Histogram(
            'bot_request_duration_seconds',
            'Time spent processing requests',
            ['endpoint']
        )
        
        self.active_users = Gauge(
            'bot_active_users',
            'Number of active users',
            ['platform']
        )
        
        self.error_counter = Counter(
            'bot_errors_total',
            'Total number of errors',
            ['type']
        )
        
        # Start Prometheus server
        start_http_server(8000)
    
    async def track_message(self, platform: str, message_type: str):
        """Track message metrics"""
        try:
            # Increment Prometheus counter
            self.message_counter.labels(platform=platform, type=message_type).inc()
            
            # Store in MongoDB for detailed analytics
            await self.db.store_analytics({
                "event": "message",
                "platform": platform,
                "type": message_type,
                "timestamp": datetime.utcnow()
            })
        except Exception as e:
            logger.error(f"Error tracking message: {e}")
            sentry_sdk.capture_exception(e)
    
    async def track_request_duration(self, endpoint: str):
        """Track request duration using context manager"""
        class TimerContextManager:
            def __init__(self, analytics, endpoint):
                self.analytics = analytics
                self.endpoint = endpoint
                self.start_time = None
            
            async def __aenter__(self):
                self.start_time = time.time()
                return self
            
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                duration = time.time() - self.start_time
                self.analytics.request_duration.labels(endpoint=self.endpoint).observe(duration)
                
                if exc_type:
                    sentry_sdk.capture_exception(exc_val)
                    self.analytics.error_counter.labels(type=str(exc_type.__name__)).inc()
        
        return TimerContextManager(self, endpoint)
    
    async def update_active_users(self, platform: str, count: int):
        """Update active users gauge"""
        self.active_users.labels(platform=platform).set(count)
    
    async def track_error(self, error_type: str, error: Exception):
        """Track error metrics"""
        try:
            # Increment Prometheus counter
            self.error_counter.labels(type=error_type).inc()
            
            # Send to Sentry
            sentry_sdk.capture_exception(error)
            
            # Store in MongoDB
            await self.db.store_analytics({
                "event": "error",
                "type": error_type,
                "message": str(error),
                "timestamp": datetime.utcnow()
            })
        except Exception as e:
            logger.error(f"Error tracking error: {e}")
            sentry_sdk.capture_exception(e)
    
    async def get_daily_stats(self, date: Optional[datetime] = None) -> Dict[str, Any]:
        """Get daily statistics"""
        try:
            if not date:
                date = datetime.utcnow()
            
            start_date = date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = start_date + timedelta(days=1)
            
            pipeline = [
                {
                    "$match": {
                        "timestamp": {
                            "$gte": start_date,
                            "$lt": end_date
                        }
                    }
                },
                {
                    "$group": {
                        "_id": {
                            "event": "$event",
                            "platform": "$platform"
                        },
                        "count": {"$sum": 1}
                    }
                }
            ]
            
            stats = await self.db.mongo_db.analytics.aggregate(pipeline).to_list(None)
            
            # Format results
            results = {
                "date": date.date().isoformat(),
                "total_messages": 0,
                "platform_stats": {},
                "error_count": 0
            }
            
            for stat in stats:
                event_type = stat["_id"]["event"]
                platform = stat["_id"].get("platform", "unknown")
                count = stat["count"]
                
                if event_type == "message":
                    results["total_messages"] += count
                    if platform not in results["platform_stats"]:
                        results["platform_stats"][platform] = 0
                    results["platform_stats"][platform] += count
                elif event_type == "error":
                    results["error_count"] += count
            
            return results
            
        except Exception as e:
            logger.error(f"Error getting daily stats: {e}")
            sentry_sdk.capture_exception(e)
            return {
                "date": date.date().isoformat() if date else datetime.utcnow().date().isoformat(),
                "error": str(e)
            }
    
    async def get_user_activity(self, user_id: int) -> Dict[str, Any]:
        """Get user activity statistics"""
        try:
            pipeline = [
                {
                    "$match": {
                        "user_id": user_id,
                        "timestamp": {
                            "$gte": datetime.utcnow() - timedelta(days=30)
                        }
                    }
                },
                {
                    "$group": {
                        "_id": {
                            "date": {"$dateToString": {"format": "%Y-%m-%d", "date": "$timestamp"}},
                            "event": "$event"
                        },
                        "count": {"$sum": 1}
                    }
                },
                {
                    "$sort": {"_id.date": 1}
                }
            ]
            
            activity = await self.db.mongo_db.analytics.aggregate(pipeline).to_list(None)
            
            # Format results
            results = {
                "user_id": user_id,
                "total_messages": 0,
                "daily_activity": {},
                "platforms_used": set()
            }
            
            for entry in activity:
                date = entry["_id"]["date"]
                event = entry["_id"]["event"]
                count = entry["count"]
                
                if date not in results["daily_activity"]:
                    results["daily_activity"][date] = {"messages": 0, "errors": 0}
                
                if event == "message":
                    results["daily_activity"][date]["messages"] += count
                    results["total_messages"] += count
                elif event == "error":
                    results["daily_activity"][date]["errors"] += count
            
            return results
            
        except Exception as e:
            logger.error(f"Error getting user activity: {e}")
            sentry_sdk.capture_exception(e)
            return {
                "user_id": user_id,
                "error": str(e)
            } 