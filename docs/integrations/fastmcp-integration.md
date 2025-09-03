# FastMCP Integration

**FastMCP integration** enables dependency injection for MCP (Model Context Protocol) servers, providing automatic service resolution with proper request scoping and lifecycle management.

## 🎯 Getting Started

### Basic Setup

```python
from fastmcp import FastMCP
from injectq import InjectQ
from injectq.integrations.fastmcp import setup_fastmcp_integration, InjectQDependency

# 1. Create container and bind services
container = InjectQ()
container.bind(IDocumentService, DocumentService())
container.bind(IUserService, UserService())
container.bind(IAuthService, AuthService())

# 2. Create FastMCP server
mcp = FastMCP("My MCP Server")

# 3. Set up integration
setup_fastmcp_integration(mcp, container)

# 4. Use dependency injection in tools
@mcp.tool()
async def search_documents(
    query: str,
    limit: int = 10,
    doc_service: IDocumentService = InjectQDependency(IDocumentService),
    user_service: IUserService = InjectQDependency(IUserService)
):
    """Search documents with user context."""
    # Get current user from context
    user = user_service.get_current_user()

    # Search documents
    results = await doc_service.search_documents(
        query=query,
        user_id=user.id,
        limit=limit
    )

    return results

@mcp.tool()
async def create_document(
    title: str,
    content: str,
    doc_service: IDocumentService = InjectQDependency(IDocumentService),
    auth_service: IAuthService = InjectQDependency(IAuthService)
):
    """Create a new document."""
    # Verify permissions
    if not auth_service.has_permission("create_document"):
        raise ValueError("Insufficient permissions")

    # Create document
    document = await doc_service.create_document(
        title=title,
        content=content
    )

    return document

# 5. Start the server
if __name__ == "__main__":
    mcp.run()
```

### Service Definitions

```python
from typing import Protocol, List, Optional
from datetime import datetime

# Define service interfaces
class IDocumentService(Protocol):
    async def search_documents(self, query: str, user_id: int, limit: int) -> List[Document]: ...
    async def create_document(self, title: str, content: str) -> Document: ...
    async def get_document(self, doc_id: int) -> Optional[Document]: ...
    async def update_document(self, doc_id: int, title: str, content: str) -> Document: ...
    async def delete_document(self, doc_id: int) -> bool: ...

class IUserService(Protocol):
    def get_current_user(self) -> User: ...
    def get_user(self, user_id: int) -> Optional[User]: ...
    def get_user_permissions(self, user_id: int) -> List[str]: ...

class IAuthService(Protocol):
    def has_permission(self, permission: str) -> bool: ...
    def authenticate_user(self, token: str) -> Optional[User]: ...
    def authorize_action(self, user: User, action: str, resource: str) -> bool: ...

# Data models
class User:
    def __init__(self, id: int, name: str, email: str):
        self.id = id
        self.name = name
        self.email = email

class Document:
    def __init__(self, id: int, title: str, content: str, user_id: int, created_at: datetime):
        self.id = id
        self.title = title
        self.content = content
        self.user_id = user_id
        self.created_at = created_at

# Implement services
class DocumentService:
    def __init__(self, db: IDatabaseConnection):
        self.db = db

    async def search_documents(self, query: str, user_id: int, limit: int) -> List[Document]:
        # Search documents in database
        return await self.db.query(Document).filter(
            Document.user_id == user_id,
            Document.title.contains(query) | Document.content.contains(query)
        ).limit(limit).all()

    async def create_document(self, title: str, content: str) -> Document:
        # Get current user from context
        user_service = self.db.get(IUserService)  # Injected via container
        user = user_service.get_current_user()

        document = Document(
            id=self.db.next_id(),
            title=title,
            content=content,
            user_id=user.id,
            created_at=datetime.now()
        )

        await self.db.save(document)
        return document

    async def get_document(self, doc_id: int) -> Optional[Document]:
        return await self.db.query(Document).filter(Document.id == doc_id).first()

    async def update_document(self, doc_id: int, title: str, content: str) -> Document:
        document = await self.get_document(doc_id)
        if not document:
            raise ValueError(f"Document {doc_id} not found")

        document.title = title
        document.content = content
        await self.db.save(document)
        return document

    async def delete_document(self, doc_id: int) -> bool:
        document = await self.get_document(doc_id)
        if not document:
            return False

        await self.db.delete(document)
        return True

class UserService:
    def __init__(self, db: IDatabaseConnection):
        self.db = db
        self._current_user = None

    def get_current_user(self) -> User:
        if self._current_user is None:
            # Get from request context (set by middleware)
            self._current_user = self._get_user_from_context()
        return self._current_user

    def _get_user_from_context(self) -> User:
        # Implementation depends on your auth system
        # This would typically get user from request context
        pass

    def get_user(self, user_id: int) -> Optional[User]:
        return self.db.query(User).filter(User.id == user_id).first()

    def get_user_permissions(self, user_id: int) -> List[str]:
        # Get user permissions from database
        return self.db.query(Permission).filter(Permission.user_id == user_id).all()

class AuthService:
    def __init__(self, user_service: IUserService):
        self.user_service = user_service

    def has_permission(self, permission: str) -> bool:
        user = self.user_service.get_current_user()
        permissions = self.user_service.get_user_permissions(user.id)
        return permission in permissions

    def authenticate_user(self, token: str) -> Optional[User]:
        # Verify token and return user
        pass

    def authorize_action(self, user: User, action: str, resource: str) -> bool:
        # Check if user can perform action on resource
        pass
```

## 🔧 Advanced Configuration

### Request-Scoped Services

```python
from injectq import scoped

@scoped
class RequestContext:
    def __init__(self):
        self.request_id = str(uuid.uuid4())
        self.start_time = time.time()
        self.user = None
        self.metadata = {}

    def set_user(self, user: User):
        self.user = user

    def set_metadata(self, key: str, value: Any):
        self.metadata[key] = value

    def get_duration(self) -> float:
        return time.time() - self.start_time

@scoped
class RequestMetrics:
    def __init__(self):
        self.operations = []
        self.errors = []

    def record_operation(self, operation: str, duration: float):
        self.operations.append({
            "operation": operation,
            "duration": duration,
            "timestamp": time.time()
        })

    def record_error(self, error: str):
        self.errors.append({
            "error": error,
            "timestamp": time.time()
        })

# Use in MCP tools
@mcp.tool()
async def complex_document_operation(
    doc_id: int,
    operation: str,
    ctx: RequestContext = InjectQDependency(RequestContext),
    metrics: RequestMetrics = InjectQDependency(RequestMetrics),
    doc_service: IDocumentService = InjectQDependency(IDocumentService)
):
    ctx.set_metadata("operation", operation)
    ctx.set_metadata("doc_id", doc_id)

    try:
        # Perform operation with metrics
        start_time = time.time()

        if operation == "get":
            result = await doc_service.get_document(doc_id)
        elif operation == "update":
            result = await doc_service.update_document(doc_id, "New Title", "New Content")
        else:
            raise ValueError(f"Unknown operation: {operation}")

        duration = time.time() - start_time
        metrics.record_operation(operation, duration)

        return result

    except Exception as e:
        metrics.record_error(str(e))
        raise
```

### Module-Based Setup

```python
from injectq import Module

class DocumentModule(Module):
    def configure(self, binder):
        # Document services
        binder.bind(IDocumentService, DocumentService())
        binder.bind(IUserService, UserService())
        binder.bind(IAuthService, AuthService())

        # Request context services
        binder.bind(RequestContext, RequestContext())
        binder.bind(RequestMetrics, RequestMetrics())

class InfrastructureModule(Module):
    def configure(self, binder):
        # Database and external services
        binder.bind(IDatabaseConnection, PostgresConnection())
        binder.bind(ICacheService, RedisCache())

class AuthModule(Module):
    def configure(self, binder):
        # Authentication services
        binder.bind(ITokenService, JWTTokenService())
        binder.bind(ISessionService, SessionService())

def create_mcp_server() -> FastMCP:
    # Create container with modules
    container = InjectQ()
    container.install(InfrastructureModule())
    container.install(AuthModule())
    container.install(DocumentModule())

    # Create MCP server
    mcp = FastMCP("Document Management Server")

    # Set up integration
    setup_fastmcp_integration(mcp, container)

    return mcp

# Usage
mcp = create_mcp_server()
```

## 🎨 MCP Tool Patterns

### Document Management Tools

```python
@mcp.tool()
async def list_user_documents(
    limit: int = 20,
    offset: int = 0,
    doc_service: IDocumentService = InjectQDependency(IDocumentService)
):
    """List current user's documents."""
    documents = await doc_service.list_user_documents(limit, offset)
    return {
        "documents": [
            {
                "id": doc.id,
                "title": doc.title,
                "created_at": doc.created_at.isoformat()
            }
            for doc in documents
        ],
        "total": len(documents)
    }

@mcp.tool()
async def search_documents(
    query: str,
    category: Optional[str] = None,
    limit: int = 10,
    doc_service: IDocumentService = InjectQDependency(IDocumentService)
):
    """Search documents with advanced filters."""
    results = await doc_service.search_documents(
        query=query,
        category=category,
        limit=limit
    )

    return {
        "query": query,
        "results": [
            {
                "id": result.id,
                "title": result.title,
                "snippet": result.content[:200] + "..." if len(result.content) > 200 else result.content,
                "score": result.score
            }
            for result in results
        ]
    }

@mcp.tool()
async def create_document_from_template(
    template_id: int,
    title: str,
    variables: dict,
    doc_service: IDocumentService = InjectQDependency(IDocumentService),
    template_service: ITemplateService = InjectQDependency(ITemplateService)
):
    """Create document from template with variable substitution."""
    # Get template
    template = await template_service.get_template(template_id)

    # Substitute variables
    content = template.content
    for key, value in variables.items():
        content = content.replace(f"{{{{ {key} }}}}", str(value))

    # Create document
    document = await doc_service.create_document(title, content)

    return {
        "document_id": document.id,
        "title": document.title,
        "created_at": document.created_at.isoformat()
    }
```

### User Management Tools

```python
@mcp.tool()
async def get_user_profile(
    user_service: IUserService = InjectQDependency(IUserService)
):
    """Get current user's profile."""
    user = user_service.get_current_user()
    permissions = user_service.get_user_permissions(user.id)

    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "permissions": permissions
    }

@mcp.tool()
async def update_user_preferences(
    preferences: dict,
    user_service: IUserService = InjectQDependency(IUserService),
    preference_service: IPreferenceService = InjectQDependency(IPreferenceService)
):
    """Update user preferences."""
    user = user_service.get_current_user()

    await preference_service.update_preferences(user.id, preferences)

    return {"message": "Preferences updated successfully"}

@mcp.tool()
async def share_document(
    document_id: int,
    target_user_id: int,
    permissions: List[str],
    doc_service: IDocumentService = InjectQDependency(IDocumentService),
    auth_service: IAuthService = InjectQDependency(IAuthService)
):
    """Share document with another user."""
    # Check if current user owns the document
    document = await doc_service.get_document(document_id)
    current_user = doc_service.user_service.get_current_user()

    if document.user_id != current_user.id:
        raise ValueError("You can only share documents you own")

    # Check permissions
    if not auth_service.authorize_action(current_user, "share", "document"):
        raise ValueError("Insufficient permissions to share documents")

    # Share document
    await doc_service.share_document(document_id, target_user_id, permissions)

    return {"message": f"Document shared with user {target_user_id}"}
```

### Analytics and Reporting Tools

```python
@mcp.tool()
async def get_document_stats(
    document_id: int,
    analytics_service: IAnalyticsService = InjectQDependency(IAnalyticsService),
    auth_service: IAuthService = InjectQDependency(IAuthService)
):
    """Get analytics for a document."""
    # Check permissions
    if not auth_service.has_permission("view_analytics"):
        raise ValueError("Insufficient permissions")

    stats = await analytics_service.get_document_stats(document_id)

    return {
        "document_id": document_id,
        "views": stats.views,
        "unique_viewers": stats.unique_viewers,
        "last_viewed": stats.last_viewed.isoformat() if stats.last_viewed else None,
        "average_session_duration": stats.average_session_duration
    }

@mcp.tool()
async def generate_user_report(
    user_id: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    report_service: IReportService = InjectQDependency(IReportService),
    auth_service: IAuthService = InjectQDependency(IAuthService)
):
    """Generate user activity report."""
    # Check permissions
    if not auth_service.has_permission("generate_reports"):
        raise ValueError("Insufficient permissions")

    # Default to current user if not specified
    if user_id is None:
        user_service = report_service.container.get(IUserService)
        user_id = user_service.get_current_user().id

    # Parse dates
    from_date = datetime.fromisoformat(date_from) if date_from else None
    to_date = datetime.fromisoformat(date_to) if date_to else None

    # Generate report
    report = await report_service.generate_user_report(
        user_id=user_id,
        from_date=from_date,
        to_date=to_date
    )

    return {
        "user_id": user_id,
        "period": {
            "from": from_date.isoformat() if from_date else None,
            "to": to_date.isoformat() if to_date else None
        },
        "documents_created": report.documents_created,
        "documents_viewed": report.documents_viewed,
        "total_activity_time": report.total_activity_time,
        "most_active_day": report.most_active_day.isoformat() if report.most_active_day else None
    }
```

## 🧪 Testing FastMCP Integration

### Unit Testing Tools

```python
import pytest
from injectq.integrations.fastmcp import setup_fastmcp_integration

@pytest.fixture
def test_mcp():
    # Create test container
    container = InjectQ()
    container.bind(IDocumentService, MockDocumentService())
    container.bind(IUserService, MockUserService())

    # Create test MCP server
    mcp = FastMCP("Test Server")
    setup_fastmcp_integration(mcp, container)

    return mcp

def test_search_documents_tool(test_mcp):
    # Define test tool
    @test_mcp.tool()
    async def search_documents(
        query: str,
        doc_service: IDocumentService = InjectQDependency(IDocumentService)
    ):
        results = await doc_service.search_documents(query, user_id=1, limit=5)
        return {"results": results, "count": len(results)}

    # Mock the request context
    with test_mcp.test_context():
        # Execute tool
        result = await test_mcp.call_tool("search_documents", {"query": "test"})

        # Verify result
        assert "results" in result
        assert "count" in result
        assert result["count"] > 0

def test_request_scoping(test_mcp):
    # Define tool with scoped service
    @test_mcp.tool()
    async def scoped_tool(
        data: str,
        ctx: RequestContext = InjectQDependency(RequestContext)
    ):
        ctx.set_metadata("input", data)
        return ctx.metadata

    # Execute multiple requests
    with test_mcp.test_context():
        result1 = await test_mcp.call_tool("scoped_tool", {"data": "test1"})
        result2 = await test_mcp.call_tool("scoped_tool", {"data": "test2"})

    # Each request should have its own context
    assert result1["input"] == "test1"
    assert result2["input"] == "test2"
```

### Integration Testing

```python
@pytest.fixture
def integration_mcp():
    # Real container with test database
    container = InjectQ()
    container.install(TestDatabaseModule())
    container.install(DocumentModule())
    container.install(AuthModule())

    mcp = FastMCP("Integration Test Server")
    setup_fastmcp_integration(mcp, container)

    return mcp

def test_document_creation_integration(integration_mcp):
    # Define integration tool
    @integration_mcp.tool()
    async def create_test_document(
        title: str,
        content: str,
        doc_service: IDocumentService = InjectQDependency(IDocumentService)
    ):
        document = await doc_service.create_document(title, content)
        return {
            "id": document.id,
            "title": document.title,
            "content_length": len(document.content)
        }

    # Execute tool
    with integration_mcp.test_context():
        result = await integration_mcp.call_tool("create_test_document", {
            "title": "Test Document",
            "content": "This is a test document content."
        })

    # Verify result
    assert result["title"] == "Test Document"
    assert result["content_length"] == len("This is a test document content.")
    assert "id" in result

def test_error_handling_integration(integration_mcp):
    # Define tool that might fail
    @integration_mcp.tool()
    async def risky_tool(
        doc_id: int,
        doc_service: IDocumentService = InjectQDependency(IDocumentService)
    ):
        document = await doc_service.get_document(doc_id)
        if not document:
            raise ValueError("Document not found")
        return {"title": document.title}

    # Test successful case
    with integration_mcp.test_context():
        # First create a document
        create_result = await integration_mcp.call_tool("create_test_document", {
            "title": "Test",
            "content": "Content"
        })

        # Then retrieve it
        result = await integration_mcp.call_tool("risky_tool", {
            "doc_id": create_result["id"]
        })

        assert result["title"] == "Test"

    # Test error case
    with integration_mcp.test_context():
        with pytest.raises(ValueError, match="Document not found"):
            await integration_mcp.call_tool("risky_tool", {"doc_id": 99999})
```

### Mock Testing

```python
class MockDocumentService:
    def __init__(self):
        self.documents = {}
        self.next_id = 1

    async def search_documents(self, query: str, user_id: int, limit: int):
        # Simple mock search
        results = [
            doc for doc in self.documents.values()
            if query.lower() in doc.title.lower() or query.lower() in doc.content.lower()
        ]
        return results[:limit]

    async def create_document(self, title: str, content: str):
        doc_id = self.next_id
        self.next_id += 1

        document = Document(
            id=doc_id,
            title=title,
            content=content,
            user_id=1,  # Mock user
            created_at=datetime.now()
        )

        self.documents[doc_id] = document
        return document

    async def get_document(self, doc_id: int):
        return self.documents.get(doc_id)

class MockUserService:
    def __init__(self):
        self.current_user = User(id=1, name="Test User", email="test@example.com")

    def get_current_user(self):
        return self.current_user

    def get_user(self, user_id: int):
        if user_id == 1:
            return self.current_user
        return None

def test_with_mocks():
    container = InjectQ()
    mock_doc = MockDocumentService()
    mock_user = MockUserService()

    container.bind(IDocumentService, mock_doc)
    container.bind(IUserService, mock_user)

    mcp = FastMCP("Mock Test Server")
    setup_fastmcp_integration(mcp, container)

    @mcp.tool()
    async def test_tool(
        title: str,
        doc_service: IDocumentService = InjectQDependency(IDocumentService)
    ):
        doc = await doc_service.create_document(title, "Test content")
        return {"created_id": doc.id, "documents_count": len(mock_doc.documents)}

    # Execute tool
    with mcp.test_context():
        result = await mcp.call_tool("test_tool", {"title": "Mock Test"})

    # Verify mock interactions
    assert result["created_id"] == 1
    assert result["documents_count"] == 1
    assert len(mock_doc.documents) == 1
```

## 🚨 Common Patterns and Pitfalls

### ✅ Good Patterns

#### 1. Proper Request Scoping

```python
# ✅ Good: Use scoped for request-specific data
@scoped
class RequestContext:
    def __init__(self):
        self.request_id = str(uuid.uuid4())
        self.user = None
        self.metadata = {}

# ✅ Good: Use singleton for shared resources
@singleton
class DatabasePool:
    def __init__(self):
        self.pool = create_database_pool()

# ✅ Good: Use transient for stateless operations
@transient
class DataValidator:
    def validate(self, data: dict) -> bool:
        return validate_schema(data)
```

#### 2. Error Handling

```python
# ✅ Good: Handle tool errors gracefully
@mcp.tool()
async def safe_tool_operation(
    data: dict,
    service: IService = InjectQDependency(IService),
    logger: ILogger = InjectQDependency(ILogger)
):
    try:
        result = await service.process_data(data)
        return result
    except ValidationError as e:
        logger.error(f"Validation failed: {e}")
        return {"error": "Invalid data", "details": str(e)}
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return {"error": "Internal server error"}
```

#### 3. Permission Checking

```python
# ✅ Good: Check permissions before operations
@mcp.tool()
async def secure_document_operation(
    doc_id: int,
    operation: str,
    auth_service: IAuthService = InjectQDependency(IAuthService),
    doc_service: IDocumentService = InjectQDependency(IDocumentService)
):
    # Check permissions first
    if not auth_service.has_permission(f"document.{operation}"):
        raise ValueError(f"Insufficient permissions for {operation}")

    # Perform operation
    if operation == "read":
        return await doc_service.get_document(doc_id)
    elif operation == "update":
        return await doc_service.update_document(doc_id, "New Title", "New Content")
    else:
        raise ValueError(f"Unknown operation: {operation}")
```

### ❌ Bad Patterns

#### 1. Manual Container Access

```python
# ❌ Bad: Manual container access in tools
container = InjectQ()  # Global container

@mcp.tool()
async def manual_tool(user_id: int):
    user_service = container.get(IUserService)  # Manual resolution
    return user_service.get_user(user_id)

# ✅ Good: Use dependency injection
@mcp.tool()
async def injected_tool(
    user_id: int,
    user_service: IUserService = InjectQDependency(IUserService)
):
    return user_service.get_user(user_id)
```

#### 2. Singleton Abuse

```python
# ❌ Bad: Singleton for request-specific state
@singleton
class RequestState:
    def __init__(self):
        self.current_request_data = None  # Shared across requests!

    def set_request_data(self, data):
        self.current_request_data = data  # Overwrites other requests!

# ❌ Bad: Singleton for mutable request data
@singleton
class RequestMetrics:
    def __init__(self):
        self.request_count = 0  # Accumulates across all requests

    def increment_request_count(self):
        self.request_count += 1  # Not request-specific

# ✅ Good: Scoped for request-specific data
@scoped
class RequestState:
    def __init__(self):
        self.request_data = None

@scoped
class RequestMetrics:
    def __init__(self):
        self.operations = []
```

#### 3. Heavy Operations in Tools

```python
# ❌ Bad: Heavy initialization per request
@mcp.tool()
async def heavy_tool(data: dict):
    # Load model on every request
    model = await load_ml_model()  # 2GB model!
    result = model.predict(data)
    return result

# ✅ Good: Pre-load heavy resources
@singleton
class MLModelService:
    def __init__(self):
        self.model = None

    async def initialize(self):
        if self.model is None:
            self.model = await load_ml_model()

    async def predict(self, data: dict):
        await self.initialize()
        return self.model.predict(data)

@mcp.tool()
async def light_tool(
    data: dict,
    ml_service: MLModelService = InjectQDependency(MLModelService)
):
    return await ml_service.predict(data)
```

## ⚡ Advanced Features

### Custom MCP Middleware

```python
from injectq.integrations.fastmcp import FastMCPMiddleware

class MetricsMiddleware(FastMCPMiddleware):
    def __init__(self, metrics_service: IMetricsService):
        self.metrics = metrics_service

    async def before_tool_call(self, tool_name, args):
        # Record tool call start
        self.metrics.increment("tool_calls_started")
        self.metrics.increment(f"tool_{tool_name}_calls")

    async def after_tool_call(self, tool_name, args, result, duration):
        # Record tool call completion
        self.metrics.histogram("tool_call_duration", duration)
        self.metrics.increment("tool_calls_completed")

    async def on_tool_error(self, tool_name, args, error):
        # Record tool call failure
        self.metrics.increment("tool_calls_failed")
        self.metrics.increment(f"tool_error_{type(error).__name__}")

# Use custom middleware
setup_fastmcp_integration(
    mcp,
    container,
    middlewares=[MetricsMiddleware(metrics_service)]
)
```

### Tool Result Caching

```python
@scoped
class ToolCache:
    def __init__(self):
        self.cache = {}

    def get(self, key: str):
        return self.cache.get(key)

    def set(self, key: str, value: Any, ttl: int = 300):
        self.cache[key] = {
            "value": value,
            "expires_at": time.time() + ttl
        }

    def is_expired(self, key: str) -> bool:
        if key not in self.cache:
            return True
        return time.time() > self.cache[key]["expires_at"]

@mcp.tool()
async def cached_search_documents(
    query: str,
    cache: ToolCache = InjectQDependency(ToolCache),
    doc_service: IDocumentService = InjectQDependency(IDocumentService)
):
    """Search documents with caching."""
    cache_key = f"search:{query}"

    # Check cache first
    if not cache.is_expired(cache_key):
        return cache.get(cache_key)["value"]

    # Perform search
    results = await doc_service.search_documents(query, user_id=1, limit=10)

    # Cache results
    cache.set(cache_key, results)

    return results
```

### Tool Composition

```python
@mcp.tool()
async def complex_workflow(
    input_data: dict,
    validator: IDataValidator = InjectQDependency(IDataValidator),
    processor: IDataProcessor = InjectQDependency(IDataProcessor),
    formatter: IDataFormatter = InjectQDependency(IDataFormatter)
):
    """Complex workflow combining multiple services."""
    # Step 1: Validate input
    validation_result = validator.validate(input_data)
    if not validation_result.valid:
        return {"error": "Validation failed", "details": validation_result.errors}

    # Step 2: Process data
    processed_data = await processor.process_data(input_data)

    # Step 3: Format output
    formatted_result = formatter.format_data(processed_data)

    return {
        "success": True,
        "original_input": input_data,
        "processed_data": processed_data,
        "formatted_result": formatted_result
    }

@mcp.tool()
async def batch_operation(
    items: List[dict],
    batch_processor: IBatchProcessor = InjectQDependency(IBatchProcessor)
):
    """Process multiple items in batch."""
    # Process items in parallel
    results = await batch_processor.process_batch(items)

    # Group results
    successful = [r for r in results if r.success]
    failed = [r for r in results if not r.success]

    return {
        "total_items": len(items),
        "successful": len(successful),
        "failed": len(failed),
        "results": results
    }
```

## 🎯 Summary

FastMCP integration provides:

- **Automatic dependency injection** - No manual container management in tools
- **Request-scoped services** - Proper isolation per MCP request
- **Type-driven injection** - Just add type hints to tool parameters
- **Framework lifecycle integration** - Automatic cleanup and resource management
- **Testing support** - Easy mocking and test isolation

**Key features:**
- Seamless integration with FastMCP's tool system
- Support for all InjectQ scopes (singleton, scoped, transient)
- Request-scoped container access
- Custom middleware support
- Tool result caching
- Tool composition patterns

**Best practices:**
- Use scoped services for request-specific data
- Use singleton for shared resources and heavy objects
- Use transient for stateless operations
- Handle errors gracefully in tools
- Check permissions before operations
- Test thoroughly with mocked dependencies
- Avoid manual container access in tools

Congratulations! You've completed the framework integrations section. Ready to explore [testing utilities](testing.md)?
