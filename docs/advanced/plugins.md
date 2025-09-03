# Plugins

InjectQ's plugin system provides a powerful way to extend functionality, integrate with third-party libraries, and create reusable components that can be easily shared across projects.

## Plugin Architecture

### Plugin Interface

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Type
from dataclasses import dataclass
import importlib
import sys

@dataclass
class PluginMetadata:
    """Metadata for a plugin."""
    name: str
    version: str
    description: str
    author: str
    dependencies: List[str] = None
    tags: List[str] = None
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.tags is None:
            self.tags = []

class InjectQPlugin(ABC):
    """Base class for InjectQ plugins."""
    
    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """Get plugin metadata."""
        pass
    
    @abstractmethod
    def initialize(self, container) -> None:
        """Initialize plugin with container."""
        pass
    
    def configure(self, config: Dict[str, Any]) -> None:
        """Configure plugin with settings."""
        pass
    
    def dispose(self) -> None:
        """Cleanup plugin resources."""
        pass
    
    def get_services(self) -> Dict[Type, Any]:
        """Get services provided by this plugin."""
        return {}
    
    def get_middleware(self) -> List[Any]:
        """Get middleware provided by this plugin."""
        return []

# Plugin registry
class PluginRegistry:
    """Registry for managing plugins."""
    
    def __init__(self):
        self._plugins: Dict[str, InjectQPlugin] = {}
        self._plugin_configs: Dict[str, Dict[str, Any]] = {}
        self._loaded_plugins: Dict[str, bool] = {}
    
    def register_plugin(self, plugin: InjectQPlugin, config: Dict[str, Any] = None):
        """Register a plugin."""
        metadata = plugin.metadata
        
        if metadata.name in self._plugins:
            raise ValueError(f"Plugin '{metadata.name}' is already registered")
        
        # Check dependencies
        self._check_dependencies(metadata)
        
        # Register plugin
        self._plugins[metadata.name] = plugin
        self._plugin_configs[metadata.name] = config or {}
        self._loaded_plugins[metadata.name] = False
        
        print(f"Registered plugin: {metadata.name} v{metadata.version}")
    
    def load_plugin(self, name: str, container) -> None:
        """Load and initialize a plugin."""
        if name not in self._plugins:
            raise ValueError(f"Plugin '{name}' is not registered")
        
        if self._loaded_plugins[name]:
            return  # Already loaded
        
        plugin = self._plugins[name]
        config = self._plugin_configs[name]
        
        # Configure plugin
        plugin.configure(config)
        
        # Initialize plugin
        plugin.initialize(container)
        
        # Register plugin services
        services = plugin.get_services()
        for service_type, implementation in services.items():
            container.register(service_type, implementation)
        
        # Add plugin middleware
        middleware_list = plugin.get_middleware()
        for middleware in middleware_list:
            container.add_middleware(middleware)
        
        self._loaded_plugins[name] = True
        print(f"Loaded plugin: {name}")
    
    def unload_plugin(self, name: str) -> None:
        """Unload a plugin."""
        if name not in self._plugins:
            return
        
        if not self._loaded_plugins[name]:
            return  # Not loaded
        
        plugin = self._plugins[name]
        plugin.dispose()
        
        self._loaded_plugins[name] = False
        print(f"Unloaded plugin: {name}")
    
    def get_plugin(self, name: str) -> Optional[InjectQPlugin]:
        """Get a plugin by name."""
        return self._plugins.get(name)
    
    def list_plugins(self) -> List[PluginMetadata]:
        """List all registered plugins."""
        return [plugin.metadata for plugin in self._plugins.values()]
    
    def _check_dependencies(self, metadata: PluginMetadata):
        """Check if plugin dependencies are satisfied."""
        for dependency in metadata.dependencies:
            if dependency not in self._plugins:
                raise ValueError(
                    f"Plugin '{metadata.name}' requires dependency '{dependency}' "
                    f"which is not registered"
                )

# Global plugin registry
plugin_registry = PluginRegistry()
```

## Built-in Plugins

### Database Plugin

```python
class DatabasePlugin(InjectQPlugin):
    """Plugin for database integration."""
    
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="database",
            version="1.0.0",
            description="Database integration plugin with connection pooling",
            author="InjectQ Team",
            tags=["database", "sql", "orm"]
        )
    
    def __init__(self):
        self._connection_pool = None
        self._config = {}
    
    def configure(self, config: Dict[str, Any]) -> None:
        """Configure database plugin."""
        self._config = config
        
        # Validate required config
        required_keys = ['connection_string', 'pool_size']
        for key in required_keys:
            if key not in config:
                raise ValueError(f"Database plugin requires '{key}' configuration")
    
    def initialize(self, container) -> None:
        """Initialize database plugin."""
        # Create connection pool
        self._connection_pool = self._create_connection_pool()
        
        print(f"Database plugin initialized with pool size: {self._config['pool_size']}")
    
    def _create_connection_pool(self):
        """Create database connection pool."""
        # This would create actual connection pool
        class MockConnectionPool:
            def __init__(self, connection_string: str, pool_size: int):
                self.connection_string = connection_string
                self.pool_size = pool_size
            
            def get_connection(self):
                return MockConnection(self.connection_string)
            
            def close(self):
                print("Connection pool closed")
        
        return MockConnectionPool(
            self._config['connection_string'],
            self._config['pool_size']
        )
    
    def get_services(self) -> Dict[Type, Any]:
        """Get database services."""
        return {
            ConnectionPool: lambda: self._connection_pool,
            DatabaseConnection: lambda: self._connection_pool.get_connection(),
            UserRepository: lambda conn=self._connection_pool.get_connection(): DatabaseUserRepository(conn),
            OrderRepository: lambda conn=self._connection_pool.get_connection(): DatabaseOrderRepository(conn)
        }
    
    def dispose(self) -> None:
        """Cleanup database resources."""
        if self._connection_pool:
            self._connection_pool.close()

# Mock classes for example
class ConnectionPool:
    pass

class DatabaseConnection:
    pass

class MockConnection:
    def __init__(self, connection_string: str):
        self.connection_string = connection_string

class DatabaseUserRepository:
    def __init__(self, connection):
        self.connection = connection

class DatabaseOrderRepository:
    def __init__(self, connection):
        self.connection = connection

# Usage
database_config = {
    'connection_string': 'postgresql://localhost/mydb',
    'pool_size': 10
}

plugin_registry.register_plugin(DatabasePlugin(), database_config)
plugin_registry.load_plugin('database', container)
```

### Caching Plugin

```python
import time
from typing import Union

class CachingPlugin(InjectQPlugin):
    """Plugin for caching functionality."""
    
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="caching",
            version="1.0.0",
            description="Caching plugin with multiple backends",
            author="InjectQ Team",
            tags=["cache", "performance", "memory"]
        )
    
    def __init__(self):
        self._cache_backend = None
        self._config = {}
    
    def configure(self, config: Dict[str, Any]) -> None:
        """Configure caching plugin."""
        self._config = config
        
        # Default configuration
        self._config.setdefault('backend', 'memory')
        self._config.setdefault('ttl', 300)  # 5 minutes
        self._config.setdefault('max_size', 1000)
    
    def initialize(self, container) -> None:
        """Initialize caching plugin."""
        backend_type = self._config['backend']
        
        if backend_type == 'memory':
            self._cache_backend = MemoryCache(
                ttl=self._config['ttl'],
                max_size=self._config['max_size']
            )
        elif backend_type == 'redis':
            self._cache_backend = RedisCache(
                redis_url=self._config.get('redis_url', 'redis://localhost'),
                ttl=self._config['ttl']
            )
        else:
            raise ValueError(f"Unsupported cache backend: {backend_type}")
        
        print(f"Caching plugin initialized with {backend_type} backend")
    
    def get_services(self) -> Dict[Type, Any]:
        """Get caching services."""
        return {
            CacheService: lambda: self._cache_backend,
            CacheManager: lambda: CacheManager(self._cache_backend)
        }
    
    def get_middleware(self) -> List[Any]:
        """Get caching middleware."""
        return [CacheMiddleware(self._cache_backend)]

# Cache implementations
class CacheService(ABC):
    """Abstract cache service."""
    
    @abstractmethod
    def get(self, key: str) -> Any:
        pass
    
    @abstractmethod
    def set(self, key: str, value: Any, ttl: int = None) -> None:
        pass
    
    @abstractmethod
    def delete(self, key: str) -> None:
        pass

class MemoryCache(CacheService):
    """In-memory cache implementation."""
    
    def __init__(self, ttl: int = 300, max_size: int = 1000):
        self.ttl = ttl
        self.max_size = max_size
        self._cache: Dict[str, tuple] = {}  # key -> (value, expiry_time)
    
    def get(self, key: str) -> Any:
        """Get value from cache."""
        if key in self._cache:
            value, expiry_time = self._cache[key]
            
            if time.time() < expiry_time:
                return value
            else:
                del self._cache[key]
        
        return None
    
    def set(self, key: str, value: Any, ttl: int = None) -> None:
        """Set value in cache."""
        ttl = ttl or self.ttl
        expiry_time = time.time() + ttl
        
        # Evict old entries if at max size
        if len(self._cache) >= self.max_size:
            self._evict_old_entries()
        
        self._cache[key] = (value, expiry_time)
    
    def delete(self, key: str) -> None:
        """Delete value from cache."""
        self._cache.pop(key, None)
    
    def _evict_old_entries(self):
        """Evict expired or oldest entries."""
        current_time = time.time()
        
        # Remove expired entries
        expired_keys = [
            key for key, (_, expiry_time) in self._cache.items()
            if current_time >= expiry_time
        ]
        
        for key in expired_keys:
            del self._cache[key]
        
        # If still at max size, remove oldest
        if len(self._cache) >= self.max_size:
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k][1])
            del self._cache[oldest_key]

class RedisCache(CacheService):
    """Redis cache implementation."""
    
    def __init__(self, redis_url: str, ttl: int = 300):
        self.redis_url = redis_url
        self.ttl = ttl
        self._redis_client = None
        self._connect()
    
    def _connect(self):
        """Connect to Redis."""
        # This would use actual Redis client
        print(f"Connected to Redis at {self.redis_url}")
        self._redis_client = MockRedisClient()
    
    def get(self, key: str) -> Any:
        """Get value from Redis cache."""
        return self._redis_client.get(key)
    
    def set(self, key: str, value: Any, ttl: int = None) -> None:
        """Set value in Redis cache."""
        ttl = ttl or self.ttl
        self._redis_client.setex(key, ttl, value)
    
    def delete(self, key: str) -> None:
        """Delete value from Redis cache."""
        self._redis_client.delete(key)

class MockRedisClient:
    """Mock Redis client for example."""
    
    def __init__(self):
        self._data = {}
    
    def get(self, key: str):
        return self._data.get(key)
    
    def setex(self, key: str, ttl: int, value: Any):
        self._data[key] = value
    
    def delete(self, key: str):
        self._data.pop(key, None)

class CacheManager:
    """High-level cache manager."""
    
    def __init__(self, cache_service: CacheService):
        self.cache_service = cache_service
    
    def cached(self, key: str, ttl: int = None):
        """Decorator for caching function results."""
        def decorator(func):
            def wrapper(*args, **kwargs):
                cache_key = f"{key}:{hash((args, tuple(kwargs.items())))}"
                
                # Try to get from cache
                result = self.cache_service.get(cache_key)
                if result is not None:
                    return result
                
                # Execute function and cache result
                result = func(*args, **kwargs)
                self.cache_service.set(cache_key, result, ttl)
                
                return result
            
            return wrapper
        return decorator

class CacheMiddleware:
    """Middleware for caching service instances."""
    
    def __init__(self, cache_service: CacheService):
        self.cache_service = cache_service
    
    async def process_resolution(self, service_type: Type, next_resolver):
        """Cache service resolution."""
        cache_key = f"service:{service_type.__name__}"
        
        # Try cache first
        cached_instance = self.cache_service.get(cache_key)
        if cached_instance is not None:
            return cached_instance
        
        # Resolve and cache
        instance = await next_resolver(service_type)
        self.cache_service.set(cache_key, instance, ttl=60)  # Cache for 1 minute
        
        return instance

# Usage
caching_config = {
    'backend': 'memory',
    'ttl': 600,
    'max_size': 5000
}

plugin_registry.register_plugin(CachingPlugin(), caching_config)
plugin_registry.load_plugin('caching', container)
```

### Logging Plugin

```python
import logging
import sys
from datetime import datetime

class LoggingPlugin(InjectQPlugin):
    """Plugin for enhanced logging functionality."""
    
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="logging",
            version="1.0.0",
            description="Enhanced logging plugin with structured logging",
            author="InjectQ Team",
            tags=["logging", "monitoring", "debugging"]
        )
    
    def __init__(self):
        self._logger = None
        self._config = {}
    
    def configure(self, config: Dict[str, Any]) -> None:
        """Configure logging plugin."""
        self._config = config
        
        # Default configuration
        self._config.setdefault('level', 'INFO')
        self._config.setdefault('format', 'json')
        self._config.setdefault('output', 'console')
    
    def initialize(self, container) -> None:
        """Initialize logging plugin."""
        self._setup_logger()
        print(f"Logging plugin initialized with {self._config['format']} format")
    
    def _setup_logger(self):
        """Setup logger configuration."""
        logger_name = 'injectq'
        self._logger = logging.getLogger(logger_name)
        
        # Set level
        level = getattr(logging, self._config['level'].upper())
        self._logger.setLevel(level)
        
        # Create formatter
        if self._config['format'] == 'json':
            formatter = JsonFormatter()
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        
        # Create handler
        if self._config['output'] == 'console':
            handler = logging.StreamHandler(sys.stdout)
        elif self._config['output'] == 'file':
            handler = logging.FileHandler(self._config.get('filename', 'injectq.log'))
        else:
            handler = logging.StreamHandler(sys.stdout)
        
        handler.setFormatter(formatter)
        self._logger.addHandler(handler)
    
    def get_services(self) -> Dict[Type, Any]:
        """Get logging services."""
        return {
            StructuredLogger: lambda: StructuredLogger(self._logger),
            LoggingService: lambda: LoggingService(self._logger)
        }
    
    def get_middleware(self) -> List[Any]:
        """Get logging middleware."""
        return [DetailedLoggingMiddleware(self._logger)]

class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record):
        """Format log record as JSON."""
        import json
        
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                          'filename', 'module', 'lineno', 'funcName', 'created',
                          'msecs', 'relativeCreated', 'thread', 'threadName',
                          'processName', 'process', 'message', 'exc_info', 'exc_text',
                          'stack_info']:
                log_data[key] = value
        
        return json.dumps(log_data)

class StructuredLogger:
    """Structured logger with context support."""
    
    def __init__(self, logger: logging.Logger):
        self._logger = logger
        self._context = {}
    
    def with_context(self, **context):
        """Add context to logger."""
        new_logger = StructuredLogger(self._logger)
        new_logger._context = {**self._context, **context}
        return new_logger
    
    def info(self, message: str, **extra):
        """Log info message with context."""
        self._log(logging.INFO, message, extra)
    
    def error(self, message: str, **extra):
        """Log error message with context."""
        self._log(logging.ERROR, message, extra)
    
    def warning(self, message: str, **extra):
        """Log warning message with context."""
        self._log(logging.WARNING, message, extra)
    
    def debug(self, message: str, **extra):
        """Log debug message with context."""
        self._log(logging.DEBUG, message, extra)
    
    def _log(self, level: int, message: str, extra: Dict[str, Any]):
        """Log message with context."""
        log_extra = {**self._context, **extra}
        self._logger.log(level, message, extra=log_extra)

class LoggingService:
    """High-level logging service."""
    
    def __init__(self, logger: logging.Logger):
        self._logger = logger
    
    def log_service_resolution(self, service_type: Type, duration_ms: float, success: bool):
        """Log service resolution."""
        status = "SUCCESS" if success else "FAILED"
        self._logger.info(
            f"Service resolution {status}",
            extra={
                'service_type': service_type.__name__,
                'duration_ms': duration_ms,
                'success': success,
                'event_type': 'service_resolution'
            }
        )
    
    def log_service_registration(self, service_type: Type, implementation: Any):
        """Log service registration."""
        self._logger.info(
            "Service registered",
            extra={
                'service_type': service_type.__name__,
                'implementation': implementation.__name__ if hasattr(implementation, '__name__') else str(implementation),
                'event_type': 'service_registration'
            }
        )

class DetailedLoggingMiddleware:
    """Detailed logging middleware."""
    
    def __init__(self, logger: logging.Logger):
        self._logger = logger
    
    async def process_resolution(self, service_type: Type, next_resolver):
        """Log detailed service resolution."""
        start_time = time.time()
        
        self._logger.debug(
            "Starting service resolution",
            extra={
                'service_type': service_type.__name__,
                'event_type': 'resolution_start'
            }
        )
        
        try:
            result = await next_resolver(service_type)
            duration_ms = (time.time() - start_time) * 1000
            
            self._logger.info(
                "Service resolution completed",
                extra={
                    'service_type': service_type.__name__,
                    'duration_ms': duration_ms,
                    'event_type': 'resolution_success'
                }
            )
            
            return result
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            
            self._logger.error(
                "Service resolution failed",
                extra={
                    'service_type': service_type.__name__,
                    'duration_ms': duration_ms,
                    'error': str(e),
                    'error_type': type(e).__name__,
                    'event_type': 'resolution_error'
                },
                exc_info=True
            )
            
            raise

# Usage
logging_config = {
    'level': 'DEBUG',
    'format': 'json',
    'output': 'console'
}

plugin_registry.register_plugin(LoggingPlugin(), logging_config)
plugin_registry.load_plugin('logging', container)
```

## Plugin Discovery

### Automatic Plugin Discovery

```python
import pkgutil
import importlib.util
from pathlib import Path

class PluginDiscovery:
    """Automatic plugin discovery system."""
    
    def __init__(self):
        self._discovered_plugins: Dict[str, InjectQPlugin] = {}
    
    def discover_plugins(self, paths: List[str] = None) -> List[InjectQPlugin]:
        """Discover plugins from specified paths."""
        paths = paths or [
            'injectq_plugins',  # Standard plugin namespace
            'plugins',          # Local plugins directory
        ]
        
        discovered = []
        
        for path in paths:
            plugins = self._discover_from_path(path)
            discovered.extend(plugins)
        
        return discovered
    
    def _discover_from_path(self, path: str) -> List[InjectQPlugin]:
        """Discover plugins from a specific path."""
        plugins = []
        
        try:
            # Try to import as module
            if '.' not in path:
                # Package path
                plugins.extend(self._discover_from_package(path))
            else:
                # File path
                plugins.extend(self._discover_from_file(path))
        except ImportError:
            # Try as directory path
            plugins.extend(self._discover_from_directory(path))
        
        return plugins
    
    def _discover_from_package(self, package_name: str) -> List[InjectQPlugin]:
        """Discover plugins from Python package."""
        plugins = []
        
        try:
            package = importlib.import_module(package_name)
            
            # Look for plugin modules
            if hasattr(package, '__path__'):
                for importer, modname, ispkg in pkgutil.iter_modules(package.__path__):
                    full_name = f"{package_name}.{modname}"
                    
                    try:
                        module = importlib.import_module(full_name)
                        plugins.extend(self._extract_plugins_from_module(module))
                    except ImportError as e:
                        print(f"Failed to import plugin module {full_name}: {e}")
        
        except ImportError:
            pass  # Package not found
        
        return plugins
    
    def _discover_from_directory(self, directory_path: str) -> List[InjectQPlugin]:
        """Discover plugins from directory."""
        plugins = []
        directory = Path(directory_path)
        
        if not directory.exists():
            return plugins
        
        # Look for Python files
        for file_path in directory.glob("*.py"):
            if file_path.name.startswith('__'):
                continue
            
            plugins.extend(self._discover_from_file(str(file_path)))
        
        return plugins
    
    def _discover_from_file(self, file_path: str) -> List[InjectQPlugin]:
        """Discover plugins from Python file."""
        plugins = []
        
        try:
            spec = importlib.util.spec_from_file_location("plugin_module", file_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            plugins.extend(self._extract_plugins_from_module(module))
        
        except Exception as e:
            print(f"Failed to load plugin from {file_path}: {e}")
        
        return plugins
    
    def _extract_plugins_from_module(self, module) -> List[InjectQPlugin]:
        """Extract plugin classes from module."""
        plugins = []
        
        for name in dir(module):
            obj = getattr(module, name)
            
            # Check if it's a plugin class
            if (isinstance(obj, type) and 
                issubclass(obj, InjectQPlugin) and 
                obj is not InjectQPlugin):
                
                try:
                    # Instantiate plugin
                    plugin = obj()
                    plugins.append(plugin)
                except Exception as e:
                    print(f"Failed to instantiate plugin {name}: {e}")
        
        return plugins
    
    def auto_register_plugins(self, paths: List[str] = None) -> int:
        """Automatically discover and register plugins."""
        plugins = self.discover_plugins(paths)
        
        registered_count = 0
        for plugin in plugins:
            try:
                plugin_registry.register_plugin(plugin)
                registered_count += 1
            except Exception as e:
                print(f"Failed to register plugin {plugin.metadata.name}: {e}")
        
        return registered_count

# Usage
discovery = PluginDiscovery()
count = discovery.auto_register_plugins(['./plugins', 'injectq_plugins'])
print(f"Discovered and registered {count} plugins")
```

### Plugin Configuration

```python
import yaml
import json
from pathlib import Path

class PluginConfiguration:
    """Manages plugin configuration from files."""
    
    def __init__(self, config_file: str = "plugins.yaml"):
        self.config_file = config_file
        self._config = {}
        self.load_config()
    
    def load_config(self):
        """Load plugin configuration from file."""
        config_path = Path(self.config_file)
        
        if not config_path.exists():
            return
        
        try:
            with open(config_path, 'r') as f:
                if config_path.suffix in ['.yaml', '.yml']:
                    self._config = yaml.safe_load(f)
                elif config_path.suffix == '.json':
                    self._config = json.load(f)
                else:
                    print(f"Unsupported config file format: {config_path.suffix}")
        
        except Exception as e:
            print(f"Failed to load plugin config: {e}")
    
    def get_plugin_config(self, plugin_name: str) -> Dict[str, Any]:
        """Get configuration for a specific plugin."""
        return self._config.get('plugins', {}).get(plugin_name, {})
    
    def is_plugin_enabled(self, plugin_name: str) -> bool:
        """Check if plugin is enabled."""
        plugin_config = self.get_plugin_config(plugin_name)
        return plugin_config.get('enabled', True)
    
    def get_enabled_plugins(self) -> List[str]:
        """Get list of enabled plugin names."""
        enabled = []
        
        for plugin_name, config in self._config.get('plugins', {}).items():
            if config.get('enabled', True):
                enabled.append(plugin_name)
        
        return enabled
    
    def apply_configuration(self):
        """Apply configuration to registered plugins."""
        for plugin_name in self.get_enabled_plugins():
            plugin = plugin_registry.get_plugin(plugin_name)
            
            if plugin:
                config = self.get_plugin_config(plugin_name)
                plugin.configure(config)

# Example configuration file (plugins.yaml):
"""
plugins:
  database:
    enabled: true
    connection_string: "postgresql://localhost/myapp"
    pool_size: 20
    timeout: 30
  
  caching:
    enabled: true
    backend: "redis"
    redis_url: "redis://localhost:6379"
    ttl: 3600
  
  logging:
    enabled: true
    level: "INFO"
    format: "json"
    output: "file"
    filename: "app.log"
"""

# Usage
config = PluginConfiguration("plugins.yaml")
config.apply_configuration()
```

## Plugin Management

### Plugin Manager

```python
class PluginManager:
    """Comprehensive plugin management system."""
    
    def __init__(self, container):
        self.container = container
        self.registry = plugin_registry
        self.discovery = PluginDiscovery()
        self.config = PluginConfiguration()
        self._load_order: List[str] = []
    
    def setup_plugins(self, auto_discover: bool = True, config_file: str = None):
        """Setup all plugins with configuration."""
        if config_file:
            self.config = PluginConfiguration(config_file)
        
        # Auto-discover plugins
        if auto_discover:
            self.discovery.auto_register_plugins()
        
        # Apply configuration
        self.config.apply_configuration()
        
        # Load enabled plugins in dependency order
        self._load_plugins_in_order()
    
    def _load_plugins_in_order(self):
        """Load plugins in dependency order."""
        enabled_plugins = self.config.get_enabled_plugins()
        loaded = set()
        
        def load_plugin_recursive(plugin_name: str):
            if plugin_name in loaded:
                return
            
            plugin = self.registry.get_plugin(plugin_name)
            if not plugin:
                print(f"Plugin '{plugin_name}' not found")
                return
            
            # Load dependencies first
            for dependency in plugin.metadata.dependencies:
                if dependency in enabled_plugins:
                    load_plugin_recursive(dependency)
            
            # Load plugin
            try:
                self.registry.load_plugin(plugin_name, self.container)
                loaded.add(plugin_name)
                self._load_order.append(plugin_name)
            except Exception as e:
                print(f"Failed to load plugin '{plugin_name}': {e}")
        
        # Load all enabled plugins
        for plugin_name in enabled_plugins:
            load_plugin_recursive(plugin_name)
    
    def reload_plugin(self, plugin_name: str):
        """Reload a specific plugin."""
        # Unload plugin
        self.registry.unload_plugin(plugin_name)
        
        # Reload configuration
        self.config.load_config()
        
        # Apply configuration
        plugin = self.registry.get_plugin(plugin_name)
        if plugin:
            config = self.config.get_plugin_config(plugin_name)
            plugin.configure(config)
            
            # Load plugin
            self.registry.load_plugin(plugin_name, self.container)
    
    def get_plugin_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all plugins."""
        status = {}
        
        for metadata in self.registry.list_plugins():
            plugin_name = metadata.name
            
            status[plugin_name] = {
                'metadata': metadata,
                'enabled': self.config.is_plugin_enabled(plugin_name),
                'loaded': self.registry._loaded_plugins.get(plugin_name, False),
                'config': self.config.get_plugin_config(plugin_name)
            }
        
        return status
    
    def print_plugin_status(self):
        """Print plugin status report."""
        status = self.get_plugin_status()
        
        print("Plugin Status Report")
        print("=" * 50)
        
        for plugin_name, info in status.items():
            metadata = info['metadata']
            enabled = "✅" if info['enabled'] else "❌"
            loaded = "🟢" if info['loaded'] else "🔴"
            
            print(f"{enabled} {loaded} {plugin_name} v{metadata.version}")
            print(f"    {metadata.description}")
            
            if metadata.dependencies:
                deps = ", ".join(metadata.dependencies)
                print(f"    Dependencies: {deps}")
            
            print()

# Usage
def setup_application_with_plugins():
    """Setup application with plugin system."""
    # Create container
    container = MiddlewareContainer()
    
    # Create plugin manager
    plugin_manager = PluginManager(container)
    
    # Setup plugins
    plugin_manager.setup_plugins(auto_discover=True, config_file="plugins.yaml")
    
    # Print status
    plugin_manager.print_plugin_status()
    
    return container, plugin_manager

# Initialize application
container, plugin_manager = setup_application_with_plugins()
```

This comprehensive plugin system documentation shows how to extend InjectQ through a flexible and powerful plugin architecture, enabling modular functionality and easy integration of third-party components.
