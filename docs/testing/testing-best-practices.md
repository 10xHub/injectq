# Testing Best Practices

**Testing best practices** provide guidelines and patterns for effective testing with dependency injection.

## 🎯 Testing Principles

### Test Behavior, Not Implementation

```python
# ✅ Good: Test what the service does
def test_user_registration_sends_welcome_email(container):
    """Test that user registration sends welcome email."""
    mock_email = MockEmailService()
    container.bind(IEmailService, mock_email)

    user_service = container.get(IUserService)
    user = user_service.register_user("john@example.com", "password")

    # Verify behavior: email is sent
    assert mock_email.call_count("send_welcome_email") == 1
    assert user.email == "john@example.com"

# ❌ Bad: Test how the service does it
def test_user_registration_calls_internal_methods(container):
    """Test internal implementation details."""
    user_service = container.get(IUserService)

    user_service.register_user("john@example.com", "password")

    # Testing implementation: private method calls
    assert user_service._validate_email_called
    assert user_service._hash_password_called
    assert user_service._save_user_called
```

### Test Public Interfaces

```python
# ✅ Good: Test public API
def test_price_calculation_public_api(container):
    """Test price calculation through public interface."""
    calculator = container.get(IPriceCalculator)

    order = Order(items=[Item(price=10, quantity=2), Item(price=5, quantity=1)])
    total = calculator.calculate_total(order)

    assert total == 25  # (10*2) + (5*1)

# ❌ Bad: Test private methods
def test_price_calculation_private_methods(container):
    """Test private implementation details."""
    calculator = container.get(IPriceCalculator)

    # Don't test private methods
    tax = calculator._calculate_tax(100)
    discount = calculator._apply_discount(100, 10)

    assert tax == 8.0
    assert discount == 90.0
```

## 🔧 Test Organization

### Test File Structure

```python
# tests/
# ├── unit/
# │   ├── test_user_service.py
# │   ├── test_order_service.py
# │   └── test_price_calculator.py
# ├── integration/
# │   ├── test_user_registration_flow.py
# │   ├── test_order_processing_flow.py
# │   └── test_payment_flow.py
# ├── e2e/
# │   ├── test_complete_user_journey.py
# │   └── test_admin_workflow.py
# └── fixtures/
#     ├── conftest.py
#     ├── test_data.py
#     └── mock_services.py
```

### Test Naming Conventions

```python
# ✅ Good: Descriptive test names
def test_user_registration_with_valid_email_sends_welcome_email():
    pass

def test_order_calculation_applies_tax_correctly():
    pass

def test_payment_processing_handles_card_decline_gracefully():
    pass

# ❌ Bad: Vague test names
def test_user():
    pass

def test_calculation():
    pass

def test_payment():
    pass

# ✅ Good: Test method naming patterns
def test_[unit_of_work]_[scenario]_[expected_result]():
    pass

# Examples:
def test_user_registration_valid_email_creates_account():
    pass

def test_order_total_calculation_includes_tax_and_discount():
    pass

def test_payment_gateway_timeout_retries_automatically():
    pass
```

### Test Class Organization

```python
class TestUserService:
    """Test cases for UserService."""

    def setup_method(self):
        """Setup for each test method."""
        self.container = TestContainer()
        # Setup common test data

    def test_successful_registration(self):
        """Test successful user registration."""
        pass

    def test_registration_with_duplicate_email_fails(self):
        """Test registration fails with duplicate email."""
        pass

    def test_password_reset_sends_email(self):
        """Test password reset sends email."""
        pass

class TestUserServiceIntegration:
    """Integration tests for UserService."""

    def test_registration_creates_user_in_database(self):
        """Test that registration persists user to database."""
        pass

    def test_registration_sends_welcome_email_via_real_service(self):
        """Test email sending with real email service."""
        pass
```

## 🎨 Test Setup Patterns

### Fixture Best Practices

```python
# ✅ Good: Descriptive fixture names
@pytest.fixture
def user_service_with_mocked_dependencies():
    """User service with mocked email and database."""
    container = TestContainer()
    container.bind_mock(IEmailService)
    container.bind_mock(IUserRepository)

    service = container.get(IUserService)
    return service

@pytest.fixture
def integration_container():
    """Container for integration tests."""
    container = TestContainer()
    container.install(TestDatabaseModule())
    container.install(BusinessLogicModule())
    container.bind_mock(IExternalAPI)  # Only mock externals

    return container

# ❌ Bad: Generic fixture names
@pytest.fixture
def container():
    """Too generic, unclear purpose."""
    return TestContainer()

@pytest.fixture
def service():
    """Unclear which service."""
    container = TestContainer()
    return container.get(IService)
```

### Test Data Management

```python
# ✅ Good: Factory pattern for test data
class TestDataFactory:
    @staticmethod
    def create_user(email=None, name=None):
        return User(
            id=None,  # Will be set by database
            email=email or f"test_{uuid.uuid4().hex[:8]}@example.com",
            name=name or "Test User",
            created_at=datetime.now()
        )

    @staticmethod
    def create_order(user_id, items=None):
        if items is None:
            items = [TestDataFactory.create_order_item()]

        return Order(
            id=None,
            user_id=user_id,
            items=items,
            total=sum(item.price * item.quantity for item in items),
            status="pending"
        )

def test_order_creation_with_factory(container):
    """Test order creation using test data factory."""
    user = TestDataFactory.create_user()
    order = TestDataFactory.create_order(user.id)

    order_service = container.get(IOrderService)
    created_order = order_service.create_order(order)

    assert created_order.user_id == user.id
    assert created_order.status == "pending"

# ✅ Good: Builder pattern for complex objects
class UserBuilder:
    def __init__(self):
        self.email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        self.name = "Test User"
        self.is_active = True
        self.roles = []

    def with_email(self, email):
        self.email = email
        return self

    def with_name(self, name):
        self.name = name
        return self

    def inactive(self):
        self.is_active = False
        return self

    def with_roles(self, *roles):
        self.roles.extend(roles)
        return self

    def build(self):
        return User(
            id=None,
            email=self.email,
            name=self.name,
            is_active=self.is_active,
            roles=self.roles,
            created_at=datetime.now()
        )

def test_user_with_builder(container):
    """Test user creation using builder pattern."""
    user = (UserBuilder()
            .with_email("john@example.com")
            .with_name("John Doe")
            .with_roles("admin", "user")
            .build())

    user_service = container.get(IUserService)
    created_user = user_service.create_user(user)

    assert created_user.email == "john@example.com"
    assert "admin" in created_user.roles
```

## 🧪 Mock and Stub Patterns

### Appropriate Mock Usage

```python
# ✅ Good: Mock external dependencies
def test_user_service_with_mocked_email(container):
    """Mock external email service."""
    mock_email = container.bind_mock(IEmailService)

    user_service = container.get(IUserService)
    user = user_service.register_user("john@example.com", "password")

    # Verify external service was called
    assert mock_email.call_count("send_welcome_email") == 1

# ✅ Good: Mock slow or unreliable services
def test_payment_with_mocked_gateway(container):
    """Mock external payment gateway."""
    mock_payment = container.bind_mock(IPaymentGateway)
    mock_payment.configure_return("charge_card", "txn_123")

    payment_service = container.get(IPaymentService)
    result = payment_service.process_payment(100, "card_token")

    assert result.success is True
    assert result.transaction_id == "txn_123"

# ❌ Bad: Mock business logic
def test_business_logic_with_mocked_calculator(container):
    """Don't mock business logic you want to test."""
    mock_calculator = container.bind_mock(IPriceCalculator)
    mock_calculator.configure_return("calculate_total", 100)

    # This test is meaningless - just testing the mock
    order_service = container.get(IOrderService)
    total = order_service.calculate_order_total(order)

    assert total == 100  # Just verifying mock behavior
```

### Stub vs Mock Distinction

```python
# ✅ Use stubs for data provision
def test_with_stub_data(container):
    """Use stub for predictable test data."""
    stub_repo = StubUserRepository()
    stub_repo.save_user(TestDataFactory.create_user("existing@example.com"))

    container.bind(IUserRepository, stub_repo)

    user_service = container.get(IUserService)

    # Test with predictable existing data
    with pytest.raises(EmailExistsError):
        user_service.register_user("existing@example.com", "password")

# ✅ Use mocks for interaction verification
def test_with_mock_verification(container):
    """Use mock to verify interactions."""
    mock_email = MockEmailService()
    container.bind(IEmailService, mock_email)

    user_service = container.get(IUserService)
    user_service.register_user("john@example.com", "password")

    # Verify the interaction occurred
    assert mock_email.call_count("send_welcome_email") == 1
    assert mock_email.was_called_with("send_welcome_email", "john@example.com")
```

## 🚨 Common Testing Mistakes

### 1. Testing Implementation Details

```python
# ❌ Bad: Testing private methods
def test_private_method(container):
    service = container.get(IService)
    result = service._private_method()  # Don't test private methods
    assert result == expected

# ❌ Bad: Testing internal state
def test_internal_state(container):
    service = container.get(IService)
    service.do_something()

    # Don't test internal state
    assert service._internal_counter == 1
    assert len(service._internal_list) == 5

# ✅ Good: Test observable behavior
def test_observable_behavior(container):
    service = container.get(IService)
    result = service.do_something()

    # Test what the service does, not how
    assert result.success is True
    assert result.data is not None
```

### 2. Over-Mocking

```python
# ❌ Bad: Mocking everything
def test_with_too_many_mocks(container):
    container.bind_mock(IUserService)
    container.bind_mock(IEmailService)
    container.bind_mock(IValidator)
    container.bind_mock(IPasswordHasher)
    container.bind_mock(ILogger)

    # Test becomes meaningless
    service = container.get(IService)
    result = service.do_work()
    assert result is not None

# ✅ Good: Mock only what's necessary
def test_with_appropriate_mocking(container):
    # Mock external dependencies
    container.bind_mock(IEmailService)      # External API
    container.bind_mock(IPaymentGateway)    # External service

    # Use real implementations for business logic
    container.bind(IUserService, UserService())
    container.bind(IValidator, EmailValidator())

    # Test focuses on real business logic
    service = container.get(IService)
    result = service.do_work()
    assert result.success is True
```

### 3. No Test Isolation

```python
# ❌ Bad: Shared state between tests
class TestWithSharedState:
    container = TestContainer()  # Shared instance!

    def test1(self):
        user = self.container.get(IUserService).create_user("test@example.com")
        assert user.email == "test@example.com"

    def test2(self):
        # Sees user from test1!
        users = self.container.get(IUserService).get_all_users()
        assert len(users) == 1  # Unexpected!

# ✅ Good: Isolated tests
class TestWithIsolation:
    def setup_method(self):
        self.container = TestContainer()  # Fresh instance per test

    def test1(self):
        user = self.container.get(IUserService).create_user("test@example.com")
        assert user.email == "test@example.com"

    def test2(self):
        # Fresh container, no data from test1
        users = self.container.get(IUserService).get_all_users()
        assert len(users) == 0  # Expected
```

### 4. Ignoring Test Performance

```python
# ❌ Bad: Slow tests
def test_slow_operation(container):
    # No timeout or performance consideration
    service = container.get(IService)
    result = service.slow_operation()  # Takes 30 seconds
    assert result is not None

# ✅ Good: Performance-aware tests
def test_operation_within_timeout(container):
    service = container.get(IService)

    import time
    start = time.time()
    result = service.do_operation()
    duration = time.time() - start

    assert result is not None
    assert duration < 5.0  # Should complete within 5 seconds
```

### 5. Inconsistent Test Data

```python
# ❌ Bad: Hardcoded test data
def test_with_hardcoded_data(container):
    user_service = container.get(IUserService)

    # Hardcoded data causes conflicts
    user = user_service.create_user("test@example.com", "password")
    assert user.email == "test@example.com"

def test_another_with_hardcoded_data(container):
    user_service = container.get(IUserService)

    # Same hardcoded data causes conflicts
    user = user_service.create_user("test@example.com", "password")
    # This test might fail if previous test ran

# ✅ Good: Unique test data
def test_with_unique_data(container):
    user_service = container.get(IUserService)

    # Unique data per test
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    user = user_service.create_user(email, "password")
    assert user.email == email
```

## 📊 Test Quality Metrics

### Test Coverage Guidelines

```python
# pytest configuration for coverage
# pyproject.toml
[tool.coverage.run]
source = ["injectq"]
omit = [
    "*/tests/*",
    "*/migrations/*",
    "*/venv/*"
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError"
]
```

### Coverage Targets

- **Unit Tests**: 80%+ coverage of business logic
- **Integration Tests**: Cover critical user journeys
- **Branches**: 75%+ branch coverage
- **Lines**: 85%+ line coverage

### Test Performance Benchmarks

```python
# conftest.py
def pytest_configure(config):
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )

# Test with performance markers
@pytest.mark.slow
def test_slow_integration():
    """Mark slow tests."""
    pass

@pytest.mark.integration
def test_integration_test():
    """Mark integration tests."""
    pass
```

## ✅ Testing Best Practices Checklist

### Test Structure
- [ ] Tests are organized by type (unit, integration, e2e)
- [ ] Test names are descriptive and follow naming conventions
- [ ] Tests use appropriate fixtures for setup
- [ ] Test data is unique and isolated
- [ ] Tests clean up after themselves

### Test Quality
- [ ] Tests focus on behavior, not implementation
- [ ] Tests use appropriate mocking strategies
- [ ] Tests cover both success and failure scenarios
- [ ] Tests are fast and reliable
- [ ] Tests provide clear failure messages

### Test Maintenance
- [ ] Tests are easy to understand and modify
- [ ] Tests use factories/builders for complex data
- [ ] Tests avoid shared state
- [ ] Tests have appropriate performance expectations
- [ ] Tests are regularly reviewed and updated

### CI/CD Integration
- [ ] Tests run in CI pipeline
- [ ] Test coverage is tracked and reported
- [ ] Performance regressions are caught
- [ ] Tests run in parallel where possible
- [ ] Test results are easily accessible

## 🎯 Summary

Effective testing with dependency injection requires:

- **Clear test organization** - Separate unit, integration, and e2e tests
- **Appropriate mocking** - Mock externals, test real business logic
- **Proper isolation** - Each test gets fresh, unique data
- **Behavior focus** - Test what services do, not implementation details
- **Performance awareness** - Keep tests fast and monitor performance

**Key principles:**
- Test public interfaces and observable behavior
- Use fixtures for consistent test setup
- Mock external dependencies, use real business logic
- Ensure test isolation and cleanup
- Write descriptive test names and clear assertions
- Monitor test coverage and performance

**Common patterns:**
- Factory pattern for test data creation
- Builder pattern for complex objects
- Fixture-based test setup
- Appropriate mock vs stub usage
- Performance benchmarking in tests

**Quality checklist:**
- Tests are fast, isolated, and reliable
- Test names are descriptive
- Coverage meets targets
- Tests focus on behavior over implementation
- CI/CD integration is solid

This completes the testing section! Ready to explore [advanced features](advanced-features.md)?
