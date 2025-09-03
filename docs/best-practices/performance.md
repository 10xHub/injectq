# Performance Best Practices

This guide provides comprehensive recommendations for optimizing performance when using InjectQ in production applications.

## 🚀 Container Configuration Optimization

### Use Appropriate Lifecycles

Choosing the right lifecycle for your dependencies is crucial for performance:

```python
from injectq import InjectQ, Module, inject

class PerformanceOptimizedModule(Module):
    def configure(self):
        # Singleton for expensive-to-create objects
        self.bind(DatabaseConnection, DatabaseConnection).singleton()
        self.bind(CacheService, RedisCache).singleton()
        self.bind(LoggingService, LoggingService).singleton()
        
        # Scoped for stateful services within request boundaries
        self.bind(UserService, UserService).scoped()
        self.bind(OrderService, OrderService).scoped()
        
        # Transient only when necessary (stateless, lightweight)
        self.bind(ValidationService, ValidationService).transient()
        self.bind(CalculationEngine, CalculationEngine).transient()

# ❌ Bad: Everything as transient
class IneffientModule(Module):
    def configure(self):
        self.bind(DatabaseConnection, DatabaseConnection).transient()  # Expensive!
        self.bind(CacheService, RedisCache).transient()  # Unnecessary overhead!
        self.bind(UserService, UserService).transient()

# ✅ Good: Appropriate lifecycles
class OptimizedModule(Module):
    def configure(self):
        # Expensive resources as singletons
        self.bind(DatabaseConnection, DatabaseConnection).singleton()
        self.bind(CacheService, RedisCache).singleton()
        
        # Request-scoped services
        self.bind(UserService, UserService).scoped()
```

### Minimize Container Lookups

Cache frequently accessed dependencies instead of repeated container lookups:

```python
# ❌ Bad: Repeated container lookups
class IneffientService:
    @inject
    def __init__(self, container: InjectQ):
        self.container = container
    
    def process_data(self, data):
        # Expensive lookup every time
        validator = self.container.get(DataValidator)
        processor = self.container.get(DataProcessor)
        logger = self.container.get(Logger)
        
        # Process data...

# ✅ Good: Inject dependencies directly
class EfficientService:
    @inject
    def __init__(
        self,
        validator: DataValidator,
        processor: DataProcessor,
        logger: Logger
    ):
        self.validator = validator
        self.processor = processor
        self.logger = logger
    
    def process_data(self, data):
        # Direct access, no container lookups
        self.validator.validate(data)
        result = self.processor.process(data)
        self.logger.log(f"Processed {len(data)} items")
        return result

# ✅ Good: Cache for dynamic lookups
class CachedDynamicService:
    @inject
    def __init__(self, container: InjectQ):
        self.container = container
        self._handler_cache = {}
    
    def get_handler(self, handler_type: str):
        if handler_type not in self._handler_cache:
            self._handler_cache[handler_type] = self.container.get(
                IHandler, name=handler_type
            )
        return self._handler_cache[handler_type]
```

### Optimize Module Registration

```python
# ✅ Efficient module registration
class ProductionModule(Module):
    def configure(self):
        # Group related bindings
        self._configure_data_layer()
        self._configure_services()
        self._configure_external_apis()
    
    def _configure_data_layer(self):
        """Configure data access layer efficiently."""
        # Connection pool as singleton
        self.bind(ConnectionPool, self._create_connection_pool()).singleton()
        
        # Repository base class with shared dependencies
        self.bind(IRepository, BaseRepository, name="base").singleton()
        
        # Specific repositories inheriting base
        self.bind(UserRepository, UserRepository).scoped()
        self.bind(OrderRepository, OrderRepository).scoped()
    
    def _create_connection_pool(self) -> ConnectionPool:
        """Factory method for expensive resource creation."""
        return ConnectionPool(
            host="db.example.com",
            port=5432,
            min_connections=5,
            max_connections=20
        )
```

## 🏃‍♂️ Runtime Performance Optimization

### Async/Await Best Practices

```python
import asyncio
from injectq import InjectQ, inject
from typing import List

class AsyncOptimizedService:
    @inject
    def __init__(
        self,
        database: AsyncDatabase,
        cache: AsyncCache,
        api_client: AsyncAPIClient
    ):
        self.database = database
        self.cache = cache
        self.api_client = api_client
    
    async def process_user_data(self, user_ids: List[str]) -> List[dict]:
        """Optimized async processing with concurrency."""
        
        # ✅ Good: Concurrent cache lookups
        cache_tasks = [
            self.cache.get(f"user:{user_id}")
            for user_id in user_ids
        ]
        cache_results = await asyncio.gather(*cache_tasks, return_exceptions=True)
        
        # Identify cache misses
        missing_users = []
        cached_users = {}
        
        for user_id, result in zip(user_ids, cache_results):
            if isinstance(result, Exception) or result is None:
                missing_users.append(user_id)
            else:
                cached_users[user_id] = result
        
        # ✅ Good: Batch database query for missing users
        if missing_users:
            db_users = await self.database.get_users_batch(missing_users)
            
            # ✅ Good: Concurrent cache updates
            cache_updates = [
                self.cache.set(f"user:{user['id']}", user, ttl=300)
                for user in db_users
            ]
            await asyncio.gather(*cache_updates, return_exceptions=True)
            
            # Update cached users
            for user in db_users:
                cached_users[user['id']] = user
        
        return [cached_users[user_id] for user_id in user_ids if user_id in cached_users]

# ❌ Bad: Sequential processing
class SequentialService:
    @inject
    def __init__(self, database: AsyncDatabase, cache: AsyncCache):
        self.database = database
        self.cache = cache
    
    async def process_user_data(self, user_ids: List[str]) -> List[dict]:
        users = []
        for user_id in user_ids:  # Sequential - slow!
            user = await self.cache.get(f"user:{user_id}")
            if not user:
                user = await self.database.get_user(user_id)  # N+1 queries!
                await self.cache.set(f"user:{user_id}", user)
            users.append(user)
        return users
```

### Memory Management

```python
import weakref
from typing import Dict, Any
from injectq import inject, Module

class MemoryEfficientService:
    """Service that manages memory efficiently."""
    
    @inject
    def __init__(self, cache_service: CacheService):
        self.cache = cache_service
        self._weak_refs: Dict[str, weakref.ref] = {}
        self._memory_threshold = 100 * 1024 * 1024  # 100MB
    
    def get_large_object(self, key: str) -> Any:
        """Get large object with memory management."""
        # Check weak reference first
        if key in self._weak_refs:
            obj = self._weak_refs[key]()
            if obj is not None:
                return obj
            else:
                # Object was garbage collected
                del self._weak_refs[key]
        
        # Load from cache or create
        obj = self.cache.get(key)
        if obj is None:
            obj = self._create_large_object(key)
            self.cache.set(key, obj)
        
        # Store weak reference
        self._weak_refs[key] = weakref.ref(obj)
        
        return obj
    
    def cleanup_memory(self):
        """Periodic memory cleanup."""
        import gc
        import psutil
        import os
        
        # Check memory usage
        process = psutil.Process(os.getpid())
        memory_usage = process.memory_info().rss
        
        if memory_usage > self._memory_threshold:
            # Force garbage collection
            gc.collect()
            
            # Clear weak references to dead objects
            dead_refs = [
                key for key, ref in self._weak_refs.items()
                if ref() is None
            ]
            for key in dead_refs:
                del self._weak_refs[key]

# Module with memory optimization
class MemoryOptimizedModule(Module):
    def configure(self):
        # Use scoped lifecycle for memory-intensive services
        self.bind(DataProcessingService, DataProcessingService).scoped()
        
        # Singleton for lightweight services
        self.bind(MemoryEfficientService, MemoryEfficientService).singleton()
```

## 📊 Monitoring and Profiling

### Performance Monitoring

```python
import time
import functools
from dataclasses import dataclass
from typing import Dict, List
from injectq import inject

@dataclass
class PerformanceMetric:
    method_name: str
    execution_time: float
    memory_usage: int
    call_count: int

class PerformanceMonitor:
    """Monitor service performance."""
    
    def __init__(self):
        self.metrics: Dict[str, List[float]] = {}
        self.call_counts: Dict[str, int] = {}
    
    def record_execution(self, method_name: str, execution_time: float):
        """Record method execution time."""
        if method_name not in self.metrics:
            self.metrics[method_name] = []
            self.call_counts[method_name] = 0
        
        self.metrics[method_name].append(execution_time)
        self.call_counts[method_name] += 1
    
    def get_performance_report(self) -> List[PerformanceMetric]:
        """Generate performance report."""
        report = []
        
        for method_name, times in self.metrics.items():
            avg_time = sum(times) / len(times)
            call_count = self.call_counts[method_name]
            
            report.append(PerformanceMetric(
                method_name=method_name,
                execution_time=avg_time,
                memory_usage=0,  # Would need psutil for actual memory tracking
                call_count=call_count
            ))
        
        return sorted(report, key=lambda x: x.execution_time, reverse=True)

def monitor_performance(monitor: PerformanceMonitor):
    """Decorator to monitor method performance."""
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                end_time = time.perf_counter()
                execution_time = end_time - start_time
                monitor.record_execution(
                    f"{func.__module__}.{func.__qualname__}",
                    execution_time
                )
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                end_time = time.perf_counter()
                execution_time = end_time - start_time
                monitor.record_execution(
                    f"{func.__module__}.{func.__qualname__}",
                    execution_time
                )
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator

class MonitoredService:
    @inject
    def __init__(self, database: Database, monitor: PerformanceMonitor):
        self.database = database
        self.monitor = monitor
    
    @monitor_performance
    async def process_data(self, data: List[dict]) -> List[dict]:
        """Monitored data processing method."""
        results = []
        for item in data:
            processed = await self._process_item(item)
            results.append(processed)
        return results
    
    async def _process_item(self, item: dict) -> dict:
        # Processing logic here
        await asyncio.sleep(0.01)  # Simulate work
        return {"processed": True, **item}
```

### Database Connection Optimization

```python
import asyncpg
from contextlib import asynccontextmanager
from injectq import inject, Module

class OptimizedDatabaseService:
    """Database service with connection pooling and optimization."""
    
    @inject
    def __init__(self, connection_pool: asyncpg.Pool):
        self.pool = connection_pool
    
    @asynccontextmanager
    async def get_connection(self):
        """Context manager for database connections."""
        async with self.pool.acquire() as connection:
            yield connection
    
    async def execute_batch_query(self, queries: List[str]) -> List[Any]:
        """Execute multiple queries efficiently."""
        async with self.get_connection() as conn:
            async with conn.transaction():
                results = []
                for query in queries:
                    result = await conn.fetch(query)
                    results.append(result)
                return results
    
    async def bulk_insert(self, table: str, data: List[Dict]) -> int:
        """Optimized bulk insert operation."""
        if not data:
            return 0
        
        # Prepare column names and placeholders
        columns = list(data[0].keys())
        column_names = ", ".join(columns)
        placeholders = ", ".join(f"${i+1}" for i in range(len(columns)))
        
        query = f"INSERT INTO {table} ({column_names}) VALUES ({placeholders})"
        
        async with self.get_connection() as conn:
            # Use executemany for bulk operations
            values = [[row[col] for col in columns] for row in data]
            await conn.executemany(query, values)
            return len(data)

class DatabaseModule(Module):
    def configure(self):
        # Connection pool configuration
        self.bind(asyncpg.Pool, self._create_pool()).singleton()
        self.bind(OptimizedDatabaseService, OptimizedDatabaseService).singleton()
    
    async def _create_pool(self) -> asyncpg.Pool:
        """Create optimized connection pool."""
        return await asyncpg.create_pool(
            "postgresql://user:pass@localhost/db",
            min_size=5,
            max_size=20,
            command_timeout=60,
            server_settings={
                'application_name': 'injectq_app',
                'jit': 'off'  # Disable JIT for small queries
            }
        )
```

## 🎯 Caching Strategies

### Multi-Level Caching

```python
from abc import ABC, abstractmethod
from typing import Optional, Any
import asyncio
import json
import hashlib

class ICacheLayer(ABC):
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        pass
    
    @abstractmethod
    async def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        pass

class MemoryCache(ICacheLayer):
    """In-memory cache layer (L1)."""
    
    def __init__(self, max_size: int = 1000):
        self._cache: Dict[str, Any] = {}
        self._max_size = max_size
    
    async def get(self, key: str) -> Optional[Any]:
        return self._cache.get(key)
    
    async def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        if len(self._cache) >= self._max_size:
            # Simple LRU eviction (remove first item)
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
        
        self._cache[key] = value
        return True
    
    async def delete(self, key: str) -> bool:
        self._cache.pop(key, None)
        return True

class RedisCache(ICacheLayer):
    """Redis cache layer (L2)."""
    
    @inject
    def __init__(self, redis_client: RedisClient):
        self.redis = redis_client
    
    async def get(self, key: str) -> Optional[Any]:
        data = await self.redis.get(key)
        if data:
            return json.loads(data)
        return None
    
    async def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        data = json.dumps(value, default=str)
        return await self.redis.setex(key, ttl, data)
    
    async def delete(self, key: str) -> bool:
        return await self.redis.delete(key) > 0

class MultiLevelCache:
    """Multi-level caching system."""
    
    @inject
    def __init__(self, l1_cache: MemoryCache, l2_cache: RedisCache):
        self.l1 = l1_cache
        self.l2 = l2_cache
    
    async def get(self, key: str) -> Optional[Any]:
        # Try L1 cache first
        value = await self.l1.get(key)
        if value is not None:
            return value
        
        # Try L2 cache
        value = await self.l2.get(key)
        if value is not None:
            # Populate L1 cache
            await self.l1.set(key, value, ttl=60)  # Shorter TTL for L1
            return value
        
        return None
    
    async def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        # Set in both layers
        l1_result = await self.l1.set(key, value, min(ttl, 60))
        l2_result = await self.l2.set(key, value, ttl)
        return l1_result and l2_result
    
    async def delete(self, key: str) -> bool:
        # Delete from both layers
        l1_result = await self.l1.delete(key)
        l2_result = await self.l2.delete(key)
        return l1_result or l2_result

class CachedDataService:
    """Service with intelligent caching."""
    
    @inject
    def __init__(
        self,
        database: DatabaseService,
        cache: MultiLevelCache
    ):
        self.database = database
        self.cache = cache
    
    async def get_user_profile(self, user_id: str) -> Optional[dict]:
        """Get user profile with caching."""
        cache_key = f"user_profile:{user_id}"
        
        # Try cache first
        cached_profile = await self.cache.get(cache_key)
        if cached_profile:
            return cached_profile
        
        # Load from database
        profile = await self.database.get_user_profile(user_id)
        if profile:
            # Cache with appropriate TTL
            await self.cache.set(cache_key, profile, ttl=1800)  # 30 minutes
        
        return profile
    
    async def update_user_profile(self, user_id: str, updates: dict) -> bool:
        """Update user profile and invalidate cache."""
        success = await self.database.update_user_profile(user_id, updates)
        
        if success:
            # Invalidate cache
            cache_key = f"user_profile:{user_id}"
            await self.cache.delete(cache_key)
        
        return success
    
    def _generate_cache_key(self, prefix: str, **kwargs) -> str:
        """Generate consistent cache key."""
        key_data = f"{prefix}:" + ":".join(f"{k}={v}" for k, v in sorted(kwargs.items()))
        return hashlib.md5(key_data.encode()).hexdigest()
```

## 🔥 Production Performance Checklist

### Container Setup

- [ ] **Use appropriate lifecycles**: Singletons for expensive resources, scoped for request-bound services
- [ ] **Minimize container lookups**: Inject dependencies directly instead of container access
- [ ] **Cache dynamic lookups**: Store frequently accessed named dependencies
- [ ] **Avoid circular dependencies**: Design clean dependency graphs
- [ ] **Use lazy loading**: Only create dependencies when needed

### Async Performance

- [ ] **Use concurrent operations**: Batch operations with `asyncio.gather()`
- [ ] **Implement connection pooling**: Reuse database and HTTP connections
- [ ] **Optimize database queries**: Use bulk operations and prepared statements
- [ ] **Add circuit breakers**: Prevent cascade failures in external service calls
- [ ] **Implement timeouts**: Set appropriate timeouts for all async operations

### Memory Management

- [ ] **Monitor memory usage**: Track memory consumption in production
- [ ] **Use weak references**: For large objects that can be garbage collected
- [ ] **Implement cleanup routines**: Periodic memory cleanup for long-running services
- [ ] **Profile memory leaks**: Regular memory profiling to identify leaks
- [ ] **Configure garbage collection**: Tune Python GC settings for your workload

### Caching Strategy

- [ ] **Multi-level caching**: Implement L1 (memory) and L2 (Redis) caching
- [ ] **Cache invalidation**: Clear cache when data changes
- [ ] **TTL optimization**: Set appropriate cache expiration times
- [ ] **Cache warming**: Pre-populate cache for frequently accessed data
- [ ] **Monitor cache hit rates**: Track and optimize cache effectiveness

### Monitoring and Observability

- [ ] **Performance metrics**: Track response times and throughput
- [ ] **Error monitoring**: Log and alert on errors and exceptions
- [ ] **Resource utilization**: Monitor CPU, memory, and I/O usage
- [ ] **Dependency health**: Monitor external service health
- [ ] **Custom metrics**: Track business-specific performance indicators

### Example Production Configuration

```python
# production_config.py
from injectq import InjectQ, Module
import asyncio
import logging

class ProductionModule(Module):
    def configure(self):
        # Performance optimized bindings
        self._configure_database()
        self._configure_caching()
        self._configure_monitoring()
    
    def _configure_database(self):
        """Configure optimized database connections."""
        self.bind(DatabaseConfig, DatabaseConfig(
            max_connections=20,
            min_connections=5,
            connection_timeout=30,
            command_timeout=60
        )).singleton()
        
        self.bind(ConnectionPool, self._create_connection_pool()).singleton()
        self.bind(DatabaseService, OptimizedDatabaseService).singleton()
    
    def _configure_caching(self):
        """Configure multi-level caching."""
        self.bind(MemoryCache, MemoryCache(max_size=1000)).singleton()
        self.bind(RedisCache, RedisCache).singleton()
        self.bind(MultiLevelCache, MultiLevelCache).singleton()
    
    def _configure_monitoring(self):
        """Configure performance monitoring."""
        self.bind(PerformanceMonitor, PerformanceMonitor).singleton()
        self.bind(MetricsCollector, MetricsCollector).singleton()

# Usage in production
async def main():
    # Setup container with production optimizations
    container = InjectQ()
    container.install(ProductionModule())
    
    # Pre-warm critical services
    database = container.get(DatabaseService)
    cache = container.get(MultiLevelCache)
    
    # Start performance monitoring
    monitor = container.get(PerformanceMonitor)
    
    # Application startup
    app = container.get(Application)
    await app.start()

if __name__ == "__main__":
    # Configure logging for production
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    asyncio.run(main())
```

Following these performance best practices will ensure your InjectQ applications run efficiently in production environments with optimal resource utilization and response times.
