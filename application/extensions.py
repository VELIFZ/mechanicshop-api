from flask_marshmallow import Marshmallow
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_caching import Cache
import os
import warnings

ma = Marshmallow()

# Suppress the flask-limiter storage warnings
warnings.filterwarnings("ignore", message="Using the in-memory storage for tracking rate limits")

# Configure rate limiter with Redis (now that redis package will be available)
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=os.getenv("REDIS_URL", "redis://localhost:6379"),
    default_limits=["200 per day", "50 per hour"],
    swallow_errors=True  # Graceful fallback if Redis is unavailable
)
                  
cache = Cache(config={
    'CACHE_TYPE': 'RedisCache',
    'CACHE_REDIS_URL': os.getenv('REDIS_URL', 'redis://localhost:6379'),
    'CACHE_DEFAULT_TIMEOUT': 300,  # 5 minutes default
    'CACHE_THRESHOLD': 500  # Maximum number of items to store in the cache
})



