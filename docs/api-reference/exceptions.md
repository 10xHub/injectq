# Exceptions API

::: injectq.utils.exceptions

## Overview

The exceptions module provides a comprehensive hierarchy of exceptions for dependency injection scenarios, enabling precise error handling and debugging.

## Core Exceptions

### Base Exception

```python
class InjectQException(Exception):
    """Base exception for all InjectQ-related errors."""
    
    def __init__(self, message: str, service_type: Type = None, context: Dict[str, Any] = None):
        super().__init__(message)
        self.service_type = service_type
        self.context = context or {}
        self.timestamp = datetime.now()
    
    def __str__(self):
        base_msg = super().__str__()
        if self.service_type:
            base_msg += f" (Service: {self.service_type.__name__})"
        return base_msg
    
    def get_context_info(self) -> str:
        """Get formatted context information."""
        if not self.context:
            return ""
        
        context_lines = ["Context:"]
        for key, value in self.context.items():
            context_lines.append(f"  {key}: {value}")
        return "\n".join(context_lines)
    
    def get_full_message(self) -> str:
        """Get full error message with context."""
        message = str(self)
        context_info = self.get_context_info()
        if context_info:
            message += f"\n{context_info}"
        return message
```

### Registration Exceptions

```python
class RegistrationException(InjectQException):
    """Base exception for service registration errors."""
    pass

class ServiceAlreadyRegisteredException(RegistrationException):
    """Raised when attempting to register a service that's already registered."""
    
    def __init__(self, service_type: Type, existing_implementation: Any = None):
        message = f"Service {service_type.__name__} is already registered"
        if existing_implementation:
            message += f" with implementation {existing_implementation}"
        
        super().__init__(
            message=message,
            service_type=service_type,
            context={'existing_implementation': existing_implementation}
        )

class InvalidServiceRegistrationException(RegistrationException):
    """Raised when service registration parameters are invalid."""
    
    def __init__(self, service_type: Type, reason: str, invalid_parameter: str = None):
        message = f"Invalid registration for {service_type.__name__}: {reason}"
        
        context = {'reason': reason}
        if invalid_parameter:
            context['invalid_parameter'] = invalid_parameter
        
        super().__init__(
            message=message,
            service_type=service_type,
            context=context
        )

class ServiceNotRegisteredException(RegistrationException):
    """Raised when attempting to access a service that's not registered."""
    
    def __init__(self, service_type: Type, available_services: List[Type] = None):
        message = f"Service {service_type.__name__} is not registered"
        
        context = {}
        if available_services:
            context['available_services'] = [s.__name__ for s in available_services]
            message += f". Available services: {', '.join(context['available_services'])}"
        
        super().__init__(
            message=message,
            service_type=service_type,
            context=context
        )

class DuplicateServiceException(RegistrationException):
    """Raised when multiple services are registered for the same type."""
    
    def __init__(self, service_type: Type, implementations: List[Any]):
        impl_names = [getattr(impl, '__name__', str(impl)) for impl in implementations]
        message = f"Multiple implementations registered for {service_type.__name__}: {', '.join(impl_names)}"
        
        super().__init__(
            message=message,
            service_type=service_type,
            context={'implementations': impl_names}
        )
```

### Resolution Exceptions

```python
class ResolutionException(InjectQException):
    """Base exception for service resolution errors."""
    
    def __init__(self, message: str, service_type: Type = None, resolution_chain: List[Type] = None):
        super().__init__(message, service_type)
        self.resolution_chain = resolution_chain or []
        if resolution_chain:
            self.context['resolution_chain'] = [t.__name__ for t in resolution_chain]

class ServiceResolutionException(ResolutionException):
    """Raised when a service cannot be resolved."""
    
    def __init__(self, service_type: Type, reason: str, resolution_chain: List[Type] = None):
        message = f"Failed to resolve service {service_type.__name__}: {reason}"
        super().__init__(
            message=message,
            service_type=service_type,
            resolution_chain=resolution_chain
        )

class CircularDependencyException(ResolutionException):
    """Raised when a circular dependency is detected during resolution."""
    
    def __init__(self, service_type: Type, dependency_cycle: List[Type]):
        cycle_names = [t.__name__ for t in dependency_cycle]
        cycle_str = " -> ".join(cycle_names + [dependency_cycle[0].__name__])
        message = f"Circular dependency detected for {service_type.__name__}: {cycle_str}"
        
        super().__init__(
            message=message,
            service_type=service_type,
            resolution_chain=dependency_cycle
        )
        self.dependency_cycle = dependency_cycle

class MissingDependencyException(ResolutionException):
    """Raised when a required dependency is not available."""
    
    def __init__(self, service_type: Type, missing_dependency: Type, parameter_name: str = None):
        message = f"Missing dependency {missing_dependency.__name__} for service {service_type.__name__}"
        if parameter_name:
            message += f" (parameter: {parameter_name})"
        
        super().__init__(
            message=message,
            service_type=service_type,
            context={
                'missing_dependency': missing_dependency.__name__,
                'parameter_name': parameter_name
            }
        )
        self.missing_dependency = missing_dependency
        self.parameter_name = parameter_name

class ConstructorException(ResolutionException):
    """Raised when service constructor fails."""
    
    def __init__(self, service_type: Type, original_exception: Exception, parameters: Dict[str, Any] = None):
        message = f"Constructor failed for service {service_type.__name__}: {str(original_exception)}"
        
        context = {'original_exception': str(original_exception)}
        if parameters:
            context['constructor_parameters'] = {k: type(v).__name__ for k, v in parameters.items()}
        
        super().__init__(
            message=message,
            service_type=service_type,
            context=context
        )
        self.original_exception = original_exception
        self.parameters = parameters

class ServiceCreationException(ResolutionException):
    """Raised when service creation fails."""
    
    def __init__(self, service_type: Type, creation_method: str, original_exception: Exception = None):
        message = f"Failed to create service {service_type.__name__} using {creation_method}"
        if original_exception:
            message += f": {str(original_exception)}"
        
        context = {'creation_method': creation_method}
        if original_exception:
            context['original_exception'] = str(original_exception)
        
        super().__init__(
            message=message,
            service_type=service_type,
            context=context
        )
        self.creation_method = creation_method
        self.original_exception = original_exception
```

### Scope Exceptions

```python
class ScopeException(InjectQException):
    """Base exception for scope-related errors."""
    pass

class ScopeNotActiveException(ScopeException):
    """Raised when attempting to use a scope that's not active."""
    
    def __init__(self, scope_name: str, service_type: Type = None):
        message = f"Scope '{scope_name}' is not active"
        if service_type:
            message += f" for service {service_type.__name__}"
        
        super().__init__(
            message=message,
            service_type=service_type,
            context={'scope_name': scope_name}
        )
        self.scope_name = scope_name

class ScopeDisposedException(ScopeException):
    """Raised when attempting to use a disposed scope."""
    
    def __init__(self, scope_name: str, service_type: Type = None):
        message = f"Scope '{scope_name}' has been disposed"
        if service_type:
            message += f" (requested service: {service_type.__name__})"
        
        super().__init__(
            message=message,
            service_type=service_type,
            context={'scope_name': scope_name}
        )
        self.scope_name = scope_name

class InvalidScopeException(ScopeException):
    """Raised when an invalid scope is specified."""
    
    def __init__(self, scope_name: str, valid_scopes: List[str] = None):
        message = f"Invalid scope '{scope_name}'"
        if valid_scopes:
            message += f". Valid scopes: {', '.join(valid_scopes)}"
        
        super().__init__(
            message=message,
            context={'scope_name': scope_name, 'valid_scopes': valid_scopes}
        )
        self.scope_name = scope_name
        self.valid_scopes = valid_scopes

class ScopeLifecycleException(ScopeException):
    """Raised when scope lifecycle operations fail."""
    
    def __init__(self, scope_name: str, operation: str, reason: str):
        message = f"Scope '{scope_name}' {operation} failed: {reason}"
        
        super().__init__(
            message=message,
            context={
                'scope_name': scope_name,
                'operation': operation,
                'reason': reason
            }
        )
        self.scope_name = scope_name
        self.operation = operation
        self.reason = reason
```

### Configuration Exceptions

```python
class ConfigurationException(InjectQException):
    """Base exception for configuration errors."""
    pass

class InvalidConfigurationException(ConfigurationException):
    """Raised when container configuration is invalid."""
    
    def __init__(self, config_key: str, config_value: Any, reason: str):
        message = f"Invalid configuration for '{config_key}': {reason}"
        
        super().__init__(
            message=message,
            context={
                'config_key': config_key,
                'config_value': str(config_value),
                'reason': reason
            }
        )
        self.config_key = config_key
        self.config_value = config_value
        self.reason = reason

class ModuleLoadException(ConfigurationException):
    """Raised when a module fails to load."""
    
    def __init__(self, module_name: str, original_exception: Exception):
        message = f"Failed to load module '{module_name}': {str(original_exception)}"
        
        super().__init__(
            message=message,
            context={
                'module_name': module_name,
                'original_exception': str(original_exception)
            }
        )
        self.module_name = module_name
        self.original_exception = original_exception

class ContainerLockedException(ConfigurationException):
    """Raised when attempting to modify a locked container."""
    
    def __init__(self, operation: str):
        message = f"Cannot perform '{operation}' on locked container"
        
        super().__init__(
            message=message,
            context={'operation': operation}
        )
        self.operation = operation
```

### Validation Exceptions

```python
class ValidationException(InjectQException):
    """Base exception for validation errors."""
    pass

class TypeValidationException(ValidationException):
    """Raised when type validation fails."""
    
    def __init__(self, expected_type: Type, actual_type: Type, parameter_name: str = None):
        message = f"Type validation failed: expected {expected_type.__name__}, got {actual_type.__name__}"
        if parameter_name:
            message += f" for parameter '{parameter_name}'"
        
        super().__init__(
            message=message,
            context={
                'expected_type': expected_type.__name__,
                'actual_type': actual_type.__name__,
                'parameter_name': parameter_name
            }
        )
        self.expected_type = expected_type
        self.actual_type = actual_type
        self.parameter_name = parameter_name

class ContainerValidationException(ValidationException):
    """Raised when container validation fails."""
    
    def __init__(self, validation_errors: List[str]):
        message = f"Container validation failed with {len(validation_errors)} error(s)"
        
        super().__init__(
            message=message,
            context={'validation_errors': validation_errors}
        )
        self.validation_errors = validation_errors
    
    def __str__(self):
        base_msg = super().__str__()
        if self.validation_errors:
            error_list = "\n".join(f"  - {error}" for error in self.validation_errors)
            base_msg += f"\nValidation errors:\n{error_list}"
        return base_msg
```

### Integration Exceptions

```python
class IntegrationException(InjectQException):
    """Base exception for framework integration errors."""
    pass

class FrameworkIntegrationException(IntegrationException):
    """Raised when framework integration fails."""
    
    def __init__(self, framework_name: str, reason: str, component: str = None):
        message = f"{framework_name} integration failed: {reason}"
        if component:
            message += f" (component: {component})"
        
        super().__init__(
            message=message,
            context={
                'framework_name': framework_name,
                'reason': reason,
                'component': component
            }
        )
        self.framework_name = framework_name
        self.reason = reason
        self.component = component

class MiddlewareException(IntegrationException):
    """Raised when middleware integration fails."""
    
    def __init__(self, middleware_name: str, operation: str, original_exception: Exception = None):
        message = f"Middleware '{middleware_name}' {operation} failed"
        if original_exception:
            message += f": {str(original_exception)}"
        
        context = {
            'middleware_name': middleware_name,
            'operation': operation
        }
        if original_exception:
            context['original_exception'] = str(original_exception)
        
        super().__init__(
            message=message,
            context=context
        )
        self.middleware_name = middleware_name
        self.operation = operation
        self.original_exception = original_exception
```

## Exception Utilities

### Exception Handler

```python
from typing import Callable, Type, Dict, List
import logging
import traceback

class ExceptionHandler:
    """Centralized exception handling for InjectQ."""
    
    def __init__(self, logger: logging.Logger = None):
        self.logger = logger or logging.getLogger(__name__)
        self._handlers: Dict[Type[Exception], List[Callable]] = {}
        self._global_handlers: List[Callable] = []
    
    def register_handler(self, exception_type: Type[Exception], handler: Callable[[Exception], None]):
        """Register a handler for a specific exception type."""
        if exception_type not in self._handlers:
            self._handlers[exception_type] = []
        self._handlers[exception_type].append(handler)
    
    def register_global_handler(self, handler: Callable[[Exception], None]):
        """Register a global exception handler."""
        self._global_handlers.append(handler)
    
    def handle_exception(self, exception: Exception, context: Dict[str, Any] = None) -> bool:
        """Handle an exception using registered handlers."""
        handled = False
        
        # Try specific handlers first
        for exc_type, handlers in self._handlers.items():
            if isinstance(exception, exc_type):
                for handler in handlers:
                    try:
                        handler(exception)
                        handled = True
                    except Exception as handler_exc:
                        self.logger.error(f"Exception handler failed: {handler_exc}")
        
        # Try global handlers
        if not handled:
            for handler in self._global_handlers:
                try:
                    handler(exception)
                    handled = True
                except Exception as handler_exc:
                    self.logger.error(f"Global exception handler failed: {handler_exc}")
        
        # Default logging if not handled
        if not handled:
            self._log_exception(exception, context)
        
        return handled
    
    def _log_exception(self, exception: Exception, context: Dict[str, Any] = None):
        """Log exception with context information."""
        error_msg = f"Unhandled InjectQ exception: {exception}"
        
        if isinstance(exception, InjectQException):
            error_msg = exception.get_full_message()
        
        if context:
            error_msg += f"\nAdditional context: {context}"
        
        self.logger.error(error_msg, exc_info=True)

# Default exception handlers
def log_registration_errors(exception: RegistrationException):
    """Default handler for registration errors."""
    logging.getLogger('injectq.registration').error(
        f"Registration error: {exception.get_full_message()}"
    )

def log_resolution_errors(exception: ResolutionException):
    """Default handler for resolution errors."""
    logger = logging.getLogger('injectq.resolution')
    
    if isinstance(exception, CircularDependencyException):
        logger.error(f"Circular dependency detected: {exception.dependency_cycle}")
    else:
        logger.error(f"Resolution error: {exception.get_full_message()}")

def log_scope_errors(exception: ScopeException):
    """Default handler for scope errors."""
    logging.getLogger('injectq.scope').warning(
        f"Scope error: {exception.get_full_message()}"
    )

# Setup default handlers
default_handler = ExceptionHandler()
default_handler.register_handler(RegistrationException, log_registration_errors)
default_handler.register_handler(ResolutionException, log_resolution_errors)
default_handler.register_handler(ScopeException, log_scope_errors)
```

### Exception Context Manager

```python
from contextlib import contextmanager
from typing import Generator, Optional, Callable

@contextmanager
def handle_injectq_exceptions(
    handler: ExceptionHandler = None,
    reraise: bool = True,
    fallback_value: Any = None,
    custom_handler: Callable[[Exception], Any] = None
) -> Generator[None, None, None]:
    """Context manager for handling InjectQ exceptions."""
    
    exception_handler = handler or default_handler
    
    try:
        yield
    except InjectQException as e:
        # Handle with registered handlers
        handled = exception_handler.handle_exception(e)
        
        # Custom handler
        if custom_handler:
            try:
                result = custom_handler(e)
                if result is not None:
                    return result
            except Exception as handler_exc:
                logging.getLogger(__name__).error(f"Custom handler failed: {handler_exc}")
        
        # Reraise or return fallback
        if reraise:
            raise
        else:
            return fallback_value
    except Exception as e:
        # Wrap non-InjectQ exceptions
        wrapped = InjectQException(f"Unexpected error: {str(e)}")
        wrapped.__cause__ = e
        
        exception_handler.handle_exception(wrapped)
        
        if reraise:
            raise wrapped
        else:
            return fallback_value

# Usage examples
def safe_service_resolution(container: Container, service_type: Type[T]) -> Optional[T]:
    """Safely resolve a service, returning None on error."""
    
    with handle_injectq_exceptions(reraise=False, fallback_value=None):
        return container.resolve(service_type)

def resolve_with_fallback(container: Container, service_type: Type[T], fallback: T) -> T:
    """Resolve a service with a fallback value."""
    
    def fallback_handler(exc: Exception) -> T:
        logging.getLogger(__name__).warning(f"Using fallback for {service_type.__name__}: {exc}")
        return fallback
    
    with handle_injectq_exceptions(reraise=False, custom_handler=fallback_handler):
        return container.resolve(service_type)
```

### Exception Diagnostics

```python
class ExceptionDiagnostics:
    """Provides diagnostic information for InjectQ exceptions."""
    
    @staticmethod
    def analyze_exception(exception: InjectQException) -> Dict[str, Any]:
        """Analyze an exception and provide diagnostic information."""
        analysis = {
            'exception_type': type(exception).__name__,
            'message': str(exception),
            'service_type': exception.service_type.__name__ if exception.service_type else None,
            'context': exception.context,
            'timestamp': exception.timestamp,
            'suggestions': []
        }
        
        # Add type-specific analysis
        if isinstance(exception, ServiceNotRegisteredException):
            analysis['suggestions'] = [
                f"Register {exception.service_type.__name__} with container.register()",
                "Check if the service is registered in a different scope",
                "Verify the service type is spelled correctly"
            ]
        
        elif isinstance(exception, CircularDependencyException):
            analysis['dependency_cycle'] = [t.__name__ for t in exception.dependency_cycle]
            analysis['suggestions'] = [
                "Break the circular dependency by using interfaces",
                "Consider using factory patterns",
                "Refactor services to reduce coupling"
            ]
        
        elif isinstance(exception, MissingDependencyException):
            analysis['missing_dependency'] = exception.missing_dependency.__name__
            analysis['suggestions'] = [
                f"Register {exception.missing_dependency.__name__} with the container",
                "Make the dependency optional if it's not required",
                "Check if the dependency is registered with a different name"
            ]
        
        elif isinstance(exception, TypeValidationException):
            analysis['type_mismatch'] = {
                'expected': exception.expected_type.__name__,
                'actual': exception.actual_type.__name__
            }
            analysis['suggestions'] = [
                "Check that the registered implementation matches the service interface",
                "Verify type annotations are correct",
                "Consider using duck typing if appropriate"
            ]
        
        return analysis
    
    @staticmethod
    def print_exception_analysis(exception: InjectQException):
        """Print formatted exception analysis."""
        analysis = ExceptionDiagnostics.analyze_exception(exception)
        
        print(f"InjectQ Exception Analysis")
        print(f"=" * 50)
        print(f"Exception Type: {analysis['exception_type']}")
        print(f"Message: {analysis['message']}")
        
        if analysis['service_type']:
            print(f"Service Type: {analysis['service_type']}")
        
        if analysis['context']:
            print(f"Context:")
            for key, value in analysis['context'].items():
                print(f"  {key}: {value}")
        
        if 'dependency_cycle' in analysis:
            cycle = " -> ".join(analysis['dependency_cycle'])
            print(f"Dependency Cycle: {cycle}")
        
        if analysis['suggestions']:
            print(f"\nSuggestions:")
            for suggestion in analysis['suggestions']:
                print(f"  • {suggestion}")
        
        print(f"\nTimestamp: {analysis['timestamp']}")

# Usage
try:
    container.resolve(UnregisteredService)
except InjectQException as e:
    ExceptionDiagnostics.print_exception_analysis(e)
```
