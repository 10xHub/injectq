# Integrations API

::: injectq.integrations

## Overview

The integrations module provides seamless integration with popular Python frameworks and libraries, enabling easy adoption of dependency injection in existing applications.

## FastAPI Integration

### Basic Integration

```python
from fastapi import FastAPI
from injectq.integrations.fastapi import InjectQDependency, setup_injectq
from injectq import Container, inject

# Create FastAPI app and InjectQ container
app = FastAPI()
container = Container()

# Register services
container.register(UserRepository, DatabaseUserRepository)
container.register(EmailService, SMTPEmailService)

# Setup InjectQ with FastAPI
setup_injectq(app, container)

# Use dependency injection in endpoints
@app.get("/users/{user_id}")
@inject
async def get_user(user_id: int, user_service: UserService = InjectQDependency()):
    return await user_service.get_user(user_id)

@app.post("/users")
@inject
async def create_user(user_data: UserCreateModel, user_service: UserService = InjectQDependency()):
    return await user_service.create_user(user_data)
```

### FastAPI Dependency Provider

```python
from typing import Type, TypeVar, Any, Callable
from fastapi import Depends, Request
from fastapi.dependencies.utils import get_typed_signature

T = TypeVar('T')

class InjectQDependency:
    """FastAPI dependency that resolves services from InjectQ container."""
    
    def __init__(self, service_type: Type[T] = None):
        self.service_type = service_type
    
    def __call__(self, request: Request) -> Any:
        """Resolve service from container."""
        container = getattr(request.app.state, 'injectq_container', None)
        if not container:
            raise RuntimeError("InjectQ container not configured. Call setup_injectq() first.")
        
        if self.service_type:
            return container.resolve(self.service_type)
        else:
            # Auto-detect service type from function parameter annotation
            frame = inspect.currentframe()
            if frame and frame.f_back:
                local_vars = frame.f_back.f_locals
                # This is a simplified approach - real implementation would be more robust
                for var_name, var_value in local_vars.items():
                    if isinstance(var_value, type):
                        return container.resolve(var_value)
            
            raise ValueError("Could not determine service type for injection")

def setup_injectq(app: FastAPI, container: Container):
    """Setup InjectQ integration with FastAPI."""
    app.state.injectq_container = container
    
    # Add middleware for scope management
    @app.middleware("http")
    async def injectq_scope_middleware(request: Request, call_next):
        # Create request scope
        with container.create_scope() as scope:
            request.state.injectq_scope = scope
            response = await call_next(request)
            return response
    
    return app

# Alternative dependency function
def get_service(service_type: Type[T]) -> Callable[[Request], T]:
    """Create FastAPI dependency function for a service type."""
    def dependency(request: Request) -> T:
        container = request.app.state.injectq_container
        return container.resolve(service_type)
    
    return dependency

# Usage with get_service
@app.get("/users/{user_id}")
async def get_user_alt(
    user_id: int,
    user_service: UserService = Depends(get_service(UserService))
):
    return await user_service.get_user(user_id)
```

### Scoped Services in FastAPI

```python
from contextlib import asynccontextmanager

class FastAPIScope:
    """FastAPI-specific scope implementation."""
    
    def __init__(self, container: Container):
        self.container = container
        self._request_instances: Dict[Type, Any] = {}
    
    def get_instance(self, service_type: Type[T]) -> T:
        """Get or create scoped instance for request."""
        if service_type not in self._request_instances:
            self._request_instances[service_type] = self.container.resolve(service_type)
        return self._request_instances[service_type]
    
    def dispose(self):
        """Dispose all request-scoped instances."""
        for instance in self._request_instances.values():
            if hasattr(instance, 'dispose'):
                instance.dispose()
        self._request_instances.clear()

@asynccontextmanager
async def request_scope_lifespan(app: FastAPI):
    """Lifespan context manager for request scopes."""
    # Startup
    yield
    # Shutdown - cleanup handled by middleware

def setup_request_scoping(app: FastAPI, container: Container):
    """Setup request-scoped services."""
    
    @app.middleware("http")
    async def request_scope_middleware(request: Request, call_next):
        scope = FastAPIScope(container)
        request.state.service_scope = scope
        
        try:
            response = await call_next(request)
            return response
        finally:
            scope.dispose()
    
    # Modify dependency to use request scope
    def get_scoped_service(service_type: Type[T]) -> Callable[[Request], T]:
        def dependency(request: Request) -> T:
            scope = getattr(request.state, 'service_scope', None)
            if scope:
                return scope.get_instance(service_type)
            else:
                # Fallback to container
                container = request.app.state.injectq_container
                return container.resolve(service_type)
        
        return dependency
    
    return get_scoped_service
```

## Django Integration

### Django App Configuration

```python
# settings.py
INSTALLED_APPS = [
    # ... other apps
    'injectq.integrations.django',
]

INJECTQ_SETTINGS = {
    'CONTAINER_MODULE': 'myproject.container',
    'AUTO_DISCOVER': True,
    'SCOPE_PER_REQUEST': True,
}

# container.py
from injectq import Container
from myproject.services import UserService, EmailService
from myproject.repositories import UserRepository

def create_container() -> Container:
    """Create and configure application container."""
    container = Container()
    
    # Register services
    container.register(UserRepository, DatabaseUserRepository)
    container.register(EmailService, DjangoEmailService)
    container.register(UserService, UserService)
    
    return container

# Global container instance
container = create_container()
```

### Django Views Integration

```python
from django.http import JsonResponse
from django.views import View
from injectq.integrations.django import inject_view, get_service
from injectq import inject

class UserListView(View):
    """Django view with dependency injection."""
    
    @inject_view
    @inject
    def get(self, request, user_service: UserService):
        """Get list of users."""
        users = user_service.get_all_users()
        return JsonResponse({
            'users': [{'id': u.id, 'email': u.email} for u in users]
        })
    
    @inject_view
    @inject
    def post(self, request, user_service: UserService):
        """Create new user."""
        import json
        data = json.loads(request.body)
        user = user_service.create_user(data['email'])
        return JsonResponse({'id': user.id, 'email': user.email})

# Function-based view
@inject_view
@inject
def user_detail(request, user_id: int, user_service: UserService):
    """Get user details."""
    user = user_service.get_user(user_id)
    if user:
        return JsonResponse({'id': user.id, 'email': user.email})
    else:
        return JsonResponse({'error': 'User not found'}, status=404)

# Alternative using explicit service resolution
def user_detail_alt(request, user_id: int):
    """Get user details with explicit service resolution."""
    user_service = get_service(UserService)
    user = user_service.get_user(user_id)
    if user:
        return JsonResponse({'id': user.id, 'email': user.email})
    else:
        return JsonResponse({'error': 'User not found'}, status=404)
```

### Django Middleware

```python
from django.utils.deprecation import MiddlewareMixin
from injectq.integrations.django import get_container

class InjectQMiddleware(MiddlewareMixin):
    """Middleware for managing InjectQ scopes per request."""
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.container = get_container()
        super().__init__(get_response)
    
    def process_request(self, request):
        """Create request scope."""
        request.injectq_scope = self.container.create_scope()
        return None
    
    def process_response(self, request, response):
        """Dispose request scope."""
        scope = getattr(request, 'injectq_scope', None)
        if scope:
            scope.dispose()
        return response

# Django App Config
from django.apps import AppConfig

class InjectQConfig(AppConfig):
    """Django app configuration for InjectQ."""
    
    name = 'injectq.integrations.django'
    verbose_name = 'InjectQ Django Integration'
    
    def ready(self):
        """Initialize InjectQ when Django starts."""
        from django.conf import settings
        from . import setup_django_integration
        
        injectq_settings = getattr(settings, 'INJECTQ_SETTINGS', {})
        setup_django_integration(injectq_settings)

def setup_django_integration(settings: dict):
    """Setup Django integration."""
    container_module = settings.get('CONTAINER_MODULE')
    if container_module:
        # Import and initialize container
        module = __import__(container_module, fromlist=['container'])
        container = getattr(module, 'container')
        
        # Store globally
        _set_global_container(container)
    
    if settings.get('AUTO_DISCOVER', True):
        # Auto-discover and register Django models, etc.
        autodiscover_services()

def autodiscover_services():
    """Auto-discover Django services."""
    from django.apps import apps
    
    for app_config in apps.get_app_configs():
        try:
            # Look for services.py in each app
            services_module = f"{app_config.name}.services"
            __import__(services_module)
        except ImportError:
            pass
```

## Flask Integration

### Flask Application Factory

```python
from flask import Flask, request, g
from injectq import Container
from injectq.integrations.flask import setup_injectq, inject_route

def create_app(config=None) -> Flask:
    """Create Flask application with InjectQ."""
    app = Flask(__name__)
    
    if config:
        app.config.from_object(config)
    
    # Create container
    container = Container()
    setup_container(container)
    
    # Setup InjectQ
    setup_injectq(app, container)
    
    # Register blueprints
    from .views import user_bp
    app.register_blueprint(user_bp)
    
    return app

def setup_container(container: Container):
    """Configure application container."""
    container.register(UserRepository, DatabaseUserRepository)
    container.register(EmailService, FlaskEmailService)
    container.register(UserService, UserService)

# views.py
from flask import Blueprint, jsonify, request
from injectq.integrations.flask import inject_route
from injectq import inject

user_bp = Blueprint('users', __name__, url_prefix='/users')

@user_bp.route('/', methods=['GET'])
@inject_route
@inject
def get_users(user_service: UserService):
    """Get all users."""
    users = user_service.get_all_users()
    return jsonify([{'id': u.id, 'email': u.email} for u in users])

@user_bp.route('/', methods=['POST'])
@inject_route
@inject
def create_user(user_service: UserService):
    """Create new user."""
    data = request.get_json()
    user = user_service.create_user(data['email'])
    return jsonify({'id': user.id, 'email': user.email}), 201

@user_bp.route('/<int:user_id>')
@inject_route
@inject
def get_user(user_id: int, user_service: UserService):
    """Get specific user."""
    user = user_service.get_user(user_id)
    if user:
        return jsonify({'id': user.id, 'email': user.email})
    else:
        return jsonify({'error': 'User not found'}), 404
```

### Flask Extension

```python
from flask import Flask, g, request
from typing import Optional

class InjectQ:
    """Flask extension for InjectQ integration."""
    
    def __init__(self, app: Optional[Flask] = None, container: Optional[Container] = None):
        self.container = container
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app: Flask):
        """Initialize extension with Flask app."""
        if not hasattr(app, 'extensions'):
            app.extensions = {}
        
        app.extensions['injectq'] = self
        
        # Store container in app config
        if self.container:
            app.config['INJECTQ_CONTAINER'] = self.container
        
        # Setup request hooks
        app.before_request(self._before_request)
        app.teardown_request(self._teardown_request)
    
    def _before_request(self):
        """Create request scope before handling request."""
        container = current_app.config.get('INJECTQ_CONTAINER')
        if container:
            g.injectq_scope = container.create_scope()
    
    def _teardown_request(self, exception):
        """Dispose request scope after handling request."""
        scope = getattr(g, 'injectq_scope', None)
        if scope:
            scope.dispose()

def get_service(service_type: Type[T]) -> T:
    """Get service instance from current request scope."""
    container = current_app.config.get('INJECTQ_CONTAINER')
    if not container:
        raise RuntimeError("InjectQ not configured")
    
    scope = getattr(g, 'injectq_scope', None)
    if scope:
        return scope.resolve(service_type)
    else:
        return container.resolve(service_type)

def inject_route(func):
    """Decorator for injecting dependencies into Flask routes."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        container = current_app.config.get('INJECTQ_CONTAINER')
        if container:
            return container.resolve(func, *args, **kwargs)
        else:
            return func(*args, **kwargs)
    
    return wrapper

# Usage
app = Flask(__name__)
container = Container()
# ... configure container

injectq = InjectQ(app, container)

@app.route('/test')
@inject_route
@inject
def test_route(user_service: UserService):
    return jsonify({'message': 'Hello from injected service!'})
```

## Celery Integration

### Celery Task Injection

```python
from celery import Celery
from injectq import Container, inject
from injectq.integrations.celery import setup_celery_injection

# Create Celery app
celery_app = Celery('myapp')

# Create container
container = Container()
container.register(EmailService, SMTPEmailService)
container.register(UserRepository, DatabaseUserRepository)

# Setup injection
setup_celery_injection(celery_app, container)

# Define tasks with injection
@celery_app.task
@inject
def send_welcome_email(user_id: int, email_service: EmailService, user_repository: UserRepository):
    """Send welcome email task."""
    user = user_repository.get_user(user_id)
    if user:
        email_service.send_welcome_email(user.email)
        return f"Welcome email sent to {user.email}"
    else:
        return f"User {user_id} not found"

@celery_app.task
@inject
def cleanup_expired_data(data_service: DataService):
    """Cleanup expired data task."""
    deleted_count = data_service.cleanup_expired()
    return f"Deleted {deleted_count} expired records"

# Task with custom scope
@celery_app.task
@inject(scope='task')
def process_large_dataset(dataset_id: int, processor: DataProcessor):
    """Process large dataset with task-scoped dependencies."""
    return processor.process_dataset(dataset_id)
```

### Celery Integration Setup

```python
from celery.signals import task_prerun, task_postrun
from celery import Task

class InjectQTask(Task):
    """Custom Celery task class with InjectQ support."""
    
    def __init__(self):
        self.container = None
        self.scope = None
    
    def apply_async(self, args=None, kwargs=None, **options):
        """Override to setup injection context."""
        # Inject dependencies before task execution
        return super().apply_async(args, kwargs, **options)
    
    def __call__(self, *args, **kwargs):
        """Execute task with dependency injection."""
        if self.container:
            with self.container.create_scope() as scope:
                self.scope = scope
                try:
                    return self.run(*args, **kwargs)
                finally:
                    self.scope = None
        else:
            return self.run(*args, **kwargs)

def setup_celery_injection(celery_app: Celery, container: Container):
    """Setup Celery integration with InjectQ."""
    
    # Set custom task class
    celery_app.Task = InjectQTask
    
    # Store container reference
    celery_app.container = container
    
    @task_prerun.connect
    def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **kwds):
        """Setup task context before execution."""
        if hasattr(task, 'container') and task.container:
            task.scope = task.container.create_scope()
    
    @task_postrun.connect
    def task_postrun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, retval=None, state=None, **kwds):
        """Cleanup task context after execution."""
        if hasattr(task, 'scope') and task.scope:
            task.scope.dispose()
            task.scope = None
    
    # Configure all tasks to use container
    for task_name, task in celery_app.tasks.items():
        if hasattr(task, '__class__') and issubclass(task.__class__, InjectQTask):
            task.container = container

# Custom task decorator with scope support
def task_with_injection(celery_app: Celery, scope: str = 'task'):
    """Create task decorator with specific injection scope."""
    
    def decorator(func):
        @celery_app.task(bind=True, base=InjectQTask)
        @inject
        def wrapper(self, *args, **kwargs):
            return func(*args, **kwargs)
        
        # Configure task container
        wrapper.container = celery_app.container
        return wrapper
    
    return decorator
```

## SQLAlchemy Integration

### Session Management

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from injectq import Container, Scope
from injectq.integrations.sqlalchemy import SQLAlchemyScope

# Database setup
engine = create_engine('sqlite:///example.db')
SessionLocal = sessionmaker(bind=engine)

def create_database_container() -> Container:
    """Create container with SQLAlchemy integration."""
    container = Container()
    
    # Register session factory
    container.register(
        Session,
        lambda: SessionLocal(),
        scope=Scope.SCOPED  # Session per scope
    )
    
    # Register repositories with session injection
    container.register(UserRepository, SQLAlchemyUserRepository)
    container.register(OrderRepository, SQLAlchemyOrderRepository)
    
    return container

class SQLAlchemyUserRepository:
    """Repository using SQLAlchemy session."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def get_user(self, user_id: int) -> Optional[User]:
        return self.session.query(User).filter(User.id == user_id).first()
    
    def create_user(self, email: str) -> User:
        user = User(email=email)
        self.session.add(user)
        self.session.commit()
        return user
    
    def __del__(self):
        """Cleanup session."""
        if hasattr(self, 'session'):
            self.session.close()

# Usage with automatic session management
container = create_database_container()

@inject
def create_user_service(email: str, user_repo: UserRepository) -> User:
    # Session is automatically managed within this scope
    return user_repo.create_user(email)

# With explicit scope management
with container.create_scope() as scope:
    user_service = scope.resolve(UserService)
    user = user_service.create_user("test@example.com")
    # Session is automatically committed and closed when scope ends
```

### Transaction Management

```python
from contextlib import contextmanager
from sqlalchemy.orm import Session

class TransactionalScope:
    """Scope with transaction management."""
    
    def __init__(self, container: Container, session: Session):
        self.container = container
        self.session = session
        self.in_transaction = False
    
    @contextmanager
    def transaction(self):
        """Context manager for database transactions."""
        if self.in_transaction:
            # Nested transaction - use savepoint
            savepoint = self.session.begin_nested()
            try:
                yield self.session
                savepoint.commit()
            except Exception:
                savepoint.rollback()
                raise
        else:
            # Main transaction
            self.in_transaction = True
            transaction = self.session.begin()
            try:
                yield self.session
                transaction.commit()
            except Exception:
                transaction.rollback()
                raise
            finally:
                self.in_transaction = False
    
    def resolve(self, service_type: Type[T]) -> T:
        """Resolve service with transactional session."""
        return self.container.resolve(service_type)

# Usage
@inject
def transfer_funds(from_user_id: int, to_user_id: int, amount: float, 
                  user_repo: UserRepository, account_repo: AccountRepository):
    """Transfer funds between users."""
    
    # Get current scope
    scope = get_current_scope()  # Implementation specific
    
    with scope.transaction():
        from_account = account_repo.get_by_user_id(from_user_id)
        to_account = account_repo.get_by_user_id(to_user_id)
        
        if from_account.balance < amount:
            raise ValueError("Insufficient funds")
        
        from_account.balance -= amount
        to_account.balance += amount
        
        account_repo.update(from_account)
        account_repo.update(to_account)
        
        # Transaction committed automatically when context exits
```
