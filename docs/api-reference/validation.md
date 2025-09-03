# Validation API

::: injectq.diagnostics.validation

## Overview

The validation module provides comprehensive tools for validating dependency injection configurations, detecting issues, and ensuring container integrity.

## Container Validation

### Basic Validation

```python
from injectq.diagnostics import ContainerValidator

# Create validator
validator = ContainerValidator(container)

# Validate container configuration
result = validator.validate()

if result.is_valid:
    print("Container configuration is valid")
else:
    print("Validation errors found:")
    for error in result.errors:
        print(f"  - {error}")
```

### Validation Result

```python
from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class ValidationResult:
    """Result of container validation."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    suggestions: List[str]
    metadata: Dict[str, Any]
    
    def print_summary(self):
        """Print validation summary."""
        print(f"Validation Result: {'PASSED' if self.is_valid else 'FAILED'}")
        
        if self.errors:
            print(f"\nErrors ({len(self.errors)}):")
            for error in self.errors:
                print(f"  ❌ {error}")
        
        if self.warnings:
            print(f"\nWarnings ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"  ⚠️ {warning}")
        
        if self.suggestions:
            print(f"\nSuggestions ({len(self.suggestions)}):")
            for suggestion in self.suggestions:
                print(f"  💡 {suggestion}")
```

## Validation Rules

### Dependency Validation

```python
class DependencyValidator:
    """Validates service dependencies."""
    
    def __init__(self, container):
        self.container = container
        self.registry = container._registry
    
    def validate_dependencies(self) -> ValidationResult:
        """Validate all service dependencies."""
        errors = []
        warnings = []
        suggestions = []
        
        for service_type in self.registry.get_all_services():
            # Check if all dependencies are registered
            dependencies = self.get_service_dependencies(service_type)
            
            for dep_name, dep_type in dependencies.items():
                if not self.registry.is_registered(dep_type):
                    if self.is_optional_dependency(dep_type):
                        warnings.append(f"Optional dependency {dep_type.__name__} not registered for {service_type.__name__}")
                    else:
                        errors.append(f"Required dependency {dep_type.__name__} not registered for {service_type.__name__}")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions,
            metadata={}
        )
    
    def get_service_dependencies(self, service_type: type) -> Dict[str, type]:
        """Get dependencies for a service type."""
        dependencies = {}
        
        # Analyze constructor parameters
        if hasattr(service_type, '__init__'):
            import inspect
            sig = inspect.signature(service_type.__init__)
            
            for param_name, param in sig.parameters.items():
                if param_name != 'self' and param.annotation != inspect.Parameter.empty:
                    dependencies[param_name] = param.annotation
        
        return dependencies
    
    def is_optional_dependency(self, dep_type: type) -> bool:
        """Check if dependency is optional."""
        from typing import get_origin, get_args
        
        origin = get_origin(dep_type)
        if origin is Union:
            args = get_args(dep_type)
            return type(None) in args
        
        return False
```

### Circular Dependency Detection

```python
class CircularDependencyValidator:
    """Detects circular dependencies in service graph."""
    
    def __init__(self, container):
        self.container = container
        self.registry = container._registry
    
    def validate_circular_dependencies(self) -> ValidationResult:
        """Detect circular dependencies."""
        errors = []
        visited = set()
        recursion_stack = set()
        
        for service_type in self.registry.get_all_services():
            if service_type not in visited:
                cycles = self.find_cycles(service_type, visited, recursion_stack, [])
                
                for cycle in cycles:
                    cycle_str = " -> ".join(t.__name__ for t in cycle)
                    errors.append(f"Circular dependency detected: {cycle_str}")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=[],
            suggestions=[],
            metadata={'total_services': len(self.registry.get_all_services())}
        )
    
    def find_cycles(self, service_type: type, visited: set, rec_stack: set, path: List[type]):
        """Find cycles starting from a service type."""
        visited.add(service_type)
        rec_stack.add(service_type)
        path.append(service_type)
        
        cycles = []
        dependencies = self.get_dependencies(service_type)
        
        for dep_type in dependencies:
            if dep_type not in visited:
                cycles.extend(self.find_cycles(dep_type, visited, rec_stack, path.copy()))
            elif dep_type in rec_stack:
                # Found a cycle
                cycle_start = path.index(dep_type)
                cycle = path[cycle_start:] + [dep_type]
                cycles.append(cycle)
        
        rec_stack.remove(service_type)
        return cycles
    
    def get_dependencies(self, service_type: type) -> List[type]:
        """Get direct dependencies of a service type."""
        dependencies = []
        
        if hasattr(service_type, '__init__'):
            import inspect
            sig = inspect.signature(service_type.__init__)
            
            for param in sig.parameters.values():
                if param.name != 'self' and param.annotation != inspect.Parameter.empty:
                    dependencies.append(param.annotation)
        
        return dependencies
```

### Scope Validation

```python
from injectq.core.scopes import Scope

class ScopeValidator:
    """Validates scope configurations."""
    
    def __init__(self, container):
        self.container = container
        self.registry = container._registry
    
    def validate_scopes(self) -> ValidationResult:
        """Validate scope configurations."""
        errors = []
        warnings = []
        suggestions = []
        
        for service_type, binding in self.registry.get_all_services().items():
            # Check for scope anti-patterns
            self.check_singleton_dependencies(service_type, binding, errors, warnings)
            self.check_transient_performance(service_type, binding, warnings, suggestions)
            self.check_scoped_lifecycle(service_type, binding, warnings, suggestions)
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions,
            metadata={}
        )
    
    def check_singleton_dependencies(self, service_type: type, binding, errors: List[str], warnings: List[str]):
        """Check if singleton services depend on non-singleton services."""
        if binding.scope == Scope.SINGLETON:
            dependencies = self.get_dependencies(service_type)
            
            for dep_type in dependencies:
                dep_binding = self.registry.get_binding(dep_type)
                if dep_binding and dep_binding.scope != Scope.SINGLETON:
                    if dep_binding.scope == Scope.SCOPED:
                        errors.append(f"Singleton service {service_type.__name__} depends on scoped service {dep_type.__name__}")
                    elif dep_binding.scope == Scope.TRANSIENT:
                        warnings.append(f"Singleton service {service_type.__name__} depends on transient service {dep_type.__name__}")
    
    def check_transient_performance(self, service_type: type, binding, warnings: List[str], suggestions: List[str]):
        """Check for performance issues with transient services."""
        if binding.scope == Scope.TRANSIENT:
            # Check if service is expensive to create
            if self.is_expensive_service(service_type):
                warnings.append(f"Expensive service {service_type.__name__} is configured as transient")
                suggestions.append(f"Consider making {service_type.__name__} singleton or scoped")
    
    def check_scoped_lifecycle(self, service_type: type, binding, warnings: List[str], suggestions: List[str]):
        """Check scoped service lifecycle."""
        if binding.scope == Scope.SCOPED:
            # Check if service implements disposable pattern
            if not hasattr(service_type, 'dispose') and not hasattr(service_type, '__exit__'):
                suggestions.append(f"Scoped service {service_type.__name__} should implement disposal pattern")
    
    def is_expensive_service(self, service_type: type) -> bool:
        """Check if service is expensive to create."""
        # Heuristics for expensive services
        expensive_indicators = [
            'Database', 'Connection', 'Client', 'Service', 'Manager',
            'Repository', 'Cache', 'Pool', 'Factory'
        ]
        
        service_name = service_type.__name__
        return any(indicator in service_name for indicator in expensive_indicators)
    
    def get_dependencies(self, service_type: type) -> List[type]:
        """Get dependencies for a service type."""
        dependencies = []
        
        if hasattr(service_type, '__init__'):
            import inspect
            sig = inspect.signature(service_type.__init__)
            
            for param in sig.parameters.values():
                if param.name != 'self' and param.annotation != inspect.Parameter.empty:
                    dependencies.append(param.annotation)
        
        return dependencies
```

## Advanced Validation

### Type Safety Validation

```python
class TypeSafetyValidator:
    """Validates type safety of dependency injection."""
    
    def __init__(self, container):
        self.container = container
        self.registry = container._registry
    
    def validate_type_safety(self) -> ValidationResult:
        """Validate type safety of all bindings."""
        errors = []
        warnings = []
        suggestions = []
        
        for service_type, binding in self.registry.get_all_services().items():
            # Check implementation compatibility
            if not self.is_compatible_implementation(service_type, binding.implementation):
                errors.append(f"Implementation {binding.implementation} is not compatible with {service_type}")
            
            # Check generic types
            if self.has_generic_types(service_type):
                generic_errors = self.validate_generic_types(service_type, binding)
                errors.extend(generic_errors)
            
            # Check forward references
            forward_ref_warnings = self.check_forward_references(service_type)
            warnings.extend(forward_ref_warnings)
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions,
            metadata={}
        )
    
    def is_compatible_implementation(self, service_type: type, implementation) -> bool:
        """Check if implementation is compatible with service type."""
        if isinstance(implementation, type):
            try:
                return issubclass(implementation, service_type) or service_type == implementation
            except TypeError:
                # Handle cases where issubclass doesn't work (e.g., generics)
                return True
        
        return isinstance(implementation, service_type)
    
    def has_generic_types(self, service_type: type) -> bool:
        """Check if service type uses generics."""
        from typing import get_origin
        return get_origin(service_type) is not None
    
    def validate_generic_types(self, service_type: type, binding) -> List[str]:
        """Validate generic type bindings."""
        errors = []
        
        from typing import get_origin, get_args
        
        origin = get_origin(service_type)
        args = get_args(service_type)
        
        if origin and args:
            # Validate that implementation satisfies generic constraints
            impl_origin = get_origin(binding.implementation) if hasattr(binding.implementation, '__origin__') else None
            impl_args = get_args(binding.implementation) if hasattr(binding.implementation, '__args__') else ()
            
            if impl_origin != origin:
                errors.append(f"Generic implementation {binding.implementation} doesn't match service type {service_type}")
            elif len(impl_args) != len(args):
                errors.append(f"Generic argument count mismatch for {service_type}")
        
        return errors
    
    def check_forward_references(self, service_type: type) -> List[str]:
        """Check for unresolved forward references."""
        warnings = []
        
        if hasattr(service_type, '__forward_arg__'):
            warnings.append(f"Service type {service_type} has unresolved forward reference")
        
        return warnings
```

### Performance Validation

```python
class PerformanceValidator:
    """Validates performance characteristics of container configuration."""
    
    def __init__(self, container):
        self.container = container
        self.registry = container._registry
    
    def validate_performance(self) -> ValidationResult:
        """Validate performance characteristics."""
        errors = []
        warnings = []
        suggestions = []
        
        # Check dependency depth
        max_depth = self.check_dependency_depth()
        if max_depth > 10:
            warnings.append(f"Maximum dependency depth is {max_depth}, which may impact performance")
        
        # Check for singleton abuse
        singleton_count = self.count_singletons()
        total_services = len(self.registry.get_all_services())
        
        if singleton_count / total_services > 0.8:
            warnings.append(f"High percentage of singleton services ({singleton_count}/{total_services})")
            suggestions.append("Consider using scoped services for better memory management")
        
        # Check for transient overuse
        transient_count = self.count_transients()
        if transient_count / total_services > 0.5:
            warnings.append(f"High percentage of transient services ({transient_count}/{total_services})")
            suggestions.append("Consider using singleton or scoped services for better performance")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions,
            metadata={
                'max_dependency_depth': max_depth,
                'singleton_count': singleton_count,
                'transient_count': transient_count,
                'total_services': total_services
            }
        )
    
    def check_dependency_depth(self) -> int:
        """Calculate maximum dependency depth."""
        max_depth = 0
        
        for service_type in self.registry.get_all_services():
            depth = self.calculate_depth(service_type, set())
            max_depth = max(max_depth, depth)
        
        return max_depth
    
    def calculate_depth(self, service_type: type, visited: set) -> int:
        """Calculate dependency depth for a service."""
        if service_type in visited:
            return 0  # Circular dependency
        
        visited.add(service_type)
        
        dependencies = self.get_dependencies(service_type)
        if not dependencies:
            return 1
        
        max_child_depth = 0
        for dep_type in dependencies:
            child_depth = self.calculate_depth(dep_type, visited.copy())
            max_child_depth = max(max_child_depth, child_depth)
        
        return 1 + max_child_depth
    
    def count_singletons(self) -> int:
        """Count singleton services."""
        count = 0
        for _, binding in self.registry.get_all_services().items():
            if binding.scope == Scope.SINGLETON:
                count += 1
        return count
    
    def count_transients(self) -> int:
        """Count transient services."""
        count = 0
        for _, binding in self.registry.get_all_services().items():
            if binding.scope == Scope.TRANSIENT:
                count += 1
        return count
    
    def get_dependencies(self, service_type: type) -> List[type]:
        """Get dependencies for a service type."""
        dependencies = []
        
        if hasattr(service_type, '__init__'):
            import inspect
            sig = inspect.signature(service_type.__init__)
            
            for param in sig.parameters.values():
                if param.name != 'self' and param.annotation != inspect.Parameter.empty:
                    dependencies.append(param.annotation)
        
        return dependencies
```

## Validation Tools

### Comprehensive Validator

```python
class ContainerValidator:
    """Comprehensive container validator."""
    
    def __init__(self, container):
        self.container = container
        self.validators = [
            DependencyValidator(container),
            CircularDependencyValidator(container),
            ScopeValidator(container),
            TypeSafetyValidator(container),
            PerformanceValidator(container)
        ]
    
    def validate(self) -> ValidationResult:
        """Run all validation checks."""
        all_errors = []
        all_warnings = []
        all_suggestions = []
        combined_metadata = {}
        
        for validator in self.validators:
            if hasattr(validator, 'validate_dependencies'):
                result = validator.validate_dependencies()
            elif hasattr(validator, 'validate_circular_dependencies'):
                result = validator.validate_circular_dependencies()
            elif hasattr(validator, 'validate_scopes'):
                result = validator.validate_scopes()
            elif hasattr(validator, 'validate_type_safety'):
                result = validator.validate_type_safety()
            elif hasattr(validator, 'validate_performance'):
                result = validator.validate_performance()
            else:
                continue
            
            all_errors.extend(result.errors)
            all_warnings.extend(result.warnings)
            all_suggestions.extend(result.suggestions)
            combined_metadata.update(result.metadata)
        
        return ValidationResult(
            is_valid=len(all_errors) == 0,
            errors=all_errors,
            warnings=all_warnings,
            suggestions=all_suggestions,
            metadata=combined_metadata
        )
    
    def validate_and_report(self):
        """Validate and print detailed report."""
        result = self.validate()
        result.print_summary()
        return result
```

### Custom Validation Rules

```python
class CustomValidationRule:
    """Base class for custom validation rules."""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
    
    def validate(self, container) -> ValidationResult:
        """Implement validation logic."""
        raise NotImplementedError

class NamingConventionRule(CustomValidationRule):
    """Validates service naming conventions."""
    
    def __init__(self):
        super().__init__(
            "naming_convention",
            "Validates that services follow naming conventions"
        )
    
    def validate(self, container) -> ValidationResult:
        """Validate naming conventions."""
        warnings = []
        suggestions = []
        
        for service_type in container._registry.get_all_services():
            service_name = service_type.__name__
            
            # Check for interface naming
            if service_name.startswith('I') and service_name[1].isupper():
                # Interface should end with interface-indicating suffix
                if not any(service_name.endswith(suffix) for suffix in ['Service', 'Repository', 'Factory', 'Manager']):
                    suggestions.append(f"Interface {service_name} should end with descriptive suffix")
            
            # Check for implementation naming
            if service_name.endswith('Impl'):
                warnings.append(f"Service {service_name} uses 'Impl' suffix, consider more descriptive name")
        
        return ValidationResult(
            is_valid=True,  # Naming issues are not errors
            errors=[],
            warnings=warnings,
            suggestions=suggestions,
            metadata={}
        )

# Usage
validator = ContainerValidator(container)
validator.validators.append(NamingConventionRule())

result = validator.validate()
```

## Validation Configuration

### Validation Settings

```python
@dataclass
class ValidationSettings:
    """Configuration for validation behavior."""
    
    # Dependency validation
    check_missing_dependencies: bool = True
    allow_optional_dependencies: bool = True
    
    # Circular dependency validation
    check_circular_dependencies: bool = True
    max_dependency_depth: int = 20
    
    # Scope validation
    check_scope_compatibility: bool = True
    warn_singleton_transient_deps: bool = True
    
    # Type safety validation
    check_type_compatibility: bool = True
    validate_generic_types: bool = True
    
    # Performance validation
    check_performance_issues: bool = True
    max_singleton_percentage: float = 0.8
    max_transient_percentage: float = 0.5
    
    # Custom rules
    custom_rules: List[CustomValidationRule] = field(default_factory=list)

class ConfigurableValidator:
    """Validator with configurable settings."""
    
    def __init__(self, container, settings: ValidationSettings = None):
        self.container = container
        self.settings = settings or ValidationSettings()
    
    def validate(self) -> ValidationResult:
        """Validate with configured settings."""
        all_errors = []
        all_warnings = []
        all_suggestions = []
        combined_metadata = {}
        
        if self.settings.check_missing_dependencies:
            result = DependencyValidator(self.container).validate_dependencies()
            all_errors.extend(result.errors)
            all_warnings.extend(result.warnings)
        
        if self.settings.check_circular_dependencies:
            result = CircularDependencyValidator(self.container).validate_circular_dependencies()
            all_errors.extend(result.errors)
        
        # Continue with other validation checks based on settings...
        
        return ValidationResult(
            is_valid=len(all_errors) == 0,
            errors=all_errors,
            warnings=all_warnings,
            suggestions=all_suggestions,
            metadata=combined_metadata
        )
```
