# Types API

::: injectq.utils.types

## Overview

The types module provides comprehensive type utilities for working with dependency injection, including type analysis, generic handling, and runtime type checking.

## Type Analysis

### Basic Type Utilities

```python
from typing import Type, TypeVar, Union, Optional, Any, get_origin, get_args
import inspect

T = TypeVar('T')

class TypeAnalyzer:
    """Utility class for analyzing types in dependency injection context."""
    
    @staticmethod
    def is_generic_type(type_hint: Type) -> bool:
        """Check if a type is a generic type."""
        return get_origin(type_hint) is not None
    
    @staticmethod
    def get_generic_origin(type_hint: Type) -> Optional[Type]:
        """Get the origin of a generic type."""
        return get_origin(type_hint)
    
    @staticmethod
    def get_generic_args(type_hint: Type) -> tuple:
        """Get the arguments of a generic type."""
        return get_args(type_hint)
    
    @staticmethod
    def is_optional_type(type_hint: Type) -> bool:
        """Check if a type is Optional (Union with None)."""
        origin = get_origin(type_hint)
        if origin is Union:
            args = get_args(type_hint)
            return len(args) == 2 and type(None) in args
        return False
    
    @staticmethod
    def get_optional_inner_type(type_hint: Type) -> Optional[Type]:
        """Get the inner type of an Optional type."""
        if TypeAnalyzer.is_optional_type(type_hint):
            args = get_args(type_hint)
            return next(arg for arg in args if arg is not type(None))
        return None
    
    @staticmethod
    def is_collection_type(type_hint: Type) -> bool:
        """Check if a type is a collection type."""
        origin = get_origin(type_hint)
        collection_origins = (list, tuple, set, frozenset, dict)
        return origin in collection_origins
    
    @staticmethod
    def is_callable_type(type_hint: Type) -> bool:
        """Check if a type is a callable type."""
        from collections.abc import Callable
        origin = get_origin(type_hint)
        return origin is Callable or origin is callable
    
    @staticmethod
    def extract_type_from_annotation(annotation: Any) -> Optional[Type]:
        """Extract concrete type from type annotation."""
        if annotation == inspect.Parameter.empty:
            return None
        
        # Handle string annotations (forward references)
        if isinstance(annotation, str):
            # This would need proper evaluation context
            return annotation
        
        # Handle Optional types
        if TypeAnalyzer.is_optional_type(annotation):
            return TypeAnalyzer.get_optional_inner_type(annotation)
        
        # Handle generic types
        if TypeAnalyzer.is_generic_type(annotation):
            return TypeAnalyzer.get_generic_origin(annotation)
        
        return annotation

# Usage examples
analyzer = TypeAnalyzer()

# Check generic types
print(analyzer.is_generic_type(List[str]))  # True
print(analyzer.is_generic_type(str))        # False

# Extract type information
print(analyzer.get_generic_origin(List[str]))  # <class 'list'>
print(analyzer.get_generic_args(Dict[str, int]))  # (<class 'str'>, <class 'int'>)

# Check optional types
print(analyzer.is_optional_type(Optional[str]))  # True
print(analyzer.get_optional_inner_type(Optional[str]))  # <class 'str'>
```

### Service Type Metadata

```python
from dataclasses import dataclass
from typing import Dict, List, Any

@dataclass
class ServiceTypeInfo:
    """Metadata about a service type."""
    service_type: Type
    is_abstract: bool
    is_generic: bool
    dependencies: List['DependencyInfo']
    methods: List['MethodInfo']
    properties: List['PropertyInfo']
    interfaces: List[Type]
    base_classes: List[Type]
    
    def __str__(self):
        return f"ServiceTypeInfo({self.service_type.__name__})"

@dataclass
class DependencyInfo:
    """Information about a service dependency."""
    name: str
    type_hint: Type
    is_optional: bool
    default_value: Any
    injection_token: Optional[str] = None
    
    def __str__(self):
        optional = "?" if self.is_optional else ""
        return f"{self.name}: {self.type_hint.__name__}{optional}"

@dataclass
class MethodInfo:
    """Information about a service method."""
    name: str
    parameters: List[DependencyInfo]
    return_type: Optional[Type]
    is_async: bool
    is_property: bool
    
    def __str__(self):
        async_marker = "async " if self.is_async else ""
        return f"{async_marker}{self.name}({', '.join(str(p) for p in self.parameters)})"

@dataclass
class PropertyInfo:
    """Information about a service property."""
    name: str
    type_hint: Type
    is_readonly: bool
    has_setter: bool
    
    def __str__(self):
        readonly = " (readonly)" if self.is_readonly else ""
        return f"{self.name}: {self.type_hint.__name__}{readonly}"

class ServiceIntrospector:
    """Introspects service types to extract metadata."""
    
    def __init__(self):
        self._cache: Dict[Type, ServiceTypeInfo] = {}
    
    def analyze_service(self, service_type: Type) -> ServiceTypeInfo:
        """Analyze a service type and return metadata."""
        if service_type in self._cache:
            return self._cache[service_type]
        
        info = ServiceTypeInfo(
            service_type=service_type,
            is_abstract=self._is_abstract_class(service_type),
            is_generic=TypeAnalyzer.is_generic_type(service_type),
            dependencies=self._extract_dependencies(service_type),
            methods=self._extract_methods(service_type),
            properties=self._extract_properties(service_type),
            interfaces=self._extract_interfaces(service_type),
            base_classes=self._extract_base_classes(service_type)
        )
        
        self._cache[service_type] = info
        return info
    
    def _is_abstract_class(self, service_type: Type) -> bool:
        """Check if a type is an abstract class."""
        return inspect.isabstract(service_type)
    
    def _extract_dependencies(self, service_type: Type) -> List[DependencyInfo]:
        """Extract constructor dependencies."""
        dependencies = []
        
        if hasattr(service_type, '__init__'):
            sig = inspect.signature(service_type.__init__)
            
            for param_name, param in sig.parameters.items():
                if param_name == 'self':
                    continue
                
                dep_info = DependencyInfo(
                    name=param_name,
                    type_hint=TypeAnalyzer.extract_type_from_annotation(param.annotation),
                    is_optional=param.default != inspect.Parameter.empty or TypeAnalyzer.is_optional_type(param.annotation),
                    default_value=param.default if param.default != inspect.Parameter.empty else None
                )
                dependencies.append(dep_info)
        
        return dependencies
    
    def _extract_methods(self, service_type: Type) -> List[MethodInfo]:
        """Extract method information."""
        methods = []
        
        for name, method in inspect.getmembers(service_type, inspect.isfunction):
            if name.startswith('_'):
                continue
            
            sig = inspect.signature(method)
            parameters = []
            
            for param_name, param in sig.parameters.items():
                if param_name == 'self':
                    continue
                
                param_info = DependencyInfo(
                    name=param_name,
                    type_hint=TypeAnalyzer.extract_type_from_annotation(param.annotation),
                    is_optional=param.default != inspect.Parameter.empty,
                    default_value=param.default if param.default != inspect.Parameter.empty else None
                )
                parameters.append(param_info)
            
            method_info = MethodInfo(
                name=name,
                parameters=parameters,
                return_type=TypeAnalyzer.extract_type_from_annotation(sig.return_annotation),
                is_async=inspect.iscoroutinefunction(method),
                is_property=isinstance(getattr(service_type, name, None), property)
            )
            methods.append(method_info)
        
        return methods
    
    def _extract_properties(self, service_type: Type) -> List[PropertyInfo]:
        """Extract property information."""
        properties = []
        
        for name, prop in inspect.getmembers(service_type):
            if isinstance(prop, property):
                prop_info = PropertyInfo(
                    name=name,
                    type_hint=self._get_property_type(service_type, name),
                    is_readonly=prop.fset is None,
                    has_setter=prop.fset is not None
                )
                properties.append(prop_info)
        
        return properties
    
    def _get_property_type(self, service_type: Type, prop_name: str) -> Type:
        """Get type hint for a property."""
        annotations = getattr(service_type, '__annotations__', {})
        return annotations.get(prop_name, Any)
    
    def _extract_interfaces(self, service_type: Type) -> List[Type]:
        """Extract implemented interfaces."""
        # This is simplified - real implementation would check for Protocol types
        interfaces = []
        
        for base in service_type.__mro__[1:]:
            if hasattr(base, '__abstractmethods__') and base.__abstractmethods__:
                interfaces.append(base)
        
        return interfaces
    
    def _extract_base_classes(self, service_type: Type) -> List[Type]:
        """Extract base classes."""
        return list(service_type.__bases__)
```

## Generic Type Handling

### Generic Service Registration

```python
from typing import Generic, TypeVar, Dict, Type, Any

T = TypeVar('T')
K = TypeVar('K')
V = TypeVar('V')

class GenericTypeHandler:
    """Handles registration and resolution of generic services."""
    
    def __init__(self):
        self._generic_registrations: Dict[Type, Dict[tuple, Any]] = {}
    
    def register_generic(self, generic_type: Type[Generic], type_args: tuple, implementation: Any):
        """Register a concrete implementation for a generic type."""
        if generic_type not in self._generic_registrations:
            self._generic_registrations[generic_type] = {}
        
        self._generic_registrations[generic_type][type_args] = implementation
    
    def resolve_generic(self, concrete_type: Type) -> Any:
        """Resolve a concrete generic type."""
        origin = get_origin(concrete_type)
        args = get_args(concrete_type)
        
        if origin and origin in self._generic_registrations:
            generic_impls = self._generic_registrations[origin]
            
            # Exact match
            if args in generic_impls:
                return generic_impls[args]
            
            # Try to find compatible implementation
            for registered_args, implementation in generic_impls.items():
                if self._is_compatible_generic(args, registered_args):
                    return implementation
        
        return None
    
    def _is_compatible_generic(self, requested_args: tuple, registered_args: tuple) -> bool:
        """Check if generic type arguments are compatible."""
        if len(requested_args) != len(registered_args):
            return False
        
        for req_arg, reg_arg in zip(requested_args, registered_args):
            if not self._is_assignable(req_arg, reg_arg):
                return False
        
        return True
    
    def _is_assignable(self, source: Type, target: Type) -> bool:
        """Check if source type is assignable to target type."""
        try:
            return issubclass(source, target)
        except TypeError:
            # Handle cases where issubclass doesn't work
            return source == target

# Example generic service
class Repository(Generic[T]):
    """Generic repository interface."""
    
    def get(self, id: int) -> Optional[T]:
        raise NotImplementedError
    
    def save(self, entity: T) -> T:
        raise NotImplementedError
    
    def delete(self, id: int) -> bool:
        raise NotImplementedError

class UserRepository(Repository[User]):
    """Concrete user repository."""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
    
    def get(self, id: int) -> Optional[User]:
        return self.db_session.query(User).filter(User.id == id).first()
    
    def save(self, user: User) -> User:
        self.db_session.add(user)
        self.db_session.commit()
        return user
    
    def delete(self, id: int) -> bool:
        user = self.get(id)
        if user:
            self.db_session.delete(user)
            self.db_session.commit()
            return True
        return False

# Usage
handler = GenericTypeHandler()

# Register concrete implementation
handler.register_generic(Repository, (User,), UserRepository)

# Resolve generic type
user_repo_impl = handler.resolve_generic(Repository[User])
print(user_repo_impl)  # UserRepository
```

### Type Constraint Validation

```python
from typing import TypeVar, Union, Callable, Any

# Type variable with constraints
Numeric = TypeVar('Numeric', int, float, complex)
Comparable = TypeVar('Comparable', bound='Comparable')

class TypeConstraintValidator:
    """Validates type constraints for generic types."""
    
    def __init__(self):
        self._constraint_validators: Dict[TypeVar, Callable[[Type], bool]] = {}
    
    def register_constraint_validator(self, type_var: TypeVar, validator: Callable[[Type], bool]):
        """Register a custom constraint validator."""
        self._constraint_validators[type_var] = validator
    
    def validate_type_constraints(self, type_var: TypeVar, concrete_type: Type) -> bool:
        """Validate that a concrete type satisfies type variable constraints."""
        # Check explicit constraints
        if hasattr(type_var, '__constraints__') and type_var.__constraints__:
            return any(self._is_assignable(concrete_type, constraint) 
                      for constraint in type_var.__constraints__)
        
        # Check bound constraint
        if hasattr(type_var, '__bound__') and type_var.__bound__:
            return self._is_assignable(concrete_type, type_var.__bound__)
        
        # Check custom validator
        if type_var in self._constraint_validators:
            return self._constraint_validators[type_var](concrete_type)
        
        return True  # No constraints
    
    def _is_assignable(self, source: Type, target: Type) -> bool:
        """Check if source type is assignable to target type."""
        try:
            if isinstance(target, str):
                # Handle string type hints
                return source.__name__ == target
            return issubclass(source, target) or source == target
        except (TypeError, AttributeError):
            return source == target

# Custom constraint validators
def is_serializable(t: Type) -> bool:
    """Check if type is JSON serializable."""
    serializable_types = (int, float, str, bool, list, dict, type(None))
    return t in serializable_types or hasattr(t, '__json__')

def is_hashable(t: Type) -> bool:
    """Check if type is hashable."""
    try:
        hash(t())
        return True
    except (TypeError, AttributeError):
        return False

# Usage
validator = TypeConstraintValidator()
validator.register_constraint_validator(Numeric, lambda t: t in (int, float, complex))

# Validate constraints
print(validator.validate_type_constraints(Numeric, int))     # True
print(validator.validate_type_constraints(Numeric, str))     # False
```

## Runtime Type Checking

### Type Checker

```python
from typing import Any, Type, get_type_hints
import inspect

class RuntimeTypeChecker:
    """Performs runtime type checking for dependency injection."""
    
    def __init__(self, strict_mode: bool = False):
        self.strict_mode = strict_mode
        self.type_cache: Dict[Type, Dict[str, Type]] = {}
    
    def check_service_compatibility(self, service_type: Type, implementation: Any) -> bool:
        """Check if implementation is compatible with service type."""
        if inspect.isclass(implementation):
            return self._check_class_compatibility(service_type, implementation)
        else:
            return self._check_instance_compatibility(service_type, implementation)
    
    def _check_class_compatibility(self, service_type: Type, implementation_class: Type) -> bool:
        """Check if implementation class is compatible with service type."""
        try:
            # Check direct inheritance
            if issubclass(implementation_class, service_type):
                return True
            
            # Check duck typing compatibility
            if not self.strict_mode:
                return self._check_duck_typing(service_type, implementation_class)
            
            return False
        except TypeError:
            # Handle cases where issubclass doesn't work (e.g., generics)
            return self._check_structural_compatibility(service_type, implementation_class)
    
    def _check_instance_compatibility(self, service_type: Type, instance: Any) -> bool:
        """Check if instance is compatible with service type."""
        return isinstance(instance, service_type)
    
    def _check_duck_typing(self, interface: Type, implementation: Type) -> bool:
        """Check duck typing compatibility."""
        interface_methods = self._get_public_methods(interface)
        impl_methods = self._get_public_methods(implementation)
        
        # Check that implementation has all interface methods
        for method_name, method_sig in interface_methods.items():
            if method_name not in impl_methods:
                return False
            
            # Check method signature compatibility (simplified)
            impl_sig = impl_methods[method_name]
            if not self._check_signature_compatibility(method_sig, impl_sig):
                return False
        
        return True
    
    def _check_structural_compatibility(self, interface: Type, implementation: Type) -> bool:
        """Check structural type compatibility."""
        # This is a simplified structural typing check
        interface_attrs = set(dir(interface))
        impl_attrs = set(dir(implementation))
        
        # Check that implementation has all required attributes
        required_attrs = {attr for attr in interface_attrs 
                         if not attr.startswith('_') and callable(getattr(interface, attr, None))}
        
        return required_attrs.issubset(impl_attrs)
    
    def _get_public_methods(self, cls: Type) -> Dict[str, inspect.Signature]:
        """Get public methods and their signatures."""
        methods = {}
        
        for name, method in inspect.getmembers(cls, inspect.isfunction):
            if not name.startswith('_'):
                try:
                    methods[name] = inspect.signature(method)
                except (ValueError, TypeError):
                    pass  # Skip methods we can't analyze
        
        return methods
    
    def _check_signature_compatibility(self, expected: inspect.Signature, actual: inspect.Signature) -> bool:
        """Check if method signatures are compatible."""
        # Simplified signature compatibility check
        expected_params = list(expected.parameters.values())[1:]  # Skip 'self'
        actual_params = list(actual.parameters.values())[1:]      # Skip 'self'
        
        if len(expected_params) != len(actual_params):
            return False
        
        for exp_param, act_param in zip(expected_params, actual_params):
            if exp_param.annotation != inspect.Parameter.empty and act_param.annotation != inspect.Parameter.empty:
                if exp_param.annotation != act_param.annotation:
                    return False
        
        return True
    
    def validate_injection_target(self, target: Callable, dependencies: Dict[str, Any]) -> List[str]:
        """Validate that dependencies match injection target requirements."""
        errors = []
        
        try:
            sig = inspect.signature(target)
            type_hints = get_type_hints(target)
            
            for param_name, param in sig.parameters.items():
                if param_name == 'self':
                    continue
                
                expected_type = type_hints.get(param_name, param.annotation)
                
                if param_name in dependencies:
                    provided_value = dependencies[param_name]
                    
                    if expected_type != inspect.Parameter.empty:
                        if not self._is_value_compatible(provided_value, expected_type):
                            errors.append(f"Parameter '{param_name}' expects {expected_type}, got {type(provided_value)}")
                else:
                    if param.default == inspect.Parameter.empty and not TypeAnalyzer.is_optional_type(expected_type):
                        errors.append(f"Required parameter '{param_name}' not provided")
        
        except Exception as e:
            errors.append(f"Failed to validate injection target: {e}")
        
        return errors
    
    def _is_value_compatible(self, value: Any, expected_type: Type) -> bool:
        """Check if a value is compatible with expected type."""
        if expected_type == Any:
            return True
        
        try:
            return isinstance(value, expected_type)
        except TypeError:
            # Handle generic types and other complex type hints
            origin = get_origin(expected_type)
            if origin:
                return isinstance(value, origin)
            return True  # Fall back to allowing the value

# Usage
checker = RuntimeTypeChecker(strict_mode=True)

# Check service compatibility
is_compatible = checker.check_service_compatibility(UserRepository, SQLAlchemyUserRepository)
print(f"Repository compatible: {is_compatible}")

# Validate injection target
@inject
def service_method(user_repo: UserRepository, email_service: EmailService):
    pass

dependencies = {
    'user_repo': SQLAlchemyUserRepository(session),
    'email_service': "invalid_email_service"  # Wrong type
}

errors = checker.validate_injection_target(service_method, dependencies)
for error in errors:
    print(f"Validation error: {error}")
```

## Type Annotations

### Enhanced Type Annotations

```python
from typing import Annotated, Any
from dataclasses import dataclass

@dataclass
class InjectionMetadata:
    """Metadata for dependency injection."""
    token: Optional[str] = None
    scope: Optional[str] = None
    optional: bool = False
    factory: Optional[Callable] = None
    qualifier: Optional[str] = None

# Custom annotation types
def Inject(token: str = None, scope: str = None, optional: bool = False, qualifier: str = None):
    """Create injection annotation."""
    return Annotated[Any, InjectionMetadata(token=token, scope=scope, optional=optional, qualifier=qualifier)]

def Singleton(token: str = None):
    """Annotate as singleton dependency."""
    return Inject(token=token, scope='singleton')

def Transient(token: str = None):
    """Annotate as transient dependency."""
    return Inject(token=token, scope='transient')

def Optional(token: str = None):
    """Annotate as optional dependency."""
    return Inject(token=token, optional=True)

def Named(name: str):
    """Annotate with qualifier name."""
    return Inject(qualifier=name)

# Usage in service definitions
class UserService:
    def __init__(
        self,
        repository: Annotated[UserRepository, Singleton()],
        email_service: Annotated[EmailService, Named("smtp")],
        cache: Annotated[CacheService, Optional()],
        logger: Annotated[Logger, Transient()]
    ):
        self.repository = repository
        self.email_service = email_service
        self.cache = cache
        self.logger = logger

# Annotation extractor
class AnnotationExtractor:
    """Extracts injection metadata from type annotations."""
    
    @staticmethod
    def extract_injection_metadata(annotation: Any) -> Optional[InjectionMetadata]:
        """Extract injection metadata from type annotation."""
        if hasattr(annotation, '__metadata__'):
            for metadata in annotation.__metadata__:
                if isinstance(metadata, InjectionMetadata):
                    return metadata
        return None
    
    @staticmethod
    def get_service_dependencies_with_metadata(service_type: Type) -> Dict[str, tuple]:
        """Get service dependencies with their injection metadata."""
        dependencies = {}
        
        if hasattr(service_type, '__init__'):
            sig = inspect.signature(service_type.__init__)
            type_hints = get_type_hints(service_type.__init__, include_extras=True)
            
            for param_name, param in sig.parameters.items():
                if param_name == 'self':
                    continue
                
                type_hint = type_hints.get(param_name, param.annotation)
                metadata = AnnotationExtractor.extract_injection_metadata(type_hint)
                
                # Extract actual type (strip Annotated wrapper)
                actual_type = type_hint
                if hasattr(type_hint, '__origin__') and hasattr(type_hint, '__args__'):
                    actual_type = type_hint.__args__[0]
                
                dependencies[param_name] = (actual_type, metadata)
        
        return dependencies

# Usage
extractor = AnnotationExtractor()
deps = extractor.get_service_dependencies_with_metadata(UserService)

for param_name, (param_type, metadata) in deps.items():
    print(f"{param_name}: {param_type}")
    if metadata:
        print(f"  Token: {metadata.token}")
        print(f"  Scope: {metadata.scope}")
        print(f"  Optional: {metadata.optional}")
        print(f"  Qualifier: {metadata.qualifier}")
```
