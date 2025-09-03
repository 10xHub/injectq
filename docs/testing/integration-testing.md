# Integration Testing

**Integration testing** verifies that different parts of the system work together correctly, testing real implementations with minimal mocking.

## 🎯 Integration Testing Overview

### What is Integration Testing?

Integration testing focuses on testing the interaction between components, using real implementations wherever possible and mocking only external dependencies.

```python
# Unit Test - Isolated components
def test_calculator_unit(container):
    # Mock all dependencies
    container.bind_mock(ITaxCalculator)
    container.bind_mock(IDiscountService)

    calculator = container.get(PriceCalculator)
    result = calculator.calculate_total(items)

    assert result == expected_total

# Integration Test - Real components working together
def test_calculator_integration(container):
    # Use real implementations
    container.bind(ITaxCalculator, TaxCalculator())
    container.bind(IDiscountService, DiscountService())

    # Mock only external services
    container.bind_mock(IPaymentGateway)  # External API

    calculator = container.get(PriceCalculator)
    result = calculator.calculate_total(items)

    # Test real business logic integration
    assert result.total == expected_total
    assert result.tax_amount == expected_tax
    assert result.discount_amount == expected_discount
```

## 🔧 Setting Up Integration Tests

### Integration Test Container

```python
from injectq.testing import TestContainer

@pytest.fixture
def integration_container():
    """Container for integration tests with real implementations."""
    container = TestContainer()

    # Real business logic services
    container.bind(IUserService, UserService())
    container.bind(IOrderService, OrderService())
    container.bind(IPriceCalculator, PriceCalculator())

    # Real infrastructure (but test versions)
    container.bind(IDatabase, TestDatabase())
    container.bind(ICache, TestRedisCache())

    # Mock external dependencies
    container.bind_mock(IEmailService)      # External email API
    container.bind_mock(IPaymentGateway)    # External payment API
    container.bind_mock(ISMSService)        # External SMS API

    return container

@pytest.fixture
def real_container():
    """Container with completely real implementations."""
    container = InjectQ()

    # All real implementations
    container.install(DatabaseModule())
    container.install(CacheModule())
    container.install(BusinessLogicModule())

    return container
```

### Test Database Setup

```python
class TestPostgresDatabase(IDatabase):
    """Test database that uses real PostgreSQL but isolated schema."""
    def __init__(self):
        self.schema_name = f"test_{uuid.uuid4().hex[:8]}"
        self.connection_string = f"postgresql://test:test@localhost:5432/testdb"

    async def initialize(self):
        """Create isolated test schema."""
        async with self.get_connection() as conn:
            await conn.execute(f"CREATE SCHEMA {self.schema_name}")
            await conn.execute(f"SET search_path TO {self.schema_name}")

            # Run migrations for test schema
            await self.run_migrations()

    async def cleanup(self):
        """Drop test schema."""
        async with self.get_connection() as conn:
            await conn.execute(f"DROP SCHEMA {self.schema_name} CASCADE")

    async def get_connection(self):
        return await asyncpg.connect(self.connection_string)

@pytest.fixture
async def test_db():
    """Test database with isolated schema."""
    db = TestPostgresDatabase()
    await db.initialize()

    try:
        yield db
    finally:
        await db.cleanup()
```

### Test Infrastructure

```python
class TestRedisCache(ICache):
    """Test cache using real Redis but isolated namespace."""
    def __init__(self):
        self.redis = redis.Redis(host="localhost", port=6379, db=1)
        self.namespace = f"test:{uuid.uuid4().hex[:8]}"

    def make_key(self, key: str) -> str:
        return f"{self.namespace}:{key}"

    async def get(self, key: str) -> Any:
        redis_key = self.make_key(key)
        value = self.redis.get(redis_key)
        return json.loads(value) if value else None

    async def set(self, key: str, value: Any, ttl: int = None) -> None:
        redis_key = self.make_key(key)
        json_value = json.dumps(value)

        if ttl:
            self.redis.setex(redis_key, ttl, json_value)
        else:
            self.redis.set(redis_key, json_value)

    async def delete(self, key: str) -> bool:
        redis_key = self.make_key(key)
        return bool(self.redis.delete(redis_key))

    async def clear(self):
        """Clear all test cache entries."""
        keys = self.redis.keys(f"{self.namespace}:*")
        if keys:
            self.redis.delete(*keys)
```

## 🎨 Integration Test Patterns

### Service Integration Testing

```python
def test_user_registration_integration(integration_container):
    """Test complete user registration workflow."""
    user_service = integration_container.get(IUserService)
    email_mock = integration_container.get_mock(IEmailService)

    # Register user
    user = user_service.register_user(
        email="john@example.com",
        password="secure_password123"
    )

    # Verify user was created
    assert user.id is not None
    assert user.email == "john@example.com"
    assert user.is_active is True
    assert user.created_at is not None

    # Verify welcome email was sent
    assert email_mock.call_count("send_welcome_email") == 1
    assert email_mock.was_called_with("send_welcome_email", "john@example.com")

    # Verify password was hashed
    assert user.password_hash != "secure_password123"
    assert user.password_hash.startswith("$2b$")  # bcrypt hash

def test_order_processing_integration(integration_container):
    """Test complete order processing workflow."""
    # Setup test data
    user_service = integration_container.get(IUserService)
    order_service = integration_container.get(IOrderService)
    payment_mock = integration_container.get_mock(IPaymentGateway)

    # Configure payment mock for success
    payment_mock.configure_return("charge_card", "txn_12345")

    # Create user
    user = user_service.create_user("john@example.com", "password")

    # Create order
    order = order_service.create_order(
        user_id=user.id,
        items=[
            {"product_id": 1, "quantity": 2, "price": 25.00},
            {"product_id": 2, "quantity": 1, "price": 15.00}
        ]
    )

    # Verify order
    assert order.id is not None
    assert order.user_id == user.id
    assert order.total == 65.00  # 2*25 + 1*15
    assert order.status == "pending"

    # Process payment
    success = order_service.process_payment(order.id, "tok_visa")

    # Verify payment processing
    assert success is True
    assert payment_mock.call_count("charge_card") == 1

    # Verify order status updated
    updated_order = order_service.get_order(order.id)
    assert updated_order.status == "paid"
```

### Cross-Service Integration

```python
def test_user_order_integration(integration_container):
    """Test integration between user and order services."""
    user_service = integration_container.get(IUserService)
    order_service = integration_container.get(IOrderService)
    email_mock = integration_container.get_mock(IEmailService)

    # Create user
    user = user_service.register_user("john@example.com", "password")

    # Create multiple orders
    order1 = order_service.create_order(user.id, [{"product_id": 1, "quantity": 1}])
    order2 = order_service.create_order(user.id, [{"product_id": 2, "quantity": 2}])

    # Verify user-order relationship
    user_orders = order_service.get_user_orders(user.id)
    assert len(user_orders) == 2
    assert order1.id in [o.id for o in user_orders]
    assert order2.id in [o.id for o in user_orders]

    # Test order notifications
    order_service.send_order_notifications(order1.id)

    # Verify notification was sent to correct email
    assert email_mock.call_count("send_order_confirmation") == 1
    calls = email_mock.get_calls("send_order_confirmation")
    assert calls[0]["args"][0] == user.email
```

### Infrastructure Integration

```python
def test_cache_database_integration(integration_container, test_db, test_cache):
    """Test integration between cache and database."""
    user_service = integration_container.get(IUserService)

    # Create user (goes to database)
    user = user_service.create_user("john@example.com", "password")

    # First retrieval (from database, then cached)
    retrieved_user = user_service.get_user(user.id)
    assert retrieved_user.email == "john@example.com"

    # Second retrieval (from cache)
    cached_user = user_service.get_user(user.id)
    assert cached_user.email == "john@example.com"

    # Verify cache was used
    cache_key = f"user:{user.id}"
    cached_data = test_cache.get(cache_key)
    assert cached_data is not None
    assert cached_data["email"] == "john@example.com"

    # Verify database was queried only once
    # (This would require spy or additional monitoring)
```

## 🧪 Advanced Integration Patterns

### End-to-End Workflow Testing

```python
def test_complete_user_journey(integration_container):
    """Test complete user journey from registration to order fulfillment."""
    # Services
    user_service = integration_container.get(IUserService)
    order_service = integration_container.get(IOrderService)
    inventory_service = integration_container.get(IInventoryService)
    shipping_service = integration_container.get(IShippingService)

    # Mocks
    payment_mock = integration_container.get_mock(IPaymentGateway)
    email_mock = integration_container.get_mock(IEmailService)
    shipping_mock = integration_container.get_mock(IShippingProvider)

    # Configure mocks
    payment_mock.configure_return("charge_card", "txn_success")
    shipping_mock.configure_return("create_shipment", "ship_123")

    # Step 1: User registration
    user = user_service.register_user("john@example.com", "password")
    assert user.is_active is True
    assert email_mock.call_count("send_welcome_email") == 1

    # Step 2: Browse and add to cart
    products = inventory_service.get_available_products()
    assert len(products) > 0

    cart = order_service.create_cart(user.id)
    order_service.add_to_cart(cart.id, products[0].id, 2)

    # Step 3: Checkout
    order = order_service.checkout_cart(cart.id, "tok_visa")

    # Verify order creation
    assert order.status == "pending"
    assert order.total > 0

    # Step 4: Payment processing
    payment_result = order_service.process_payment(order.id, "tok_visa")
    assert payment_result.success is True
    assert order_service.get_order(order.id).status == "paid"

    # Step 5: Inventory update
    inventory_service.reserve_items(order.id, order.items)
    for item in order.items:
        stock = inventory_service.get_stock(item.product_id)
        assert stock.reserved >= item.quantity

    # Step 6: Shipping
    shipment = shipping_service.create_shipment(order.id)
    assert shipment.tracking_number == "ship_123"
    assert order_service.get_order(order.id).status == "shipped"

    # Step 7: Order completion
    order_service.mark_order_delivered(order.id)
    final_order = order_service.get_order(order.id)
    assert final_order.status == "delivered"

    # Verify all communications sent
    assert email_mock.call_count("send_order_confirmation") == 1
    assert email_mock.call_count("send_shipping_notification") == 1
    assert email_mock.call_count("send_delivery_notification") == 1
```

### Data Consistency Testing

```python
def test_transaction_consistency(integration_container, test_db):
    """Test that operations maintain data consistency."""
    user_service = integration_container.get(IUserService)
    order_service = integration_container.get(IOrderService)

    # Start transaction
    async with test_db.transaction():
        # Create user
        user = user_service.create_user("john@example.com", "password")

        # Create order
        order = order_service.create_order(user.id, [{"product_id": 1, "quantity": 1}])

        # Simulate failure after partial operations
        if random.choice([True, False]):  # Random failure
            raise Exception("Simulated failure")

    # After transaction, check consistency
    # Either both operations succeeded or both failed
    user_exists = user_service.get_user(user.id) is not None
    order_exists = order_service.get_order(order.id) is not None

    assert user_exists == order_exists, "Data inconsistency detected!"
```

### Performance Integration Testing

```python
import time

def test_operation_performance(integration_container):
    """Test that operations complete within acceptable time."""
    user_service = integration_container.get(IUserService)

    # Test user creation performance
    start_time = time.time()

    users = []
    for i in range(100):  # Create 100 users
        user = user_service.create_user(f"user{i}@example.com", "password")
        users.append(user)

    creation_time = time.time() - start_time

    # Verify performance
    assert creation_time < 5.0, f"User creation took {creation_time}s, expected < 5.0s"
    assert len(users) == 100

    # Test bulk retrieval performance
    start_time = time.time()

    retrieved_users = user_service.get_users_bulk([u.id for u in users])

    retrieval_time = time.time() - start_time

    # Verify retrieval performance
    assert retrieval_time < 2.0, f"User retrieval took {retrieval_time}s, expected < 2.0s"
    assert len(retrieved_users) == 100
```

## 🚨 Integration Testing Challenges

### External Dependency Management

```python
# Challenge: External APIs can be slow/unreliable
def test_with_external_api_mocking(integration_container):
    """Test with mocked external dependencies."""
    # Mock slow external API
    payment_mock = MockPaymentGateway()
    payment_mock.configure_delay("charge_card", 0.1)  # Fast mock

    container.bind(IPaymentGateway, payment_mock)

    order_service = container.get(IOrderService)

    start_time = time.time()
    result = order_service.process_payment(order_id, card_token)
    duration = time.time() - start_time

    # Verify fast execution
    assert duration < 0.2  # Much faster than real API
    assert result.success is True

# Challenge: External service failures
def test_external_service_failure_handling(integration_container):
    """Test handling of external service failures."""
    # Mock external API failure
    email_mock = MockEmailService()
    email_mock.configure_exception("send_email", SMTPError("Service unavailable"))

    container.bind(IEmailService, email_mock)

    notification_service = container.get(INotificationService)

    # Should handle failure gracefully
    result = notification_service.send_notification(user_id, message)

    # Verify graceful degradation
    assert result.partial_success is True
    assert "email_failed" in result.errors
    # But other notifications might have succeeded
```

### Test Data Management

```python
class TestDataManager:
    """Manages test data for integration tests."""
    def __init__(self, db: IDatabase):
        self.db = db
        self.created_users = []
        self.created_orders = []

    async def create_test_user(self, email: str = None) -> User:
        """Create a test user with cleanup tracking."""
        if email is None:
            email = f"test_{uuid.uuid4().hex[:8]}@example.com"

        user = await self.db.create_user(email, "test_password")
        self.created_users.append(user)
        return user

    async def create_test_order(self, user_id: int, items: List[dict] = None) -> Order:
        """Create a test order with cleanup tracking."""
        if items is None:
            items = [{"product_id": 1, "quantity": 1, "price": 10.00}]

        order = await self.db.create_order(user_id, items)
        self.created_orders.append(order)
        return order

    async def cleanup(self):
        """Clean up all created test data."""
        for order in self.created_orders:
            await self.db.delete_order(order.id)

        for user in self.created_users:
            await self.db.delete_user(user.id)

@pytest.fixture
async def test_data_manager(integration_container):
    """Test data manager with automatic cleanup."""
    db = integration_container.get(IDatabase)
    manager = TestDataManager(db)

    try:
        yield manager
    finally:
        await manager.cleanup()
```

### Test Isolation

```python
# Challenge: Tests affecting each other through shared state
def test_isolation_problem(integration_container):
    """Demonstrates isolation problem."""
    user_service = integration_container.get(IUserService)

    # Test 1 creates user
    user1 = user_service.create_user("shared@example.com", "password")

    # If another test runs here and deletes the user...

    # Test 1 continues and fails
    retrieved = user_service.get_user(user1.id)
    assert retrieved is not None  # Might fail due to other test

# Solution: Use unique test data
def test_with_isolation(integration_container):
    """Test with proper isolation."""
    user_service = integration_container.get(IUserService)

    # Use unique email for this test
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    user = user_service.create_user(email, "password")

    # Test operations
    retrieved = user_service.get_user(user.id)
    assert retrieved.email == email

    # Cleanup
    user_service.delete_user(user.id)
```

## 📊 Integration Test Metrics

### Test Coverage Metrics

```python
def measure_integration_coverage(integration_container):
    """Measure which code paths are covered by integration tests."""
    coverage = {}

    # Track service method calls
    services_to_track = [
        (IUserService, "user_operations"),
        (IOrderService, "order_operations"),
        (IPaymentService, "payment_operations")
    ]

    for interface, category in services_to_track:
        service = integration_container.get(interface)

        # This would require instrumented services
        coverage[category] = {
            "methods_called": service._called_methods,
            "branches_covered": service._covered_branches
        }

    return coverage
```

### Performance Benchmarks

```python
def benchmark_integration_performance(integration_container):
    """Benchmark integration test performance."""
    user_service = integration_container.get(IUserService)

    # Benchmark user creation
    times = []
    for _ in range(50):
        start = time.time()
        user = user_service.create_user(f"bench_{uuid.uuid4().hex[:8]}@example.com", "pass")
        times.append(time.time() - start)

    return {
        "avg_creation_time": sum(times) / len(times),
        "min_creation_time": min(times),
        "max_creation_time": max(times),
        "p95_creation_time": sorted(times)[int(len(times) * 0.95)]
    }
```

## ✅ Integration Testing Best Practices

### 1. Test Real Integration Points

```python
# ✅ Good: Test real service interactions
def test_real_service_integration(integration_container):
    user_service = integration_container.get(IUserService)
    order_service = integration_container.get(IOrderService)

    # Create user through real service
    user = user_service.create_user("john@example.com", "password")

    # Create order through real service
    order = order_service.create_order(user.id, items)

    # Verify real integration
    assert order.user_id == user.id

# ❌ Bad: Mock everything, no real integration
def test_no_real_integration(container):
    container.bind_mock(IUserService)
    container.bind_mock(IOrderService)

    # No real integration being tested
    user_mock = container.get_mock(IUserService)
    order_mock = container.get_mock(IOrderService)

    # Just testing mocks
```

### 2. Use Appropriate Test Doubles

```python
# ✅ Good: Mock external, use real internal
def test_mixed_dependencies(integration_container):
    # Real internal services
    container.bind(IUserService, UserService())
    container.bind(IOrderService, OrderService())

    # Mock external dependencies
    container.bind_mock(IEmailService)      # External API
    container.bind_mock(IPaymentGateway)    # External service

# ❌ Bad: Mock internal services
def test_over_mocking(container):
    # Mocking internal business logic defeats integration testing
    container.bind_mock(IUserService)       # Internal service!
    container.bind_mock(IOrderService)      # Internal service!
    container.bind_mock(IPriceCalculator)   # Internal logic!
```

### 3. Ensure Test Isolation

```python
# ✅ Good: Isolated test data
def test_with_unique_data(integration_container):
    user_service = integration_container.get(IUserService)

    # Unique email for this test
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    user = user_service.create_user(email, "password")

    # Test operations
    assert user.email == email

    # Cleanup
    user_service.delete_user(user.id)

# ❌ Bad: Shared test data
def test_with_shared_data(integration_container):
    user_service = integration_container.get(IUserService)

    # Same email for all tests - causes conflicts
    user = user_service.create_user("shared@example.com", "password")
    # Other tests might interfere
```

### 4. Test Failure Scenarios

```python
# ✅ Good: Test integration failure handling
def test_integration_failure_handling(integration_container):
    # Setup failure scenario
    payment_mock = integration_container.get_mock(IPaymentGateway)
    payment_mock.configure_exception("charge_card", PaymentError("Card declined"))

    order_service = integration_container.get(IOrderService)

    # Test failure handling
    with pytest.raises(OrderProcessingError):
        order_service.process_payment(order_id, card_token)

    # Verify failure handling
    order = order_service.get_order(order_id)
    assert order.status == "payment_failed"

# ✅ Test partial failures
def test_partial_failure_handling(integration_container):
    # Setup partial failure
    email_mock = integration_container.get_mock(IEmailService)
    email_mock.configure_exception("send_email", SMTPError("Temporary failure"))

    notification_service = integration_container.get(INotificationService)

    # Should handle partial failure gracefully
    result = notification_service.send_multiple_notifications(notifications)

    assert result.total == len(notifications)
    assert result.successful == len(notifications) - 1  # One failed
    assert result.failed == 1
```

## 🎯 Summary

Integration testing verifies that system components work together correctly:

- **Service integration** - Test real service interactions
- **Cross-service workflows** - Test complete user journeys
- **Infrastructure integration** - Test with real databases and caches
- **External dependency handling** - Test with mocked external services
- **Failure scenario testing** - Test error handling and recovery

**Key principles:**
- Use real implementations for internal services
- Mock only external dependencies
- Ensure proper test isolation
- Test complete workflows, not just individual methods
- Include failure scenarios and error handling
- Monitor performance and consistency

**Best practices:**
- Create dedicated integration test containers
- Use test-specific databases and infrastructure
- Implement proper test data management
- Test both success and failure scenarios
- Monitor test performance and coverage
- Ensure tests are isolated and repeatable

Ready to explore [test scopes](test-scopes.md)?
