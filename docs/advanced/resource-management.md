# Resource Management

**Resource management** provides automatic lifecycle management for dependencies that require initialization and cleanup, such as database connections, file handles, and network sockets.

## 🎯 Resource Lifecycle

### Basic Resource Pattern

```python
from injectq import resource, InjectQ
from typing import AsyncContextManager

@resource
class DatabaseConnection:
    """Database connection with automatic lifecycle management."""

    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.connection = None
        self.is_initialized = False

    async def initialize(self):
        """Initialize the resource."""
        if not self.is_initialized:
            self.connection = await create_database_connection(self.config)
            self.is_initialized = True
            print(f"Database connection initialized: {id(self.connection)}")

    async def dispose(self):
        """Clean up the resource."""
        if self.connection and self.is_initialized:
            await self.connection.close()
            self.is_initialized = False
            print(f"Database connection disposed: {id(self.connection)}")

    async def execute_query(self, query: str):
        """Use the resource."""
        if not self.is_initialized:
            await self.initialize()
        return await self.connection.execute(query)

# Usage
async def main():
    container = InjectQ()
    container.bind(DatabaseConnection, DatabaseConnection(DatabaseConfig()))

    async with container.resource_scope():
        db = container.get(DatabaseConnection)

        # Resource automatically initialized
        result = await db.execute_query("SELECT * FROM users")
        print(f"Query result: {result}")

    # Resource automatically disposed
```

### Resource Scope Management

```python
# Resource scope ensures proper cleanup
async def handle_request(container):
    async with container.resource_scope():
        # Resources initialized when first accessed
        db = container.get(DatabaseConnection)
        cache = container.get(CacheConnection)

        # Use resources
        user_data = await db.execute_query("SELECT * FROM users WHERE id = ?", request.user_id)
        await cache.set(f"user:{request.user_id}", user_data)

        return {"user": user_data}

    # All resources automatically disposed here

# Nested scopes
async def complex_operation(container):
    async with container.resource_scope() as outer_scope:
        # Outer scope resources
        db = container.get(DatabaseConnection)

        async with container.resource_scope() as inner_scope:
            # Inner scope can access outer scope resources
            cache = container.get(CacheConnection)
            # Inner scope resources disposed here

        # Outer scope resources still available
        await db.execute_query("COMMIT")

    # All resources disposed here
```

## 🔧 Resource Types

### Connection Pool Resources

```python
@resource
class DatabasePool:
    """Database connection pool with resource management."""

    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.pool = None
        self.active_connections = 0
        self.max_connections = config.max_connections

    async def initialize(self):
        """Initialize the connection pool."""
        self.pool = await create_connection_pool(
            host=self.config.host,
            port=self.config.port,
            database=self.config.database,
            min_size=self.config.min_connections,
            max_size=self.config.max_connections
        )
        print(f"Database pool initialized with {self.max_connections} max connections")

    async def dispose(self):
        """Close all connections in the pool."""
        if self.pool:
            await self.pool.close()
            print("Database pool disposed")

    async def acquire_connection(self):
        """Acquire a connection from the pool."""
        if not self.pool:
            await self.initialize()

        if self.active_connections >= self.max_connections:
            raise ResourceExhaustedError("No available connections")

        connection = await self.pool.acquire()
        self.active_connections += 1

        # Return connection with automatic release
        return ConnectionWrapper(connection, self)

    def release_connection(self, connection):
        """Release a connection back to the pool."""
        if hasattr(connection, '_raw_connection'):
            self.pool.release(connection._raw_connection)
        self.active_connections -= 1

class ConnectionWrapper:
    """Wrapper that automatically releases connection."""
    def __init__(self, connection, pool: DatabasePool):
        self._connection = connection
        self._pool = pool

    async def __aenter__(self):
        return self._connection

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._pool.release_connection(self)

# Usage
async def query_with_pool(container):
    pool = container.get(DatabasePool)

    async with container.resource_scope():
        async with pool.acquire_connection() as conn:
            result = await conn.execute("SELECT * FROM users")
            return result
```

### File Handle Resources

```python
@resource
class FileManager:
    """File handle manager with automatic cleanup."""

    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.open_files = {}
        self.lock = asyncio.Lock()

    async def initialize(self):
        """Ensure base directory exists."""
        self.base_path.mkdir(parents=True, exist_ok=True)
        print(f"File manager initialized at {self.base_path}")

    async def dispose(self):
        """Close all open files."""
        async with self.lock:
            for file_path, file_handle in self.open_files.items():
                await file_handle.close()
                print(f"Closed file: {file_path}")
            self.open_files.clear()

    async def open_file(self, filename: str, mode: str = 'r'):
        """Open a file with automatic management."""
        file_path = self.base_path / filename

        async with self.lock:
            if str(file_path) in self.open_files:
                return self.open_files[str(file_path)]

            file_handle = await aiofiles.open(file_path, mode)
            self.open_files[str(file_path)] = file_handle

            return FileWrapper(file_handle, str(file_path), self)

    def close_file(self, file_path: str):
        """Close a specific file."""
        if file_path in self.open_files:
            # Note: In real implementation, this would be async
            # For simplicity, we'll mark for cleanup
            pass

class FileWrapper:
    """Wrapper for file handles with automatic cleanup."""
    def __init__(self, file_handle, file_path: str, manager: FileManager):
        self._file_handle = file_handle
        self._file_path = file_path
        self._manager = manager

    async def __aenter__(self):
        return self._file_handle

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._file_handle.close()
        self._manager.close_file(self._file_path)

# Usage
async def process_file(container):
    file_manager = container.get(FileManager)

    async with container.resource_scope():
        async with file_manager.open_file("data.txt", "r") as f:
            content = await f.read()
            return content
```

### Network Connection Resources

```python
@resource
class HTTPClientPool:
    """HTTP client pool with connection management."""

    def __init__(self, config: HTTPConfig):
        self.config = config
        self.session = None
        self.connector = None

    async def initialize(self):
        """Initialize HTTP client with connection pool."""
        self.connector = aiohttp.TCPConnector(
            limit=self.config.max_connections,
            limit_per_host=self.config.max_connections_per_host,
            ttl_dns_cache=self.config.dns_cache_ttl
        )

        self.session = aiohttp.ClientSession(
            connector=self.connector,
            timeout=aiohttp.ClientTimeout(total=self.config.timeout)
        )

        print(f"HTTP client pool initialized with {self.config.max_connections} connections")

    async def dispose(self):
        """Close HTTP client and connections."""
        if self.session:
            await self.session.close()
            print("HTTP client pool disposed")

    async def request(self, method: str, url: str, **kwargs):
        """Make HTTP request using pooled connection."""
        if not self.session:
            await self.initialize()

        async with self.session.request(method, url, **kwargs) as response:
            return await response.json()

# Usage
async def fetch_data(container):
    http_client = container.get(HTTPClientPool)

    async with container.resource_scope():
        # Connection automatically managed
        data = await http_client.request('GET', 'https://api.example.com/data')
        return data
```

## 🎨 Resource Patterns

### Resource Factory Pattern

```python
class ResourceFactory:
    """Factory for creating different types of resources."""

    @staticmethod
    def create_database_pool(config: DatabaseConfig):
        @resource
        class DatabasePoolResource:
            def __init__(self):
                self.pool = None

            async def initialize(self):
                self.pool = await create_pool(config)

            async def dispose(self):
                if self.pool:
                    await self.pool.close()

            def get_pool(self):
                return self.pool

        return DatabasePoolResource()

    @staticmethod
    def create_cache_client(config: CacheConfig):
        @resource
        class CacheResource:
            def __init__(self):
                self.client = None

            async def initialize(self):
                self.client = await create_cache_client(config)

            async def dispose(self):
                if self.client:
                    await self.client.close()

            def get_client(self):
                return self.client

        return CacheResource()

# Usage
def setup_resources(container, db_config, cache_config):
    # Create and bind resources
    container.bind(DatabasePool, ResourceFactory.create_database_pool(db_config))
    container.bind(CacheClient, ResourceFactory.create_cache_client(cache_config))
```

### Resource Decorator Pattern

```python
def managed_resource(initialize_func=None, dispose_func=None):
    """Decorator to create managed resources."""
    def decorator(cls):
        original_init = cls.__init__

        async def __init__(self, *args, **kwargs):
            await original_init(self, *args, **kwargs)
            if initialize_func:
                await initialize_func(self)

        async def dispose(self):
            if dispose_func:
                await dispose_func(self)

        cls.__init__ = __init__
        cls.dispose = dispose

        # Mark as resource
        cls._is_injectq_resource = True

        return cls

    return decorator

# Usage
@managed_resource(
    initialize_func=lambda self: self.connect(),
    dispose_func=lambda self: self.disconnect()
)
class RedisClient:
    def __init__(self, config: RedisConfig):
        self.config = config
        self.connection = None

    async def connect(self):
        self.connection = await redis.create_connection(self.config.url)

    async def disconnect(self):
        if self.connection:
            self.connection.close()

    async def get(self, key: str):
        return await self.connection.get(key)

    async def set(self, key: str, value: str):
        return await self.connection.set(key, value)

# Automatic resource management
async def use_redis(container):
    redis_client = container.get(RedisClient)

    async with container.resource_scope():
        await redis_client.set("key", "value")
        result = await redis_client.get("key")
        return result
```

### Resource Pool Pattern

```python
@resource
class GenericResourcePool:
    """Generic resource pool for any type of resource."""

    def __init__(self, factory, max_size: int = 10):
        self.factory = factory
        self.max_size = max_size
        self.available = asyncio.Queue(maxsize=max_size)
        self.in_use = set()
        self.lock = asyncio.Lock()

    async def initialize(self):
        """Pre-populate the pool."""
        for _ in range(self.max_size):
            resource = await self.factory()
            await self.available.put(resource)
        print(f"Resource pool initialized with {self.max_size} resources")

    async def dispose(self):
        """Clean up all resources."""
        async with self.lock:
            # Close available resources
            while not self.available.empty():
                resource = await self.available.get()
                await self.cleanup_resource(resource)

            # Close in-use resources
            for resource in self.in_use:
                await self.cleanup_resource(resource)

            self.in_use.clear()

    async def acquire(self):
        """Acquire a resource from the pool."""
        resource = await self.available.get()

        async with self.lock:
            self.in_use.add(resource)

        return PooledResource(resource, self)

    def release(self, resource):
        """Release a resource back to the pool."""
        async with self.lock:
            if resource in self.in_use:
                self.in_use.remove(resource)
                self.available.put_nowait(resource)

    async def cleanup_resource(self, resource):
        """Clean up a single resource."""
        if hasattr(resource, 'close'):
            await resource.close()
        elif hasattr(resource, 'dispose'):
            await resource.dispose()

class PooledResource:
    """Wrapper for pooled resources."""
    def __init__(self, resource, pool: GenericResourcePool):
        self.resource = resource
        self.pool = pool

    async def __aenter__(self):
        return self.resource

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.pool.release(self.resource)

# Usage
async def create_database_connection():
    # Factory function for database connections
    return await create_connection()

async def use_pooled_resources(container):
    # Create pool of database connections
    pool = GenericResourcePool(create_database_connection, max_size=5)
    container.bind(DatabasePool, pool)

    async with container.resource_scope():
        async with pool.acquire() as conn:
            result = await conn.execute("SELECT * FROM users")
            return result
```

## 🚨 Resource Management Best Practices

### ✅ Good Patterns

#### 1. Proper Resource Cleanup

```python
# ✅ Good: Use resource scopes
async def handle_request(container):
    async with container.resource_scope():
        db = container.get(DatabaseConnection)
        cache = container.get(CacheClient)

        # Resources automatically cleaned up
        result = await process_request(db, cache)
        return result

# ✅ Good: Explicit cleanup in synchronous code
def process_sync(container):
    with container.resource_scope():
        service = container.get(Service)
        result = service.process()
        return result
```

#### 2. Resource Error Handling

```python
# ✅ Good: Handle resource initialization errors
@resource
class UnreliableResource:
    async def initialize(self):
        try:
            self.resource = await create_unreliable_resource()
        except Exception as e:
            print(f"Failed to initialize resource: {e}")
            raise ResourceInitializationError(f"Resource init failed: {e}")

    async def dispose(self):
        try:
            if self.resource:
                await self.resource.cleanup()
        except Exception as e:
            print(f"Error during resource cleanup: {e}")
            # Don't re-raise in dispose

# ✅ Good: Graceful degradation
async def use_resource_with_fallback(container):
    try:
        async with container.resource_scope():
            resource = container.get(PrimaryResource)
            return await resource.process()
    except ResourceInitializationError:
        # Fallback to secondary resource
        async with container.resource_scope():
            fallback = container.get(FallbackResource)
            return await fallback.process()
```

#### 3. Resource Monitoring

```python
# ✅ Good: Monitor resource usage
@resource
class MonitoredDatabasePool:
    def __init__(self):
        self.active_connections = 0
        self.total_connections_created = 0
        self.connection_times = []

    async def initialize(self):
        # Initialize monitoring
        self.start_time = time.time()

    async def acquire_connection(self):
        start_time = time.time()
        connection = await self._acquire()
        connection_time = time.time() - start_time

        self.connection_times.append(connection_time)
        self.active_connections += 1

        # Log slow connections
        if connection_time > 1.0:  # 1 second
            print(f"Slow connection acquisition: {connection_time}s")

        return connection

    def get_metrics(self):
        return {
            "active_connections": self.active_connections,
            "total_created": self.total_connections_created,
            "avg_connection_time": sum(self.connection_times) / len(self.connection_times) if self.connection_times else 0,
            "max_connection_time": max(self.connection_times) if self.connection_times else 0
        }
```

### ❌ Bad Patterns

#### 1. Manual Resource Management

```python
# ❌ Bad: Manual resource management
async def bad_resource_handling(container):
    db = container.get(DatabaseConnection)

    # Manual initialization - error prone
    await db.initialize()

    try:
        result = await db.query("SELECT * FROM users")
        return result
    finally:
        # Manual cleanup - easy to forget
        await db.dispose()

# ❌ Bad: Resource leaks
def leaky_function(container):
    resource = container.get(SomeResource)
    # No cleanup - resource leak!
    return resource.do_something()
```

#### 2. Resource Exhaustion

```python
# ❌ Bad: No limits on resource usage
@resource
class UnlimitedPool:
    def __init__(self):
        self.connections = []

    async def acquire_connection(self):
        # Create unlimited connections - can exhaust system
        conn = await create_connection()
        self.connections.append(conn)
        return conn

# ❌ Bad: Long-running resources
@resource
class LongRunningResource:
    async def initialize(self):
        # Very slow initialization
        await asyncio.sleep(30)  # 30 seconds!

    async def dispose(self):
        # Slow cleanup
        await asyncio.sleep(10)
```

#### 3. Improper Error Handling

```python
# ❌ Bad: Exceptions in dispose
@resource
class BadDisposeResource:
    async def dispose(self):
        # Don't raise exceptions in dispose
        if self.resource:
            await self.resource.close()
        raise Exception("Dispose failed!")  # Bad!

# ❌ Bad: Ignoring dispose errors
@resource
class IgnoringErrorsResource:
    async def dispose(self):
        try:
            await self.resource.close()
        except Exception:
            pass  # Silently ignore - can hide issues
```

## 📊 Resource Monitoring

### Resource Usage Metrics

```python
class ResourceMonitor:
    """Monitor resource usage across the application."""

    def __init__(self, container: InjectQ):
        self.container = container
        self.metrics = {
            "resources_created": 0,
            "resources_disposed": 0,
            "active_resources": 0,
            "resource_errors": 0,
            "avg_lifetime": 0
        }
        self.resource_lifetimes = []

    def track_resource_creation(self, resource):
        self.metrics["resources_created"] += 1
        self.metrics["active_resources"] += 1
        resource._creation_time = time.time()

    def track_resource_disposal(self, resource):
        self.metrics["resources_disposed"] += 1
        self.metrics["active_resources"] -= 1

        if hasattr(resource, '_creation_time'):
            lifetime = time.time() - resource._creation_time
            self.resource_lifetimes.append(lifetime)
            self.metrics["avg_lifetime"] = sum(self.resource_lifetimes) / len(self.resource_lifetimes)

    def track_resource_error(self, error):
        self.metrics["resource_errors"] += 1

    def get_report(self):
        return {
            **self.metrics,
            "total_lifetimes_tracked": len(self.resource_lifetimes),
            "median_lifetime": sorted(self.resource_lifetimes)[len(self.resource_lifetimes)//2] if self.resource_lifetimes else 0
        }

# Usage
monitor = ResourceMonitor(container)

# Integrate with resource lifecycle
@resource
class MonitoredResource:
    def __init__(self, monitor: ResourceMonitor):
        self.monitor = monitor
        self.monitor.track_resource_creation(self)

    async def dispose(self):
        try:
            await self._cleanup()
        except Exception as e:
            self.monitor.track_resource_error(e)
        finally:
            self.monitor.track_resource_disposal(self)
```

### Health Checks

```python
class ResourceHealthChecker:
    """Check health of resources."""

    def __init__(self, container: InjectQ):
        self.container = container

    async def check_all_resources(self):
        """Check health of all resources."""
        results = {}

        # Get all resources (this would require container introspection)
        resources = self.container.get_all_resources()

        for resource_type, resource in resources.items():
            try:
                health = await self.check_resource_health(resource)
                results[resource_type.__name__] = health
            except Exception as e:
                results[resource_type.__name__] = {
                    "status": "error",
                    "error": str(e)
                }

        return results

    async def check_resource_health(self, resource):
        """Check health of a single resource."""
        if hasattr(resource, 'health_check'):
            # Resource has built-in health check
            return await resource.health_check()
        elif hasattr(resource, 'ping'):
            # Simple ping check
            await resource.ping()
            return {"status": "healthy"}
        else:
            # Basic check - try to use the resource
            try:
                # This is resource-type specific
                if hasattr(resource, 'execute'):
                    await resource.execute("SELECT 1")
                elif hasattr(resource, 'get'):
                    await resource.get("health_check_key")
                else:
                    # Unknown resource type
                    return {"status": "unknown", "message": "No health check available"}

                return {"status": "healthy"}
            except Exception as e:
                return {"status": "unhealthy", "error": str(e)}

# Usage
health_checker = ResourceHealthChecker(container)
health_status = await health_checker.check_all_resources()

for resource_name, status in health_status.items():
    if status["status"] != "healthy":
        print(f"Resource {resource_name} is unhealthy: {status}")
```

## 🎯 Summary

Resource management provides automatic lifecycle management:

- **Resource lifecycle** - Automatic initialization and cleanup
- **Resource scopes** - Context managers for proper resource handling
- **Resource types** - Connection pools, file handles, network connections
- **Resource patterns** - Factories, decorators, and pools
- **Resource monitoring** - Usage metrics and health checks

**Key features:**
- Automatic resource initialization when first accessed
- Automatic cleanup when exiting resource scopes
- Support for async and sync resource management
- Resource pooling for efficient resource usage
- Monitoring and health checking capabilities

**Best practices:**
- Use resource scopes for automatic cleanup
- Handle errors gracefully in resource methods
- Monitor resource usage and performance
- Implement proper health checks
- Avoid manual resource management
- Set appropriate resource limits

**Common patterns:**
- Database connection pools
- HTTP client pools
- File handle management
- Resource factories and decorators
- Resource monitoring and health checks

Ready to explore [diagnostics](diagnostics.md)?
