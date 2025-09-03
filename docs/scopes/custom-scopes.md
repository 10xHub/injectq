# Custom Scopes

**Custom scopes** allow you to define your own **lifetime management** rules beyond the built-in singleton, transient, and scoped options.

## 🎯 What are Custom Scopes?

Custom scopes let you control **exactly when** service instances are created and destroyed, based on your application's specific needs.

```python
from injectq import InjectQ, Scope, ScopeManager

class SessionScopeManager(ScopeManager):
    """Manages per-user-session lifetime"""

    def __init__(self):
        self._sessions = {}

    def enter_scope(self, session_id: str):
        if session_id not in self._sessions:
            self._sessions[session_id] = {}
        self._current_session = session_id

    def exit_scope(self):
        self._current_session = None

    def get_current_scope(self):
        if not hasattr(self, '_current_session'):
            return None
        return self._sessions.get(self._current_session)

# Register custom scope
container = InjectQ()
container.register_scope_manager("session", SessionScopeManager())

# Use custom scope
@container.bind(scope="session")
class UserPreferences:
    def __init__(self):
        self.theme = "light"
        self.language = "en"

# Usage
def handle_user_request(session_id: str, request):
    with container.scope("session", session_id) as scope:
        prefs = scope.get(UserPreferences)
        return {"theme": prefs.theme}
```

## 🏗️ When to Use Custom Scopes

### ✅ Perfect For

- **User sessions** - Per-user lifetime
- **Tenant isolation** - Per-tenant services
- **Workflow contexts** - Per-workflow state
- **Batch operations** - Per-batch lifetime
- **Feature flags** - Per-feature context

```python
# User session scope
class UserSessionScope:
    """✅ Good - per-user session data"""

# Tenant scope
class TenantScope:
    """✅ Good - per-tenant isolation"""

# Workflow scope
class WorkflowScope:
    """✅ Good - per-workflow context"""

# Batch scope
class BatchScope:
    """✅ Good - per-batch operation"""
```

### ❌ Avoid When

- **Simple cases** - Use built-in scopes
- **Global state** - Use singleton
- **Request state** - Use scoped
- **Stateless ops** - Use transient

```python
# ❌ Overkill for simple request
class RequestScope:
    """Use built-in scoped instead"""

# ❌ Overkill for global config
class GlobalScope:
    """Use singleton instead"""
```

## 🔧 Creating Custom Scopes

### Basic Scope Manager

```python
from injectq import ScopeManager
from typing import Dict, Any, Optional

class CustomScopeManager(ScopeManager):
    """Basic custom scope manager"""

    def __init__(self):
        self._scopes: Dict[str, Dict[str, Any]] = {}
        self._current_scope: Optional[str] = None

    def enter_scope(self, scope_id: str):
        """Enter a new scope context"""
        if scope_id not in self._scopes:
            self._scopes[scope_id] = {}
        self._current_scope = scope_id

    def exit_scope(self):
        """Exit current scope context"""
        self._current_scope = None

    def get_current_scope(self) -> Optional[Dict[str, Any]]:
        """Get current scope storage"""
        if self._current_scope is None:
            return None
        return self._scopes.get(self._current_scope)

    def cleanup_scope(self, scope_id: str):
        """Clean up a specific scope"""
        if scope_id in self._scopes:
            del self._scopes[scope_id]
```

### Registration and Usage

```python
# Create and register scope manager
scope_manager = CustomScopeManager()
container.register_scope_manager("custom", scope_manager)

# Bind services to custom scope
@container.bind(scope="custom")
class CustomService:
    def __init__(self):
        self.instance_id = str(uuid.uuid4())
        print(f"Custom service created: {self.instance_id}")

# Usage
def use_custom_scope():
    with container.scope("custom", "my_scope_1") as scope:
        service1 = scope.get(CustomService)
        service2 = scope.get(CustomService)

        # Same instance within scope
        assert service1 is service2

    # Different scope gets different instance
    with container.scope("custom", "my_scope_2") as scope:
        service3 = scope.get(CustomService)
        assert service3 is not service1
```

## 🎨 Advanced Custom Scopes

### User Session Scope

```python
class UserSessionManager(ScopeManager):
    """Manages per-user session services"""

    def __init__(self, session_timeout: int = 3600):
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._session_times: Dict[str, float] = {}
        self._timeout = session_timeout
        self._current_session: Optional[str] = None

    def enter_scope(self, session_id: str):
        """Enter user session context"""
        current_time = time.time()

        # Clean up expired sessions
        self._cleanup_expired_sessions(current_time)

        # Create new session if needed
        if session_id not in self._sessions:
            self._sessions[session_id] = {}
            self._session_times[session_id] = current_time

        self._current_session = session_id

    def exit_scope(self):
        """Exit session context"""
        self._current_session = None

    def get_current_scope(self) -> Optional[Dict[str, Any]]:
        """Get current session storage"""
        if self._current_session is None:
            return None
        return self._sessions.get(self._current_session)

    def _cleanup_expired_sessions(self, current_time: float):
        """Remove expired sessions"""
        expired = [
            session_id for session_id, create_time
            in self._session_times.items()
            if current_time - create_time > self._timeout
        ]

        for session_id in expired:
            if session_id in self._sessions:
                del self._sessions[session_id]
            if session_id in self._session_times:
                del self._session_times[session_id]

# Usage
session_manager = UserSessionManager(session_timeout=1800)  # 30 minutes
container.register_scope_manager("session", session_manager)

@container.bind(scope="session")
class UserPreferences:
    def __init__(self):
        self.theme = "light"
        self.notifications = True

def handle_user_request(session_id: str, request):
    with container.scope("session", session_id) as scope:
        prefs = scope.get(UserPreferences)

        if request.action == "update_theme":
            prefs.theme = request.theme

        return {"theme": prefs.theme}
```

### Tenant Scope

```python
class TenantScopeManager(ScopeManager):
    """Manages per-tenant service isolation"""

    def __init__(self):
        self._tenants: Dict[str, Dict[str, Any]] = {}
        self._current_tenant: Optional[str] = None

    def enter_scope(self, tenant_id: str):
        """Enter tenant context"""
        if tenant_id not in self._tenants:
            self._tenants[tenant_id] = {}
        self._current_tenant = tenant_id

    def exit_scope(self):
        """Exit tenant context"""
        self._current_tenant = None

    def get_current_scope(self) -> Optional[Dict[str, Any]]:
        """Get current tenant storage"""
        if self._current_tenant is None:
            return None
        return self._tenants.get(self._current_tenant)

    def get_tenant_services(self, tenant_id: str) -> Dict[str, Any]:
        """Get all services for a tenant"""
        return self._tenants.get(tenant_id, {})

# Usage
tenant_manager = TenantScopeManager()
container.register_scope_manager("tenant", tenant_manager)

@container.bind(scope="tenant")
class TenantConfig:
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.database_url = f"postgresql://tenant_{tenant_id}"
        self.features = self._load_tenant_features(tenant_id)

    def _load_tenant_features(self, tenant_id: str) -> List[str]:
        # Load tenant-specific features
        return ["basic", "premium"] if tenant_id == "premium" else ["basic"]

def process_tenant_request(tenant_id: str, request):
    with container.scope("tenant", tenant_id) as scope:
        config = scope.get(TenantConfig)
        return {"features": config.features}
```

### Workflow Scope

```python
class WorkflowScopeManager(ScopeManager):
    """Manages per-workflow execution context"""

    def __init__(self):
        self._workflows: Dict[str, Dict[str, Any]] = {}
        self._current_workflow: Optional[str] = None

    def enter_scope(self, workflow_id: str):
        """Enter workflow context"""
        if workflow_id not in self._workflows:
            self._workflows[workflow_id] = {
                "start_time": time.time(),
                "steps": [],
                "status": "running"
            }
        self._current_workflow = workflow_id

    def exit_scope(self):
        """Exit workflow context"""
        if self._current_workflow:
            workflow_data = self._workflows.get(self._current_workflow, {})
            workflow_data["end_time"] = time.time()
            workflow_data["status"] = "completed"
        self._current_workflow = None

    def get_current_scope(self) -> Optional[Dict[str, Any]]:
        """Get current workflow storage"""
        if self._current_workflow is None:
            return None
        return self._workflows.get(self._current_workflow)

    def record_step(self, step_name: str, result: Any):
        """Record workflow step execution"""
        if self._current_workflow:
            workflow_data = self._workflows.get(self._current_workflow, {})
            workflow_data["steps"].append({
                "name": step_name,
                "result": result,
                "timestamp": time.time()
            })

# Usage
workflow_manager = WorkflowScopeManager()
container.register_scope_manager("workflow", workflow_manager)

@container.bind(scope="workflow")
class WorkflowContext:
    def __init__(self):
        self.data = {}
        self.errors = []

    def set_data(self, key: str, value: Any):
        self.data[key] = value

    def add_error(self, error: str):
        self.errors.append(error)

def execute_workflow_step(workflow_id: str, step_name: str):
    with container.scope("workflow", workflow_id) as scope:
        context = scope.get(WorkflowContext)

        try:
            result = execute_step_logic(step_name, context.data)
            context.set_data(f"{step_name}_result", result)
            workflow_manager.record_step(step_name, result)
            return {"success": True, "result": result}
        except Exception as e:
            context.add_error(str(e))
            workflow_manager.record_step(step_name, {"error": str(e)})
            return {"success": False, "error": str(e)}
```

## ⚡ Performance Considerations

### Memory Management

```python
class MemoryAwareScopeManager(ScopeManager):
    """Scope manager with memory limits"""

    def __init__(self, max_scopes: int = 1000, max_memory_mb: int = 100):
        self._scopes = {}
        self._max_scopes = max_scopes
        self._max_memory_mb = max_memory_mb
        self._current_scope = None

    def enter_scope(self, scope_id: str):
        # Cleanup old scopes if limit reached
        if len(self._scopes) >= self._max_scopes:
            self._cleanup_old_scopes()

        if scope_id not in self._scopes:
            self._scopes[scope_id] = {}
        self._current_scope = scope_id

    def _cleanup_old_scopes(self):
        """Remove oldest scopes to free memory"""
        # Simple LRU cleanup - remove oldest 10%
        scope_ids = list(self._scopes.keys())
        to_remove = scope_ids[:len(scope_ids) // 10]

        for scope_id in to_remove:
            del self._scopes[scope_id]
```

### Thread Safety

```python
import threading

class ThreadSafeScopeManager(ScopeManager):
    """Thread-safe scope manager"""

    def __init__(self):
        self._scopes = {}
        self._current_scopes = {}  # thread_id -> scope_id
        self._lock = threading.RLock()

    def enter_scope(self, scope_id: str):
        with self._lock:
            thread_id = threading.get_ident()

            if scope_id not in self._scopes:
                self._scopes[scope_id] = {}
            self._current_scopes[thread_id] = scope_id

    def exit_scope(self):
        with self._lock:
            thread_id = threading.get_ident()
            if thread_id in self._current_scopes:
                del self._current_scopes[thread_id]

    def get_current_scope(self):
        with self._lock:
            thread_id = threading.get_ident()
            scope_id = self._current_scopes.get(thread_id)

            if scope_id is None:
                return None
            return self._scopes.get(scope_id)
```

### Async Support

```python
import asyncio
from contextvars import ContextVar

class AsyncScopeManager(ScopeManager):
    """Async-aware scope manager"""

    def __init__(self):
        self._scopes = {}
        self._current_scope: ContextVar[Optional[str]] = ContextVar('current_scope', default=None)

    def enter_scope(self, scope_id: str):
        if scope_id not in self._scopes:
            self._scopes[scope_id] = {}
        self._current_scope.set(scope_id)

    def exit_scope(self):
        self._current_scope.set(None)

    def get_current_scope(self):
        scope_id = self._current_scope.get()
        if scope_id is None:
            return None
        return self._scopes.get(scope_id)

# Usage in async context
async def async_operation():
    async with container.scope("async_custom", "my_scope") as scope:
        service = scope.get(MyAsyncService)
        result = await service.process_async()
        return result
```

## 🧪 Testing Custom Scopes

### Testing Scope Isolation

```python
def test_custom_scope_isolation():
    """Test that custom scopes properly isolate instances"""
    scope_manager = CustomScopeManager()
    container.register_scope_manager("test", scope_manager)

    @container.bind(scope="test")
    class TestService:
        def __init__(self):
            self.id = str(uuid.uuid4())

    # Test different scopes get different instances
    with container.scope("test", "scope1") as scope1:
        service1 = scope1.get(TestService)

    with container.scope("test", "scope2") as scope2:
        service2 = scope2.get(TestService)

    assert service1.id != service2.id

def test_custom_scope_sharing():
    """Test that same scope shares instances"""
    scope_manager = CustomScopeManager()
    container.register_scope_manager("test", scope_manager)

    @container.bind(scope="test")
    class TestService:
        def __init__(self):
            self.id = str(uuid.uuid4())

    with container.scope("test", "scope1") as scope:
        service1 = scope.get(TestService)
        service2 = scope.get(TestService)

    assert service1.id == service2.id
    assert service1 is service2
```

### Testing Scope Lifecycle

```python
def test_scope_lifecycle():
    """Test scope creation and cleanup"""
    scope_manager = CustomScopeManager()
    container.register_scope_manager("test", scope_manager)

    @container.bind(scope="test")
    class LifecycleService:
        def __init__(self):
            self.created = True

        def __del__(self):
            self.destroyed = True

    # Test scope creation
    with container.scope("test", "scope1") as scope:
        service = scope.get(LifecycleService)
        assert service.created

    # Test scope cleanup
    assert "scope1" not in scope_manager._scopes
```

### Testing Concurrent Scopes

```python
def test_concurrent_scopes():
    """Test custom scopes work correctly with concurrency"""
    scope_manager = ThreadSafeScopeManager()
    container.register_scope_manager("thread", scope_manager)

    @container.bind(scope="thread")
    class ThreadService:
        def __init__(self):
            self.thread_id = threading.get_ident()

    results = []

    def worker(scope_id: str):
        with container.scope("thread", scope_id) as scope:
            service = scope.get(ThreadService)
            results.append((scope_id, service.thread_id))

    # Run multiple threads with different scopes
    threads = []
    for i in range(5):
        t = threading.Thread(target=worker, args=[f"scope_{i}"])
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    # Each scope should have its own service instance
    scope_ids = set()
    for scope_id, thread_id in results:
        scope_ids.add(scope_id)

    assert len(scope_ids) == 5
```

## 🚨 Common Custom Scope Mistakes

### 1. Memory Leaks

```python
class LeakyScopeManager(ScopeManager):
    """❌ Never cleans up scopes"""

    def __init__(self):
        self._scopes = {}
        self._current_scope = None

    def enter_scope(self, scope_id: str):
        if scope_id not in self._scopes:
            self._scopes[scope_id] = {}
        self._current_scope = scope_id

    # ❌ No cleanup method
    # Scopes accumulate forever!

# ✅ Proper cleanup
class CleanScopeManager(ScopeManager):
    def __init__(self):
        self._scopes = {}
        self._current_scope = None
        self._scope_times = {}

    def enter_scope(self, scope_id: str):
        current_time = time.time()
        if scope_id not in self._scopes:
            self._scopes[scope_id] = {}
            self._scope_times[scope_id] = current_time
        self._current_scope = scope_id

    def cleanup_expired_scopes(self, max_age: float = 3600):
        """Clean up old scopes"""
        current_time = time.time()
        expired = [
            scope_id for scope_id, create_time
            in self._scope_times.items()
            if current_time - create_time > max_age
        ]

        for scope_id in expired:
            if scope_id in self._scopes:
                del self._scopes[scope_id]
            if scope_id in self._scope_times:
                del self._scope_times[scope_id]
```

### 2. Thread Safety Issues

```python
class UnsafeScopeManager(ScopeManager):
    """❌ Not thread-safe"""

    def __init__(self):
        self._scopes = {}
        self._current_scope = None  # ❌ Shared across threads

    def enter_scope(self, scope_id: str):
        if scope_id not in self._scopes:
            self._scopes[scope_id] = {}  # ❌ Race condition
        self._current_scope = scope_id  # ❌ Overwrites other threads

# ✅ Thread-safe
class SafeScopeManager(ScopeManager):
    def __init__(self):
        self._scopes = {}
        self._current_scopes = {}  # thread_id -> scope_id
        self._lock = threading.RLock()

    def enter_scope(self, scope_id: str):
        with self._lock:
            thread_id = threading.get_ident()
            if scope_id not in self._scopes:
                self._scopes[scope_id] = {}
            self._current_scopes[thread_id] = scope_id

    def get_current_scope(self):
        with self._lock:
            thread_id = threading.get_ident()
            scope_id = self._current_scopes.get(thread_id)
            if scope_id is None:
                return None
            return self._scopes.get(scope_id)
```

### 3. Scope Confusion

```python
# ❌ Confusing scope names
container.register_scope_manager("my_custom_scope", MyScopeManager())
container.register_scope_manager("another_custom", AnotherScopeManager())

# Usage is confusing
with container.scope("my_custom_scope", "id") as scope:
    service = scope.get(Service)

# ✅ Clear scope names
container.register_scope_manager("user_session", UserSessionManager())
container.register_scope_manager("tenant", TenantScopeManager())

# Usage is clear
with container.scope("user_session", user_id) as scope:
    service = scope.get(Service)
```

## 🏆 Best Practices

### 1. Clear Naming Conventions

```python
# ✅ Good naming
container.register_scope_manager("user_session", UserSessionManager())
container.register_scope_manager("tenant_isolation", TenantScopeManager())
container.register_scope_manager("request_batch", BatchScopeManager())

# ❌ Bad naming
container.register_scope_manager("custom1", MyScopeManager())
container.register_scope_manager("scope2", AnotherScopeManager())
```

### 2. Implement Proper Cleanup

```python
class WellBehavedScopeManager(ScopeManager):
    def __init__(self):
        self._scopes = {}
        self._scope_metadata = {}  # Track creation time, size, etc.

    def cleanup_expired_scopes(self):
        """Regular cleanup of expired scopes"""
        current_time = time.time()
        expired = [
            scope_id for scope_id, metadata
            in self._scope_metadata.items()
            if current_time - metadata["created"] > metadata["ttl"]
        ]

        for scope_id in expired:
            self._cleanup_scope(scope_id)

    def _cleanup_scope(self, scope_id: str):
        """Clean up a specific scope and its resources"""
        if scope_id in self._scopes:
            # Clean up any resources in the scope
            scope_data = self._scopes[scope_id]
            for key, value in scope_data.items():
                if hasattr(value, 'cleanup'):
                    value.cleanup()

            del self._scopes[scope_id]

        if scope_id in self._scope_metadata:
            del self._scope_metadata[scope_id]
```

### 3. Add Monitoring and Metrics

```python
class MonitoredScopeManager(ScopeManager):
    def __init__(self):
        self._scopes = {}
        self._metrics = {
            "active_scopes": 0,
            "total_scopes_created": 0,
            "scopes_cleaned_up": 0
        }

    def enter_scope(self, scope_id: str):
        if scope_id not in self._scopes:
            self._scopes[scope_id] = {}
            self._metrics["total_scopes_created"] += 1
            self._metrics["active_scopes"] += 1

        self._current_scope = scope_id

    def exit_scope(self):
        if self._current_scope:
            self._metrics["active_scopes"] -= 1
        self._current_scope = None

    def get_metrics(self):
        """Get scope usage metrics"""
        return self._metrics.copy()
```

### 4. Document Scope Behavior

```python
class DocumentedScopeManager(ScopeManager):
    """
    User Session Scope Manager

    Manages service instances per user session. Each session
    maintains its own set of service instances that are shared
    within that session but isolated between sessions.

    Features:
    - Automatic session timeout (30 minutes)
    - Memory-efficient cleanup of expired sessions
    - Thread-safe operations

    Usage:
        with container.scope("user_session", session_id) as scope:
            service = scope.get(UserService)
    """

    def __init__(self, session_timeout: int = 1800):
        self.session_timeout = session_timeout
        # ... implementation
```

### 5. Test Thoroughly

```python
def test_custom_scope_comprehensive():
    """Comprehensive test of custom scope behavior"""

    # Test basic functionality
    scope_manager = CustomScopeManager()
    container.register_scope_manager("test", scope_manager)

    @container.bind(scope="test")
    class TestService:
        def __init__(self):
            self.id = str(uuid.uuid4())

    # Test isolation
    with container.scope("test", "scope1") as s1:
        svc1a = s1.get(TestService)
        svc1b = s1.get(TestService)
        assert svc1a is svc1b

    with container.scope("test", "scope2") as s2:
        svc2 = s2.get(TestService)
        assert svc2 is not svc1a

    # Test cleanup
    assert "scope1" not in scope_manager._scopes
    assert "scope2" not in scope_manager._scopes
```

## 🔄 Custom vs Built-in Scopes

### When to Use Custom Scopes

```python
# ✅ Use custom when you need:
# - Per-user sessions
# - Tenant isolation
# - Workflow-specific contexts
# - Custom lifetime rules
# - Domain-specific scoping

# ❌ Don't use custom for:
# - Simple per-request state (use scoped)
# - Global application state (use singleton)
# - Stateless operations (use transient)
```

### Migration from Built-in

```python
# Built-in scoped
@scoped
class RequestService:
    pass

# Custom equivalent
class RequestScopeManager(ScopeManager):
    def __init__(self):
        self._current_request = None

    def enter_scope(self, request_id: str):
        self._current_request = request_id
        # Custom logic here

    # ... rest of implementation

# Use custom scope
container.register_scope_manager("request", RequestScopeManager())

@container.bind(scope="request")
class RequestService:
    pass
```

## 🎯 Summary

Custom scopes provide:

- **Flexible lifetime management** - Define your own rules
- **Domain-specific contexts** - User sessions, tenants, workflows
- **Advanced features** - Cleanup, monitoring, thread safety
- **Complete control** - When instances are created/destroyed

**Perfect for:**
- User session management
- Multi-tenant applications
- Workflow execution contexts
- Batch processing
- Feature flag contexts

**Key principles:**
- Implement proper cleanup to prevent memory leaks
- Ensure thread safety for concurrent access
- Add monitoring and metrics
- Test thoroughly with isolation and concurrency
- Document behavior and usage patterns

Ready to explore [scope best practices](scope-best-practices.md)?
