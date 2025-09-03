# Override Patterns

**Override patterns** provide ways to temporarily replace service implementations during testing or runtime configuration.

## 🎯 Basic Override

### Simple Override

```python
def test_with_simple_override(container):
    """Test with simple service override."""
    # Setup original service
    container.bind(IEmailService, RealEmailService())

    # Verify original
    service = container.get(IEmailService)
    assert isinstance(service, RealEmailService)

    # Override with mock
    container.bind(IEmailService, MockEmailService())

    # Verify override
    service = container.get(IEmailService)
    assert isinstance(service, MockEmailService)

    # Override is permanent for this container
    service2 = container.get(IEmailService)
    assert isinstance(service2, MockEmailService)
```

### Context Manager Override

```python
def test_with_context_override(container):
    """Test with temporary override using context manager."""
    # Setup original service
    container.bind(IEmailService, RealEmailService())

    # Verify original
    service = container.get(IEmailService)
    assert isinstance(service, RealEmailService)

    # Temporary override
    with container.override(IEmailService, MockEmailService()) as mock:
        # Inside context: mock is active
        service = container.get(IEmailService)
        assert isinstance(service, MockEmailService)

        # Use the mock
        user_service = container.get(IUserService)
        user_service.register_user("john@example.com", "password")

        # Verify mock was used
        assert mock.call_count("send_welcome_email") == 1

    # Outside context: back to original
    service = container.get(IEmailService)
    assert isinstance(service, RealEmailService)
```

## 🔧 Advanced Override Patterns

### Nested Overrides

```python
def test_nested_overrides(container):
    """Test multiple levels of overrides."""
    container.bind(IEmailService, RealEmailService())
    container.bind(IUserService, RealUserService())

    # First level override
    with container.override(IEmailService, MockEmailService()) as email_mock:
        assert isinstance(container.get(IEmailService), MockEmailService)
        assert isinstance(container.get(IUserService), RealUserService)

        # Second level override
        with container.override(IUserService, MockUserService()) as user_mock:
            assert isinstance(container.get(IEmailService), MockEmailService)
            assert isinstance(container.get(IUserService), MockUserService)

            # Both services are mocked
            notification_svc = container.get(INotificationService)
            notification_svc.send_user_notification(123)

            # Verify both mocks were called
            assert email_mock.call_count("send_email") == 1
            assert user_mock.call_count("get_user") == 1

        # Back to first level
        assert isinstance(container.get(IEmailService), MockEmailService)
        assert isinstance(container.get(IUserService), RealUserService)

    # Back to original
    assert isinstance(container.get(IEmailService), RealEmailService)
    assert isinstance(container.get(IUserService), RealUserService)
```

### Conditional Overrides

```python
def test_conditional_override(container):
    """Override services based on conditions."""
    container.bind(IEmailService, RealEmailService())

    # Override based on environment
    if os.getenv("USE_MOCK_EMAIL", "false").lower() == "true":
        container.bind(IEmailService, MockEmailService())

    # Override based on test scenario
    test_scenario = os.getenv("TEST_SCENARIO", "normal")

    if test_scenario == "email_failure":
        container.bind(IEmailService, FailingEmailService())
    elif test_scenario == "slow_email":
        container.bind(IEmailService, SlowEmailService())

    # Test runs with appropriate service
    email_service = container.get(IEmailService)

    if test_scenario == "email_failure":
        assert isinstance(email_service, FailingEmailService)
    elif test_scenario == "slow_email":
        assert isinstance(email_service, SlowEmailService)
    else:
        assert isinstance(email_service, RealEmailService)
```

### Partial Overrides

```python
class PartialOverrideEmailService(RealEmailService):
    """Service that overrides only specific methods."""
    def __init__(self, real_service: RealEmailService):
        self.real_service = real_service
        self.mocked_calls = []

    def send_welcome_email(self, email: str) -> None:
        # Override this method
        self.mocked_calls.append(("send_welcome_email", email))

    def send_password_reset(self, email: str, token: str) -> None:
        # Use real implementation for this method
        self.real_service.send_password_reset(email, token)

def test_partial_override(container):
    """Test with partial service override."""
    real_email = RealEmailService()
    partial_override = PartialOverrideEmailService(real_email)
    container.bind(IEmailService, partial_override)

    user_service = container.get(IUserService)

    # Welcome email uses override
    user_service.register_user("john@example.com", "password")

    # Password reset uses real implementation
    user_service.reset_password("john@example.com")

    # Verify partial override
    assert len(partial_override.mocked_calls) == 1
    assert partial_override.mocked_calls[0][0] == "send_welcome_email"
```

## 🎨 Override Scenarios

### Test-Specific Overrides

```python
@pytest.fixture
def container():
    return TestContainer()

def test_registration_success(container):
    """Test successful registration."""
    # Override with successful email service
    container.bind(IEmailService, MockEmailService())

    user_service = container.get(IUserService)
    user = user_service.register_user("john@example.com", "password")

    assert user.email == "john@example.com"
    assert user.is_active is True

def test_registration_email_failure(container):
    """Test registration with email failure."""
    # Override with failing email service
    failing_email = MockEmailService()
    failing_email.configure_exception("send_welcome_email", SMTPError("Connection failed"))
    container.bind(IEmailService, failing_email)

    user_service = container.get(IUserService)

    # Should handle email failure gracefully
    user = user_service.register_user("john@example.com", "password")
    assert user.email == "john@example.com"
    # User should still be created even if email fails
    assert user.is_active is True

def test_registration_duplicate_email(container):
    """Test registration with duplicate email."""
    # Override repository to return existing user
    mock_repo = MockUserRepository()
    mock_repo.configure_return("get_user_by_email", User(id=1, email="john@example.com"))
    container.bind(IUserRepository, mock_repo)

    user_service = container.get(IUserService)

    with pytest.raises(EmailAlreadyExistsError):
        user_service.register_user("john@example.com", "password")
```

### Environment-Based Overrides

```python
def create_container_for_environment(env: str) -> InjectQ:
    """Create container with environment-specific overrides."""
    container = InjectQ()

    # Base services
    container.bind(IUserService, UserService())
    container.bind(IOrderService, OrderService())

    # Environment-specific overrides
    if env == "test":
        container.bind(IEmailService, MockEmailService())
        container.bind(IPaymentService, MockPaymentService())
        container.bind(IDatabase, FakeDatabase())

    elif env == "development":
        container.bind(IEmailService, ConsoleEmailService())  # Log to console
        container.bind(IPaymentService, StripePaymentService())
        container.bind(IDatabase, PostgresDatabase())

    elif env == "production":
        container.bind(IEmailService, SendGridEmailService())
        container.bind(IPaymentService, StripePaymentService())
        container.bind(IDatabase, PostgresDatabase())

    return container

def test_environment_overrides():
    """Test different environments use correct services."""
    # Test environment
    test_container = create_container_for_environment("test")
    assert isinstance(test_container.get(IEmailService), MockEmailService)
    assert isinstance(test_container.get(IPaymentService), MockPaymentService)

    # Development environment
    dev_container = create_container_for_environment("development")
    assert isinstance(dev_container.get(IEmailService), ConsoleEmailService)
    assert isinstance(dev_container.get(IPaymentService), StripePaymentService)
```

### Feature Flag Overrides

```python
class FeatureFlagContainer(InjectQ):
    """Container that supports feature flags."""
    def __init__(self):
        super().__init__()
        self.feature_flags = {}

    def set_feature_flag(self, flag: str, enabled: bool):
        self.feature_flags[flag] = enabled

    def is_feature_enabled(self, flag: str) -> bool:
        return self.feature_flags.get(flag, False)

    def bind_with_feature_flag(self, interface, implementation, feature_flag: str):
        """Bind service that may be overridden by feature flag."""
        if self.is_feature_enabled(feature_flag):
            self.bind(interface, implementation)

def test_feature_flag_overrides():
    """Test feature flag-based service overrides."""
    container = FeatureFlagContainer()

    # Base binding
    container.bind(IEmailService, BasicEmailService())

    # Feature flag override
    container.set_feature_flag("advanced_email", True)
    container.bind_with_feature_flag(
        IEmailService,
        AdvancedEmailService(),
        "advanced_email"
    )

    # Service should use advanced implementation
    email_service = container.get(IEmailService)
    assert isinstance(email_service, AdvancedEmailService)

    # Disable feature flag
    container.set_feature_flag("advanced_email", False)
    container.bind_with_feature_flag(
        IEmailService,
        BasicEmailService(),
        "advanced_email"
    )

    # Service should use basic implementation
    email_service = container.get(IEmailService)
    assert isinstance(email_service, BasicEmailService)
```

## 🔄 Dynamic Overrides

### Runtime Service Switching

```python
class DynamicContainer(InjectQ):
    """Container that allows runtime service switching."""
    def __init__(self):
        super().__init__()
        self.service_versions = {}

    def register_service_version(self, interface, implementation, version: str):
        """Register a version of a service."""
        if interface not in self.service_versions:
            self.service_versions[interface] = {}
        self.service_versions[interface][version] = implementation

    def switch_service_version(self, interface, version: str):
        """Switch to a different version of a service."""
        if interface in self.service_versions and version in self.service_versions[interface]:
            self.bind(interface, self.service_versions[interface][version])

def test_dynamic_service_switching():
    """Test runtime service version switching."""
    container = DynamicContainer()

    # Register service versions
    container.register_service_version(IEmailService, BasicEmailService(), "v1")
    container.register_service_version(IEmailService, AdvancedEmailService(), "v2")

    # Start with v1
    container.switch_service_version(IEmailService, "v1")
    service = container.get(IEmailService)
    assert isinstance(service, BasicEmailService)

    # Switch to v2
    container.switch_service_version(IEmailService, "v2")
    service = container.get(IEmailService)
    assert isinstance(service, AdvancedEmailService)
```

### A/B Testing Overrides

```python
class ABTestContainer(InjectQ):
    """Container that supports A/B testing."""
    def __init__(self):
        super().__init__()
        self.ab_tests = {}

    def setup_ab_test(self, test_name: str, interface, variant_a, variant_b):
        """Setup A/B test for a service."""
        self.ab_tests[test_name] = {
            "interface": interface,
            "variant_a": variant_a,
            "variant_b": variant_b
        }

    def assign_variant(self, test_name: str, user_id: int) -> str:
        """Assign user to A/B test variant."""
        # Simple hash-based assignment
        variant = "A" if hash(f"{test_name}_{user_id}") % 2 == 0 else "B"
        return variant

    def get_service_for_user(self, interface, user_id: int):
        """Get service variant for specific user."""
        for test_name, test_config in self.ab_tests.items():
            if test_config["interface"] == interface:
                variant = self.assign_variant(test_name, user_id)
                if variant == "A":
                    return test_config["variant_a"]
                else:
                    return test_config["variant_b"]

        # No A/B test, return default
        return self.get(interface)

def test_ab_testing_overrides():
    """Test A/B testing service overrides."""
    container = ABTestContainer()

    # Setup A/B test for email service
    container.setup_ab_test(
        "email_template_test",
        IEmailService,
        BasicEmailService(),
        FancyEmailService()
    )

    # User 1 gets variant A
    service1 = container.get_service_for_user(IEmailService, 1)
    assert isinstance(service1, BasicEmailService)

    # User 2 gets variant B
    service2 = container.get_service_for_user(IEmailService, 2)
    assert isinstance(service2, FancyEmailService)
```

## 🚨 Override Best Practices

### ✅ Good Patterns

#### 1. Clear Override Scope

```python
# ✅ Good: Clear context manager scope
def test_with_clear_scope(container):
    with container.override(IService, MockService()) as mock:
        # Override is clearly scoped
        service = container.get(IService)
        assert isinstance(service, MockService)

        # Use service
        result = service.do_work()

        # Verify
        assert mock.call_count("do_work") == 1

    # Outside scope: back to original
    service = container.get(IService)
    assert isinstance(service, RealService)
```

#### 2. Descriptive Override Names

```python
# ✅ Good: Descriptive override names
def test_payment_processing_with_failed_payment():
    failing_payment = MockPaymentService()
    failing_payment.configure_exception("charge_card", PaymentError("Card declined"))

    with container.override(IPaymentService, failing_payment):
        # Clear intent of the override
        pass

def test_email_sending_with_slow_service():
    slow_email = SlowEmailService(delay=5.0)

    with container.override(IEmailService, slow_email):
        # Clear intent of the override
        pass
```

#### 3. Override Cleanup

```python
# ✅ Good: Explicit cleanup
def test_with_cleanup(container):
    original_service = container.get(IService)

    # Override
    container.bind(IService, MockService())

    try:
        # Test logic
        service = container.get(IService)
        assert isinstance(service, MockService)

    finally:
        # Explicit cleanup
        container.bind(IService, original_service)
```

### ❌ Bad Patterns

#### 1. Global Overrides

```python
# ❌ Bad: Global override affects all tests
@pytest.fixture(scope="session")
def override_container():
    container = TestContainer()
    container.bind(IEmailService, MockEmailService())  # Affects all tests!
    return container

# ❌ Bad: Override in fixture without clear scope
@pytest.fixture
def container_with_override():
    container = TestContainer()
    container.bind(IEmailService, MockEmailService())  # Permanent override
    return container
```

#### 2. Nested Override Confusion

```python
# ❌ Bad: Confusing nested overrides
def test_confusing_nesting(container):
    with container.override(IService, MockServiceA()):
        with container.override(IService, MockServiceB()):  # Overrides the override!
            service = container.get(IService)
            # Which mock is active? Confusing!

# ✅ Good: Clear nested overrides
def test_clear_nesting(container):
    with container.override(IService, MockServiceA()) as mock_a:
        # First override active
        assert isinstance(container.get(IService), MockServiceA)

        with container.override(IOtherService, MockServiceB()) as mock_b:
            # Both overrides active
            assert isinstance(container.get(IService), MockServiceA)
            assert isinstance(container.get(IOtherService), MockServiceB)

        # Back to first override only
        assert isinstance(container.get(IService), MockServiceA)
```

#### 3. Override Without Verification

```python
# ❌ Bad: Override without testing its effect
def test_without_verification(container):
    with container.override(IEmailService, MockEmailService()):
        user_service = container.get(IUserService)
        user_service.register_user("john@example.com", "password")

        # No verification that mock was actually used!

# ✅ Good: Verify override was used
def test_with_verification(container):
    with container.override(IEmailService, MockEmailService()) as mock:
        user_service = container.get(IUserService)
        user_service.register_user("john@example.com", "password")

        # Verify mock was used
        assert mock.call_count("send_welcome_email") == 1
```

## 📊 Override Metrics and Monitoring

### Override Usage Tracking

```python
class MonitoredContainer(InjectQ):
    """Container that tracks override usage."""
    def __init__(self):
        super().__init__()
        self.override_history = []

    def override(self, interface, implementation):
        # Record override
        self.override_history.append({
            "interface": interface,
            "implementation": implementation,
            "timestamp": time.time()
        })

        return super().override(interface, implementation)

    def get_override_stats(self):
        """Get statistics about override usage."""
        stats = {}
        for entry in self.override_history:
            interface_name = entry["interface"].__name__
            if interface_name not in stats:
                stats[interface_name] = 0
            stats[interface_name] += 1
        return stats

def test_with_monitoring():
    """Test with override monitoring."""
    container = MonitoredContainer()

    # Use overrides
    with container.override(IEmailService, MockEmailService()):
        pass

    with container.override(IUserService, MockUserService()):
        pass

    with container.override(IEmailService, FailingEmailService()):
        pass

    # Check override statistics
    stats = container.get_override_stats()
    assert stats["IEmailService"] == 2  # Overridden twice
    assert stats["IUserService"] == 1   # Overridden once
```

### Override Performance Monitoring

```python
class PerformanceMonitoredContainer(InjectQ):
    """Container that monitors override performance."""
    def __init__(self):
        super().__init__()
        self.performance_stats = {}

    def override(self, interface, implementation):
        start_time = time.time()

        try:
            return super().override(interface, implementation)
        finally:
            duration = time.time() - start_time
            interface_name = interface.__name__

            if interface_name not in self.performance_stats:
                self.performance_stats[interface_name] = []

            self.performance_stats[interface_name].append(duration)

    def get_performance_stats(self):
        """Get performance statistics for overrides."""
        return {
            interface: {
                "count": len(durations),
                "avg_duration": sum(durations) / len(durations),
                "max_duration": max(durations),
                "min_duration": min(durations)
            }
            for interface, durations in self.performance_stats.items()
        }
```

## 🎯 Summary

Override patterns provide flexible ways to replace services:

- **Simple overrides** - Permanent service replacement
- **Context overrides** - Temporary service replacement
- **Nested overrides** - Multiple levels of replacement
- **Conditional overrides** - Environment or condition-based replacement
- **Dynamic overrides** - Runtime service switching

**Key features:**
- Temporary service replacement with context managers
- Nested override support
- Environment and condition-based overrides
- Feature flag integration
- A/B testing support
- Performance and usage monitoring

**Best practices:**
- Use context managers for clear override scope
- Give overrides descriptive names
- Verify that overrides are actually used
- Clean up overrides explicitly when needed
- Avoid global overrides that affect multiple tests
- Monitor override usage and performance

**Common patterns:**
- Test-specific overrides for different scenarios
- Environment-based service selection
- Feature flag-driven service switching
- A/B testing with service variants
- Runtime service version switching

Ready to explore [integration testing](integration-testing.md)?
