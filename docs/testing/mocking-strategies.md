# Mocking Strategies

**Mocking strategies** define different approaches to replacing real dependencies with test doubles during testing.

## 🎯 Mock Categories

### Dummy Objects

**Dummy objects** are passed around but never actually used. They are typically used to satisfy parameter requirements.

```python
class DummyEmailService:
    """Dummy implementation that does nothing."""
    def send_welcome_email(self, email: str) -> None:
        pass

    def send_password_reset(self, email: str, token: str) -> None:
        pass

def test_user_creation_with_dummy(container):
    """Test using dummy objects for unused dependencies."""
    # Bind dummy for dependency we don't care about
    container.bind(IEmailService, DummyEmailService())

    # Focus test on user creation logic
    user_service = container.get(IUserService)
    user = user_service.create_user("john@example.com", "password")

    # Only verify user creation
    assert user.email == "john@example.com"
    assert user.is_active is True
```

### Stubs

**Stubs** provide canned answers to calls made during the test, usually not responding at all to anything outside what's programmed in for the test.

```python
class StubUserRepository:
    """Stub that returns predefined data."""
    def __init__(self):
        self.users = {
            1: User(id=1, email="existing@example.com", is_active=True)
        }

    def get_user(self, user_id: int) -> Optional[User]:
        return self.users.get(user_id)

    def save_user(self, user: User) -> User:
        # Always succeed for stub
        user.id = len(self.users) + 1
        self.users[user.id] = user
        return user

    def get_user_by_email(self, email: str) -> Optional[User]:
        return next((u for u in self.users.values() if u.email == email), None)

def test_email_uniqueness_check(container):
    """Test email uniqueness validation using stub."""
    stub_repo = StubUserRepository()
    container.bind(IUserRepository, stub_repo)

    user_service = container.get(IUserService)

    # Test with existing email
    with pytest.raises(EmailAlreadyExistsError):
        user_service.create_user("existing@example.com", "password")

    # Test with new email
    user = user_service.create_user("new@example.com", "password")
    assert user.email == "new@example.com"
```

### Mocks

**Mocks** are pre-programmed with expectations which form a specification of the calls they are expected to receive.

```python
from injectq.testing import Mock

class MockEmailService(Mock[IEmailService]):
    def __init__(self):
        super().__init__()
        self.sent_emails = []

    def send_welcome_email(self, email: str) -> None:
        self.record_call("send_welcome_email", email)
        self.sent_emails.append({
            "type": "welcome",
            "email": email,
            "timestamp": time.time()
        })

    def send_password_reset(self, email: str, token: str) -> None:
        self.record_call("send_password_reset", email, token)
        self.sent_emails.append({
            "type": "password_reset",
            "email": email,
            "token": token,
            "timestamp": time.time()
        })

def test_registration_sends_welcome_email(container):
    """Test that registration sends welcome email."""
    mock_email = MockEmailService()
    container.bind(IEmailService, mock_email)

    user_service = container.get(IUserService)
    user = user_service.register_user("john@example.com", "password")

    # Verify the behavior we care about
    assert mock_email.call_count("send_welcome_email") == 1
    assert mock_email.was_called_with("send_welcome_email", "john@example.com")
    assert user.email == "john@example.com"
```

### Spies

**Spies** are stubs that also record some information based on how they were called.

```python
class SpyUserRepository(Mock[IUserRepository]):
    """Spy that records calls while delegating to real implementation."""
    def __init__(self, real_repo: IUserRepository):
        super().__init__()
        self.real_repo = real_repo
        self.created_users = []
        self.queried_users = []

    def save_user(self, user: User) -> User:
        self.record_call("save_user", user)

        # Delegate to real implementation
        saved_user = self.real_repo.save_user(user)
        self.created_users.append(saved_user)

        return saved_user

    def get_user(self, user_id: int) -> Optional[User]:
        self.record_call("get_user", user_id)

        # Delegate to real implementation
        user = self.real_repo.get_user(user_id)
        if user:
            self.queried_users.append(user)

        return user

def test_user_operations_with_spy(container, test_db):
    """Test user operations using spy pattern."""
    real_repo = UserRepository(test_db)
    spy_repo = SpyUserRepository(real_repo)
    container.bind(IUserRepository, spy_repo)

    user_service = container.get(IUserService)

    # Create user
    user = user_service.create_user("john@example.com", "password")

    # Retrieve user
    retrieved_user = user_service.get_user(user.id)

    # Verify spy recorded interactions
    assert spy_repo.call_count("save_user") == 1
    assert spy_repo.call_count("get_user") == 1
    assert len(spy_repo.created_users) == 1
    assert len(spy_repo.queried_users) == 1
    assert spy_repo.created_users[0].id == user.id
```

### Fakes

**Fakes** are working implementations with simplified functionality, not suitable for production use.

```python
class FakeDatabase:
    """Fake database using in-memory storage."""
    def __init__(self):
        self.users = {}
        self.orders = {}
        self._next_user_id = 1
        self._next_order_id = 1

    def save_user(self, user: User) -> User:
        if user.id is None:
            user.id = self._next_user_id
            self._next_user_id += 1
        self.users[user.id] = user
        return user

    def get_user(self, user_id: int) -> Optional[User]:
        return self.users.get(user_id)

    def get_user_by_email(self, email: str) -> Optional[User]:
        return next((u for u in self.users.values() if u.email == email), None)

    def save_order(self, order: Order) -> Order:
        if order.id is None:
            order.id = self._next_order_id
            self._next_order_id += 1
        self.orders[order.id] = order
        return order

    def get_order(self, order_id: int) -> Optional[Order]:
        return self.orders.get(order_id)

    def clear(self):
        """Clear all data for test isolation."""
        self.users.clear()
        self.orders.clear()
        self._next_user_id = 1
        self._next_order_id = 1

def test_complete_workflow_with_fake(container):
    """Test complete workflow using fake database."""
    fake_db = FakeDatabase()
    container.bind(IDatabase, fake_db)

    # Test complete user journey
    user_service = container.get(IUserService)
    order_service = container.get(IOrderService)

    # Create user
    user = user_service.create_user("john@example.com", "password")
    assert user.id == 1

    # Create order
    order = order_service.create_order(user.id, ["item1", "item2"])
    assert order.id == 1
    assert order.user_id == user.id

    # Verify data persistence
    saved_user = fake_db.get_user(user.id)
    saved_order = fake_db.get_order(order.id)
    assert saved_user.email == "john@example.com"
    assert saved_order.user_id == user.id
```

## 🎨 Choosing the Right Strategy

### When to Use Each Type

#### Use Dummies When:
- You need to satisfy constructor parameters
- The dependency won't be used in the test
- You want to keep the test focused

```python
def test_business_logic_only(container):
    """Test focuses only on business logic."""
    # Dummy for unused dependency
    container.bind(IExternalAPI, DummyExternalAPI())

    calculator = container.get(PriceCalculator)
    result = calculator.calculate(items)

    assert result.total == expected_total
```

#### Use Stubs When:
- You need predictable responses
- You want to test specific scenarios
- The test doesn't care about side effects

```python
def test_validation_with_stub(container):
    """Test validation with predictable data."""
    stub_repo = StubUserRepository()
    container.bind(IUserRepository, stub_repo)

    validator = container.get(EmailValidator)

    # Test existing email
    assert not validator.is_unique("existing@example.com")

    # Test new email
    assert validator.is_unique("new@example.com")
```

#### Use Mocks When:
- You need to verify interactions
- You want to ensure certain methods are called
- You need to check call arguments

```python
def test_notification_sent_on_registration(container):
    """Test that notification is sent during registration."""
    mock_email = MockEmailService()
    container.bind(IEmailService, mock_email)

    user_service = container.get(IUserService)
    user = user_service.register_user("john@example.com", "password")

    # Verify notification was sent
    assert mock_email.call_count("send_welcome_email") == 1
    assert mock_email.was_called_with("send_welcome_email", "john@example.com")
```

#### Use Spies When:
- You want to verify interactions with real implementations
- You need both real behavior and call verification
- You're testing integration between components

```python
def test_service_integration_with_spy(container, real_db):
    """Test service integration with spy verification."""
    real_repo = UserRepository(real_db)
    spy_repo = SpyUserRepository(real_repo)
    container.bind(IUserRepository, spy_repo)

    user_service = container.get(IUserService)
    user = user_service.create_user("john@example.com", "password")

    # Verify real database operation occurred
    assert user.id is not None

    # Verify spy recorded the interaction
    assert spy_repo.call_count("save_user") == 1
```

#### Use Fakes When:
- You need realistic behavior for integration tests
- You want to test against a real interface
- Performance is important for test execution

```python
def test_workflow_integration(container):
    """Test complete workflow with fake implementations."""
    container.bind(IDatabase, FakeDatabase())
    container.bind(ICache, FakeCache())

    # Test complete user journey
    workflow = container.get(UserRegistrationWorkflow)
    result = workflow.register_and_setup_user("john@example.com", "password")

    assert result.success is True
    assert result.user.email == "john@example.com"
    assert result.setup_complete is True
```

## 🔧 Advanced Mocking Patterns

### Partial Mocks

```python
class PartialMockEmailService(Mock[IEmailService]):
    """Mock that delegates some calls to real implementation."""
    def __init__(self, real_service: IEmailService):
        super().__init__()
        self.real_service = real_service

    def send_welcome_email(self, email: str) -> None:
        # Use real implementation for this method
        self.real_service.send_welcome_email(email)

    def send_password_reset(self, email: str, token: str) -> None:
        # Mock this method
        self.record_call("send_password_reset", email, token)

def test_partial_mock_usage(container):
    """Test using partial mock for selective mocking."""
    real_email = RealEmailService()
    partial_mock = PartialMockEmailService(real_email)
    container.bind(IEmailService, partial_mock)

    user_service = container.get(IUserService)

    # Welcome email uses real service
    user_service.register_user("john@example.com", "password")

    # Password reset uses mock
    user_service.reset_password("john@example.com")

    # Verify only password reset was mocked
    assert partial_mock.call_count("send_password_reset") == 1
    assert partial_mock.call_count("send_welcome_email") == 0
```

### Chain of Mocks

```python
class MockPaymentService(Mock[IPaymentService]):
    def __init__(self):
        super().__init__()
        self.authorized_payments = set()

    def authorize_payment(self, amount: float, card: str) -> str:
        self.record_call("authorize_payment", amount, card)

        # Generate mock authorization code
        auth_code = f"auth_{len(self.authorized_payments)}"
        self.authorized_payments.add(auth_code)

        return auth_code

    def capture_payment(self, auth_code: str, amount: float) -> bool:
        self.record_call("capture_payment", auth_code, amount)

        if auth_code in self.authorized_payments:
            self.authorized_payments.remove(auth_code)
            return True
        return False

def test_payment_workflow(container):
    """Test payment workflow with chained operations."""
    mock_payment = MockPaymentService()
    container.bind(IPaymentService, mock_payment)

    payment_service = container.get(IPaymentService)

    # Authorize payment
    auth_code = payment_service.authorize_payment(100.0, "4111111111111111")
    assert auth_code.startswith("auth_")

    # Capture payment
    success = payment_service.capture_payment(auth_code, 100.0)
    assert success is True

    # Verify call chain
    assert mock_payment.call_count("authorize_payment") == 1
    assert mock_payment.call_count("capture_payment") == 1
```

### Mock Factories

```python
class MockFactory:
    """Factory for creating configured mocks."""
    @staticmethod
    def create_email_service(fail_on_send: bool = False) -> MockEmailService:
        mock = MockEmailService()
        if fail_on_send:
            mock.configure_exception("send_welcome_email", SMTPError("Connection failed"))
        return mock

    @staticmethod
    def create_user_repository(users: List[User] = None) -> StubUserRepository:
        stub = StubUserRepository()
        if users:
            for user in users:
                stub.users[user.id] = user
        return stub

    @staticmethod
    def create_database(initial_data: dict = None) -> FakeDatabase:
        fake = FakeDatabase()
        if initial_data:
            fake.users.update(initial_data.get("users", {}))
            fake.orders.update(initial_data.get("orders", {}))
        return fake

def test_with_factory_mocks(container):
    """Test using mock factory for consistent setup."""
    # Create configured mocks
    email_mock = MockFactory.create_email_service()
    user_repo = MockFactory.create_user_repository([
        User(id=1, email="existing@example.com", is_active=True)
    ])

    container.bind(IEmailService, email_mock)
    container.bind(IUserRepository, user_repo)

    user_service = container.get(IUserService)

    # Test with pre-configured state
    with pytest.raises(EmailAlreadyExistsError):
        user_service.create_user("existing@example.com", "password")
```

## 🚨 Common Mocking Mistakes

### ❌ Over-Mocking

```python
# Bad: Mocking everything
def test_with_too_many_mocks(container):
    container.bind_mock(IUserService)
    container.bind_mock(IEmailService)
    container.bind_mock(IValidator)
    container.bind_mock(IPasswordHasher)
    container.bind_mock(ILogger)
    # Test becomes meaningless

# Good: Mock only external dependencies
def test_focused_test(container):
    # Mock external services only
    container.bind_mock(IEmailService)  # External API
    container.bind_mock(IPaymentService)  # External payment

    # Use real implementations for business logic
    # Test focuses on actual behavior
```

### ❌ Mocking Internal Logic

```python
# Bad: Mocking internal business logic
def test_internal_logic_mock(container):
    mock_calculator = MockPriceCalculator()
    mock_calculator.configure_return("calculate_tax", 10.0)
    container.bind(IPriceCalculator, mock_calculator)

    service = container.get(OrderService)
    total = service.calculate_total(order)

    # Test is testing the mock, not real logic
    assert total == 110.0  # Based on mock return

# Good: Test real business logic
def test_real_business_logic(container):
    # Use real calculator
    container.bind(IPriceCalculator, PriceCalculator())

    # Mock only external dependencies
    container.bind_mock(ITaxService)  # External tax API

    service = container.get(OrderService)
    total = service.calculate_total(order)

    # Test is testing real calculation logic
    assert total == expected_total
```

### ❌ Ignoring Mock Configuration

```python
# Bad: Mock not configured for test scenario
def test_unconfigured_mock(container):
    mock_repo = MockUserRepository()
    # Forgot to configure for "user not found" scenario
    container.bind(IUserRepository, mock_repo)

    service = container.get(UserService)

    # Test expects user not found, but mock returns None by default
    user = service.get_user(999)
    assert user is None  # This might fail if mock not configured

# Good: Properly configure mock for scenario
def test_configured_mock(container):
    mock_repo = MockUserRepository()
    mock_repo.configure_return("get_user", None)  # Explicitly configure
    container.bind(IUserRepository, mock_repo)

    service = container.get(UserService)
    user = service.get_user(999)
    assert user is None
```

## 📊 Mocking Best Practices

### 1. Mock External Dependencies Only

```python
# ✅ Good: Mock external services
container.bind_mock(IEmailService)      # External API
container.bind_mock(IPaymentGateway)    # External payment
container.bind_mock(ISMSService)        # External SMS

# ✅ Use real implementations for business logic
container.bind(IPriceCalculator, PriceCalculator())  # Real business logic
container.bind(IOrderValidator, OrderValidator())    # Real validation
```

### 2. Use Appropriate Mock Types

```python
# ✅ Use stubs for predictable data
container.bind(IUserRepository, StubUserRepository())

# ✅ Use mocks for interaction verification
container.bind(IEmailService, MockEmailService())

# ✅ Use fakes for realistic behavior
container.bind(IDatabase, FakeDatabase())

# ✅ Use spies for integration testing
container.bind(IUserRepository, SpyUserRepository(real_repo))
```

### 3. Configure Mocks Explicitly

```python
# ✅ Explicit mock configuration
mock_email = MockEmailService()
mock_email.configure_return("send_welcome_email", None)
mock_email.configure_exception("send_password_reset", SMTPError())
container.bind(IEmailService, mock_email)

# ✅ Clear mock configuration between tests
@pytest.fixture
def configured_mock():
    mock = MockEmailService()
    mock.configure_return("send_welcome_email", None)
    return mock
```

### 4. Verify Important Interactions

```python
# ✅ Verify critical interactions
def test_payment_processing(container):
    mock_payment = MockPaymentService()
    container.bind(IPaymentService, mock_payment)

    order_service = container.get(IOrderService)
    order_service.process_payment(order)

    # Verify payment was processed
    assert mock_payment.call_count("charge_card") == 1
    assert mock_payment.was_called_with("charge_card", order.total, order.card_token)

# ✅ Don't verify unimportant details
def test_user_creation(container):
    mock_email = MockEmailService()
    container.bind(IEmailService, mock_email)

    user_service = container.get(IUserService)
    user = user_service.create_user("john@example.com", "password")

    # Verify result, not email sending details
    assert user.email == "john@example.com"
    # Don't check email template or exact timing
```

### 5. Keep Mocks Simple

```python
# ✅ Simple, focused mock
class SimpleMockEmailService(Mock[IEmailService]):
    def send_welcome_email(self, email: str) -> None:
        self.record_call("send_welcome_email", email)

# ❌ Complex mock with too much logic
class ComplexMockEmailService(Mock[IEmailService]):
    def __init__(self):
        self.templates = {}
        self.queue = []
        self.retry_count = 3
        self.timeout = 30
        # ... lots of configuration

    def send_welcome_email(self, email: str) -> None:
        # Complex logic that might have bugs
        if self.should_retry:
            for i in range(self.retry_count):
                try:
                    self._send_with_template(email, "welcome")
                    break
                except Exception:
                    if i == self.retry_count - 1:
                        raise
        # ... more complex logic
```

## 🎯 Summary

Mocking strategies provide different ways to replace dependencies:

- **Dummies** - Satisfy parameters, never used
- **Stubs** - Provide canned responses
- **Mocks** - Verify interactions and expectations
- **Spies** - Record calls while using real implementations
- **Fakes** - Working implementations with simplified behavior

**Key principles:**
- Choose the right strategy for each test scenario
- Mock external dependencies, use real business logic
- Configure mocks explicitly for test scenarios
- Verify important interactions, not implementation details
- Keep mocks simple and focused
- Use factories for consistent mock creation

**Best practices:**
- Use dummies for unused dependencies
- Use stubs for predictable test data
- Use mocks for interaction verification
- Use spies for integration testing
- Use fakes for realistic behavior
- Avoid over-mocking and complex mock logic

Ready to explore [override patterns](override-patterns.md)?
