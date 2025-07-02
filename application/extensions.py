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
                  
# Initialize cache without config - will be configured in init_cache
cache = Cache()

def init_cache(app):
    """Configure cache based on app configuration"""
    cache_config = {
        'CACHE_TYPE': app.config.get('CACHE_TYPE', 'SimpleCache'),
        'CACHE_DEFAULT_TIMEOUT': app.config.get('CACHE_DEFAULT_TIMEOUT', 300)
    }
    
    # Add Redis URL if using RedisCache
    if cache_config['CACHE_TYPE'] == 'RedisCache':
        cache_config['CACHE_REDIS_URL'] = app.config.get('CACHE_REDIS_URL', 'redis://localhost:6379')
    
    app.config.update(cache_config)
    cache.init_app(app)



