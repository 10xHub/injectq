# Testing Best Practices

This guide covers comprehensive testing strategies for InjectQ applications, including unit testing, integration testing, and advanced testing patterns.

## 🧪 Unit Testing with InjectQ

### Basic Unit Testing Setup

```python
# test_unit_basics.py
import pytest
from unittest.mock import Mock, AsyncMock
from injectq import InjectQ, inject, Module
from injectq.testing import TestModule, mock_service

# Example service to test
class EmailService:
    @inject
    def __init__(self, smtp_client: SMTPClient, config: EmailConfig):
        self.smtp_client = smtp_client
        self.config = config
        self.sent_emails = []
    
    async def send_email(self, to: str, subject: str, body: str) -> bool:
        """Send email and return success status."""
        try:
            await self.smtp_client.send(
                to=to,
                subject=subject,
                body=body,
                from_addr=self.config.from_address
            )
            self.sent_emails.append({
                "to": to,
                "subject": subject,
                "body": body
            })
            return True
        except Exception:
            return False
    
    async def send_bulk_emails(self, recipients: list, subject: str, body: str) -> dict:
        """Send emails to multiple recipients."""
        results = {"sent": 0, "failed": 0, "errors": []}
        
        for recipient in recipients:
            try:
                success = await self.send_email(recipient, subject, body)
                if success:
                    results["sent"] += 1
                else:
                    results["failed"] += 1
            except Exception as e:
                results["failed"] += 1
                results["errors"].append(str(e))
        
        return results

class SMTPClient:
    @inject
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.connected = False
    
    async def connect(self):
        self.connected = True
    
    async def send(self, to: str, subject: str, body: str, from_addr: str):
        if not self.connected:
            raise ConnectionError("SMTP client not connected")
        
        # Simulate sending email
        print(f"Sending email to {to}: {subject}")

@dataclass
class EmailConfig:
    from_address: str
    reply_to: str = ""

# Test module with mocks
class EmailTestModule(TestModule):
    def configure(self):
        # Mock SMTP client
        mock_smtp = Mock(spec=SMTPClient)
        mock_smtp.send = AsyncMock()
        mock_smtp.connected = True
        self.bind(SMTPClient, mock_smtp).singleton()
        
        # Real config for testing
        self.bind(EmailConfig, EmailConfig(
            from_address="test@example.com",
            reply_to="noreply@example.com"
        )).singleton()
        
        # Service under test
        self.bind(EmailService, EmailService).scoped()

# Basic unit tests
class TestEmailService:
    @pytest.fixture
    def container(self):
        """Create test container with mocked dependencies."""
        container = InjectQ()
        container.install(EmailTestModule())
        return container
    
    @pytest.fixture
    def email_service(self, container):
        """Get email service instance."""
        return container.get(EmailService)
    
    @pytest.fixture
    def mock_smtp(self, container):
        """Get mock SMTP client."""
        return container.get(SMTPClient)
    
    @pytest.mark.asyncio
    async def test_send_email_success(self, email_service, mock_smtp):
        """Test successful email sending."""
        # Arrange
        to = "user@example.com"
        subject = "Test Subject"
        body = "Test Body"
        
        # Act
        result = await email_service.send_email(to, subject, body)
        
        # Assert
        assert result is True
        mock_smtp.send.assert_called_once_with(
            to=to,
            subject=subject,
            body=body,
            from_addr="test@example.com"
        )
        assert len(email_service.sent_emails) == 1
        assert email_service.sent_emails[0]["to"] == to
    
    @pytest.mark.asyncio
    async def test_send_email_failure(self, email_service, mock_smtp):
        """Test email sending failure."""
        # Arrange
        mock_smtp.send.side_effect = Exception("SMTP Error")
        
        # Act
        result = await email_service.send_email("user@example.com", "Test", "Body")
        
        # Assert
        assert result is False
        assert len(email_service.sent_emails) == 0
    
    @pytest.mark.asyncio
    async def test_bulk_email_mixed_results(self, email_service, mock_smtp):
        """Test bulk email with mixed success/failure."""
        # Arrange
        recipients = ["user1@example.com", "user2@example.com", "user3@example.com"]
        
        # Mock SMTP to fail on second email
        def mock_send(to, **kwargs):
            if to == "user2@example.com":
                raise Exception("SMTP Error")
        
        mock_smtp.send.side_effect = mock_send
        
        # Act
        result = await email_service.send_bulk_emails(recipients, "Test", "Body")
        
        # Assert
        assert result["sent"] == 2
        assert result["failed"] == 1
        assert len(result["errors"]) == 1

# Advanced testing with dependency injection
class TestAdvancedMocking:
    @pytest.fixture
    def container_with_custom_mocks(self):
        """Create container with custom mock configurations."""
        container = InjectQ()
        
        # Create sophisticated mock
        smtp_mock = Mock(spec=SMTPClient)
        smtp_mock.connected = True
        
        # Configure mock behavior based on email content
        async def smart_send(to, subject, body, from_addr):
            if "spam" in subject.lower():
                raise ValueError("Spam detected")
            if "@invalid.com" in to:
                raise ConnectionError("Invalid domain")
            return True
        
        smtp_mock.send = AsyncMock(side_effect=smart_send)
        
        class CustomTestModule(TestModule):
            def configure(self):
                self.bind(SMTPClient, smtp_mock).singleton()
                self.bind(EmailConfig, EmailConfig(
                    from_address="test@company.com"
                )).singleton()
                self.bind(EmailService, EmailService).scoped()
        
        container.install(CustomTestModule())
        return container
    
    @pytest.mark.asyncio
    async def test_spam_detection(self, container_with_custom_mocks):
        """Test spam detection in mock."""
        email_service = container_with_custom_mocks.get(EmailService)
        
        # This should fail due to spam detection
        result = await email_service.send_email(
            "user@example.com", 
            "SPAM: Buy now!", 
            "Spam content"
        )
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_invalid_domain(self, container_with_custom_mocks):
        """Test invalid domain handling."""
        email_service = container_with_custom_mocks.get(EmailService)
        
        result = await email_service.send_email(
            "user@invalid.com", 
            "Valid Subject", 
            "Valid content"
        )
        
        assert result is False
```

### Testing with Scopes and Lifecycle

```python
# test_scopes_lifecycle.py
import pytest
import asyncio
from injectq import InjectQ, inject, Module, Scope
from injectq.testing import TestModule

class DatabaseConnection:
    """Database connection that tracks lifecycle."""
    
    def __init__(self, connection_id: str):
        self.connection_id = connection_id
        self.is_open = False
        self.transaction_count = 0
    
    async def open(self):
        self.is_open = True
        print(f"Database connection {self.connection_id} opened")
    
    async def close(self):
        self.is_open = False
        print(f"Database connection {self.connection_id} closed")
    
    async def begin_transaction(self):
        if not self.is_open:
            raise RuntimeError("Connection not open")
        self.transaction_count += 1

class UserRepository:
    @inject
    def __init__(self, db_connection: DatabaseConnection):
        self.db_connection = db_connection
        self.users = {}
    
    async def save_user(self, user_id: str, data: dict):
        await self.db_connection.begin_transaction()
        self.users[user_id] = data
        return user_id
    
    async def get_user(self, user_id: str):
        return self.users.get(user_id)

class UserService:
    @inject
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository
    
    async def create_user(self, name: str, email: str) -> str:
        user_data = {"name": name, "email": email}
        return await self.user_repository.save_user(f"user_{len(self.user_repository.users) + 1}", user_data)

# Testing different scopes
class ScopeTestModule(TestModule):
    def configure(self):
        # Singleton database connection
        self.bind(DatabaseConnection, lambda: DatabaseConnection("test_conn")).singleton()
        
        # Scoped repository (new instance per scope)
        self.bind(UserRepository, UserRepository).scoped()
        
        # Transient service (new instance every time)
        self.bind(UserService, UserService).transient()

class TestScopeBehavior:
    @pytest.fixture
    def container(self):
        container = InjectQ()
        container.install(ScopeTestModule())
        return container
    
    @pytest.mark.asyncio
    async def test_singleton_behavior(self, container):
        """Test that singleton instances are shared."""
        # Get database connection multiple times
        db1 = container.get(DatabaseConnection)
        db2 = container.get(DatabaseConnection)
        
        # Should be the same instance
        assert db1 is db2
        assert db1.connection_id == db2.connection_id
    
    @pytest.mark.asyncio
    async def test_scoped_behavior(self, container):
        """Test scoped instance behavior."""
        # First scope
        with container.create_scope() as scope1:
            repo1a = scope1.get(UserRepository)
            repo1b = scope1.get(UserRepository)
            
            # Same instance within scope
            assert repo1a is repo1b
            
            # Should use same database connection
            assert repo1a.db_connection is repo1b.db_connection
        
        # Second scope
        with container.create_scope() as scope2:
            repo2 = scope2.get(UserRepository)
            
            # Different instance in different scope
            assert repo2 is not repo1a
            
            # But same database connection (singleton)
            assert repo2.db_connection is repo1a.db_connection
    
    @pytest.mark.asyncio
    async def test_transient_behavior(self, container):
        """Test transient instance behavior."""
        with container.create_scope() as scope:
            service1 = scope.get(UserService)
            service2 = scope.get(UserService)
            
            # Different instances each time
            assert service1 is not service2
            
            # But same repository (scoped)
            assert service1.user_repository is service2.user_repository
    
    @pytest.mark.asyncio
    async def test_lifecycle_management(self, container):
        """Test proper lifecycle management in scopes."""
        db_conn = container.get(DatabaseConnection)
        await db_conn.open()
        
        initial_transaction_count = db_conn.transaction_count
        
        # Create multiple services and use them
        async with container.create_async_scope() as scope:
            service = scope.get(UserService)
            
            await service.create_user("John", "john@example.com")
            await service.create_user("Jane", "jane@example.com")
        
        # Database should have been used
        assert db_conn.transaction_count > initial_transaction_count
```

## 🔬 Integration Testing

### Testing Real Dependencies

```python
# test_integration.py
import pytest
import tempfile
import sqlite3
import aiofiles
import os
from pathlib import Path
from injectq import InjectQ, inject, Module

# Real implementations for integration testing
class SQLiteDatabase:
    @inject
    def __init__(self, database_path: str):
        self.database_path = database_path
        self.connection = None
    
    async def connect(self):
        self.connection = sqlite3.connect(self.database_path)
        await self._create_tables()
    
    async def close(self):
        if self.connection:
            self.connection.close()
    
    async def _create_tables(self):
        self.connection.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.connection.commit()

class SQLiteUserRepository:
    @inject
    def __init__(self, database: SQLiteDatabase):
        self.database = database
    
    async def save_user(self, name: str, email: str) -> int:
        cursor = self.database.connection.execute(
            "INSERT INTO users (name, email) VALUES (?, ?)",
            (name, email)
        )
        self.database.connection.commit()
        return cursor.lastrowid
    
    async def get_user(self, user_id: int) -> dict:
        cursor = self.database.connection.execute(
            "SELECT id, name, email, created_at FROM users WHERE id = ?",
            (user_id,)
        )
        row = cursor.fetchone()
        
        if row:
            return {
                "id": row[0],
                "name": row[1],
                "email": row[2],
                "created_at": row[3]
            }
        return None
    
    async def find_by_email(self, email: str) -> dict:
        cursor = self.database.connection.execute(
            "SELECT id, name, email, created_at FROM users WHERE email = ?",
            (email,)
        )
        row = cursor.fetchone()
        
        if row:
            return {
                "id": row[0],
                "name": row[1],
                "email": row[2],
                "created_at": row[3]
            }
        return None

class FileLoggerService:
    @inject
    def __init__(self, log_file_path: str):
        self.log_file_path = log_file_path
    
    async def log(self, level: str, message: str):
        async with aiofiles.open(self.log_file_path, 'a') as f:
            await f.write(f"[{level}] {message}\n")

class UserRegistrationService:
    @inject
    def __init__(
        self, 
        user_repository: SQLiteUserRepository,
        logger: FileLoggerService
    ):
        self.user_repository = user_repository
        self.logger = logger
    
    async def register_user(self, name: str, email: str) -> dict:
        """Register a new user with validation and logging."""
        await self.logger.log("INFO", f"Attempting to register user: {email}")
        
        # Check if user already exists
        existing_user = await self.user_repository.find_by_email(email)
        if existing_user:
            await self.logger.log("ERROR", f"User already exists: {email}")
            raise ValueError("User with this email already exists")
        
        # Validate email format (simple check)
        if "@" not in email:
            await self.logger.log("ERROR", f"Invalid email format: {email}")
            raise ValueError("Invalid email format")
        
        # Save user
        user_id = await self.user_repository.save_user(name, email)
        user = await self.user_repository.get_user(user_id)
        
        await self.logger.log("INFO", f"User registered successfully: {email} (ID: {user_id})")
        return user

# Integration test module
class IntegrationTestModule(Module):
    def __init__(self, temp_dir: str):
        self.temp_dir = temp_dir
    
    def configure(self):
        # Real file paths in temp directory
        db_path = os.path.join(self.temp_dir, "test.db")
        log_path = os.path.join(self.temp_dir, "test.log")
        
        self.bind(str, db_path, name="database_path")
        self.bind(str, log_path, name="log_file_path")
        
        # Real implementations
        self.bind(SQLiteDatabase, SQLiteDatabase).singleton()
        self.bind(SQLiteUserRepository, SQLiteUserRepository).singleton()
        self.bind(FileLoggerService, FileLoggerService).singleton()
        self.bind(UserRegistrationService, UserRegistrationService).singleton()

class TestUserRegistrationIntegration:
    @pytest.fixture
    async def temp_container(self):
        """Create container with real dependencies in temp directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            container = InjectQ()
            container.install(IntegrationTestModule(temp_dir))
            
            # Initialize database
            database = container.get(SQLiteDatabase)
            await database.connect()
            
            yield container, temp_dir
            
            # Cleanup
            await database.close()
    
    @pytest.mark.asyncio
    async def test_complete_user_registration_flow(self, temp_container):
        """Test complete user registration with real database and file logging."""
        container, temp_dir = temp_container
        
        registration_service = container.get(UserRegistrationService)
        
        # Register a user
        user = await registration_service.register_user("John Doe", "john@example.com")
        
        # Verify user was saved
        assert user["id"] is not None
        assert user["name"] == "John Doe"
        assert user["email"] == "john@example.com"
        assert user["created_at"] is not None
        
        # Verify logging occurred
        log_path = os.path.join(temp_dir, "test.log")
        assert os.path.exists(log_path)
        
        with open(log_path, 'r') as f:
            log_content = f.read()
            assert "Attempting to register user: john@example.com" in log_content
            assert "User registered successfully: john@example.com" in log_content
    
    @pytest.mark.asyncio
    async def test_duplicate_user_registration(self, temp_container):
        """Test duplicate user registration prevention."""
        container, temp_dir = temp_container
        
        registration_service = container.get(UserRegistrationService)
        
        # Register first user
        await registration_service.register_user("John Doe", "john@example.com")
        
        # Try to register duplicate user
        with pytest.raises(ValueError, match="User with this email already exists"):
            await registration_service.register_user("Jane Doe", "john@example.com")
        
        # Verify error was logged
        log_path = os.path.join(temp_dir, "test.log")
        with open(log_path, 'r') as f:
            log_content = f.read()
            assert "User already exists: john@example.com" in log_content
    
    @pytest.mark.asyncio
    async def test_invalid_email_validation(self, temp_container):
        """Test email validation."""
        container, temp_dir = temp_container
        
        registration_service = container.get(UserRegistrationService)
        
        # Try to register user with invalid email
        with pytest.raises(ValueError, match="Invalid email format"):
            await registration_service.register_user("John Doe", "invalid-email")
        
        # Verify error was logged
        log_path = os.path.join(temp_dir, "test.log")
        with open(log_path, 'r') as f:
            log_content = f.read()
            assert "Invalid email format: invalid-email" in log_content
    
    @pytest.mark.asyncio
    async def test_database_persistence(self, temp_container):
        """Test that data persists in database."""
        container, temp_dir = temp_container
        
        # Get services
        registration_service = container.get(UserRegistrationService)
        user_repository = container.get(SQLiteUserRepository)
        
        # Register multiple users
        user1 = await registration_service.register_user("User One", "user1@example.com")
        user2 = await registration_service.register_user("User Two", "user2@example.com")
        
        # Verify both users can be retrieved directly from repository
        retrieved_user1 = await user_repository.get_user(user1["id"])
        retrieved_user2 = await user_repository.get_user(user2["id"])
        
        assert retrieved_user1["email"] == "user1@example.com"
        assert retrieved_user2["email"] == "user2@example.com"
        
        # Test find by email
        found_user = await user_repository.find_by_email("user1@example.com")
        assert found_user["id"] == user1["id"]
```

## 🎭 Mock Strategies and Patterns

### Advanced Mocking Techniques

```python
# test_advanced_mocking.py
import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from contextlib import contextmanager
from typing import Dict, Any, List
from injectq import InjectQ, inject, Module
from injectq.testing import TestModule, mock_service

# Complex service with multiple dependencies
class PaymentGateway:
    async def charge(self, amount: float, card_token: str) -> Dict[str, Any]:
        """Charge payment method."""
        pass
    
    async def refund(self, charge_id: str) -> Dict[str, Any]:
        """Refund a charge."""
        pass

class InventoryService:
    async def check_stock(self, product_id: str) -> int:
        """Check available stock."""
        pass
    
    async def reserve_items(self, product_id: str, quantity: int) -> str:
        """Reserve items and return reservation ID."""
        pass
    
    async def release_reservation(self, reservation_id: str):
        """Release a reservation."""
        pass

class NotificationService:
    async def send_order_confirmation(self, user_id: str, order_data: Dict[str, Any]):
        """Send order confirmation."""
        pass
    
    async def send_payment_failure(self, user_id: str, error: str):
        """Send payment failure notification."""
        pass

class OrderProcessingService:
    @inject
    def __init__(
        self,
        payment_gateway: PaymentGateway,
        inventory_service: InventoryService,
        notification_service: NotificationService
    ):
        self.payment_gateway = payment_gateway
        self.inventory_service = inventory_service
        self.notification_service = notification_service
    
    async def process_order(
        self, 
        user_id: str, 
        product_id: str, 
        quantity: int, 
        card_token: str, 
        unit_price: float
    ) -> Dict[str, Any]:
        """Process complete order workflow."""
        
        # Check inventory
        available_stock = await self.inventory_service.check_stock(product_id)
        if available_stock < quantity:
            return {
                "status": "failed",
                "reason": "insufficient_stock",
                "available": available_stock
            }
        
        # Reserve inventory
        try:
            reservation_id = await self.inventory_service.reserve_items(product_id, quantity)
        except Exception as e:
            return {
                "status": "failed",
                "reason": "reservation_failed",
                "error": str(e)
            }
        
        # Process payment
        total_amount = quantity * unit_price
        try:
            payment_result = await self.payment_gateway.charge(total_amount, card_token)
            
            if not payment_result.get("success"):
                # Release reservation on payment failure
                await self.inventory_service.release_reservation(reservation_id)
                await self.notification_service.send_payment_failure(
                    user_id, 
                    payment_result.get("error", "Payment failed")
                )
                return {
                    "status": "failed",
                    "reason": "payment_failed",
                    "error": payment_result.get("error")
                }
            
            # Send confirmation
            order_data = {
                "product_id": product_id,
                "quantity": quantity,
                "total_amount": total_amount,
                "charge_id": payment_result["charge_id"]
            }
            
            await self.notification_service.send_order_confirmation(user_id, order_data)
            
            return {
                "status": "success",
                "order_data": order_data,
                "reservation_id": reservation_id
            }
            
        except Exception as e:
            # Release reservation on any error
            await self.inventory_service.release_reservation(reservation_id)
            return {
                "status": "failed",
                "reason": "processing_error",
                "error": str(e)
            }

# Smart mock factory
class SmartMockFactory:
    """Factory for creating intelligent mocks with realistic behavior."""
    
    @staticmethod
    def create_payment_gateway_mock(scenarios: Dict[str, Any] = None) -> Mock:
        """Create payment gateway mock with configurable scenarios."""
        mock = Mock(spec=PaymentGateway)
        
        # Default scenarios
        default_scenarios = {
            "success": {"success": True, "charge_id": "charge_123"},
            "insufficient_funds": {"success": False, "error": "Insufficient funds"},
            "invalid_card": {"success": False, "error": "Invalid card"},
            "network_error": Exception("Network timeout")
        }
        
        scenarios = scenarios or default_scenarios
        
        async def charge_side_effect(amount: float, card_token: str):
            # Simulate different responses based on card token
            if card_token == "invalid_card":
                return scenarios.get("invalid_card", default_scenarios["invalid_card"])
            elif card_token == "insufficient_funds":
                return scenarios.get("insufficient_funds", default_scenarios["insufficient_funds"])
            elif card_token == "network_error":
                raise scenarios.get("network_error", default_scenarios["network_error"])
            else:
                return scenarios.get("success", default_scenarios["success"])
        
        mock.charge = AsyncMock(side_effect=charge_side_effect)
        mock.refund = AsyncMock(return_value={"success": True, "refund_id": "refund_123"})
        
        return mock
    
    @staticmethod
    def create_inventory_mock(stock_levels: Dict[str, int] = None) -> Mock:
        """Create inventory service mock with configurable stock levels."""
        mock = Mock(spec=InventoryService)
        
        stock_levels = stock_levels or {}
        reservations = {}
        reservation_counter = 0
        
        async def check_stock_side_effect(product_id: str):
            return stock_levels.get(product_id, 0)
        
        async def reserve_items_side_effect(product_id: str, quantity: int):
            nonlocal reservation_counter
            
            available = stock_levels.get(product_id, 0)
            if available < quantity:
                raise ValueError(f"Insufficient stock: {available} < {quantity}")
            
            reservation_counter += 1
            reservation_id = f"reservation_{reservation_counter}"
            
            reservations[reservation_id] = {
                "product_id": product_id,
                "quantity": quantity
            }
            
            # Update stock
            stock_levels[product_id] = available - quantity
            
            return reservation_id
        
        async def release_reservation_side_effect(reservation_id: str):
            if reservation_id in reservations:
                reservation = reservations.pop(reservation_id)
                # Restore stock
                product_id = reservation["product_id"]
                quantity = reservation["quantity"]
                stock_levels[product_id] = stock_levels.get(product_id, 0) + quantity
        
        mock.check_stock = AsyncMock(side_effect=check_stock_side_effect)
        mock.reserve_items = AsyncMock(side_effect=reserve_items_side_effect)
        mock.release_reservation = AsyncMock(side_effect=release_reservation_side_effect)
        
        return mock
    
    @staticmethod
    def create_notification_mock(capture_calls: bool = True) -> Mock:
        """Create notification service mock that captures calls."""
        mock = Mock(spec=NotificationService)
        
        if capture_calls:
            mock.sent_confirmations = []
            mock.sent_failures = []
            
            async def capture_confirmation(user_id: str, order_data: Dict[str, Any]):
                mock.sent_confirmations.append({
                    "user_id": user_id,
                    "order_data": order_data
                })
            
            async def capture_failure(user_id: str, error: str):
                mock.sent_failures.append({
                    "user_id": user_id,
                    "error": error
                })
            
            mock.send_order_confirmation = AsyncMock(side_effect=capture_confirmation)
            mock.send_payment_failure = AsyncMock(side_effect=capture_failure)
        else:
            mock.send_order_confirmation = AsyncMock()
            mock.send_payment_failure = AsyncMock()
        
        return mock

# Advanced test class with sophisticated mock scenarios
class TestOrderProcessingAdvanced:
    @pytest.fixture
    def success_scenario_container(self):
        """Container configured for successful order processing."""
        container = InjectQ()
        
        class SuccessTestModule(TestModule):
            def configure(self):
                # Configure mocks for success scenario
                payment_mock = SmartMockFactory.create_payment_gateway_mock()
                inventory_mock = SmartMockFactory.create_inventory_mock({"product_1": 10})
                notification_mock = SmartMockFactory.create_notification_mock()
                
                self.bind(PaymentGateway, payment_mock).singleton()
                self.bind(InventoryService, inventory_mock).singleton()
                self.bind(NotificationService, notification_mock).singleton()
                self.bind(OrderProcessingService, OrderProcessingService).scoped()
        
        container.install(SuccessTestModule())
        return container
    
    @pytest.fixture
    def failure_scenario_container(self):
        """Container configured for various failure scenarios."""
        container = InjectQ()
        
        class FailureTestModule(TestModule):
            def configure(self):
                # Configure mocks for failure scenarios
                payment_mock = SmartMockFactory.create_payment_gateway_mock()
                inventory_mock = SmartMockFactory.create_inventory_mock({"product_1": 2})  # Low stock
                notification_mock = SmartMockFactory.create_notification_mock()
                
                self.bind(PaymentGateway, payment_mock).singleton()
                self.bind(InventoryService, inventory_mock).singleton()
                self.bind(NotificationService, notification_mock).singleton()
                self.bind(OrderProcessingService, OrderProcessingService).scoped()
        
        container.install(FailureTestModule())
        return container
    
    @pytest.mark.asyncio
    async def test_successful_order_processing(self, success_scenario_container):
        """Test complete successful order processing flow."""
        order_service = success_scenario_container.get(OrderProcessingService)
        notification_mock = success_scenario_container.get(NotificationService)
        
        result = await order_service.process_order(
            user_id="user123",
            product_id="product_1",
            quantity=2,
            card_token="valid_card",
            unit_price=25.99
        )
        
        # Verify success
        assert result["status"] == "success"
        assert result["order_data"]["total_amount"] == 51.98
        assert "reservation_id" in result
        
        # Verify notification was sent
        assert len(notification_mock.sent_confirmations) == 1
        assert notification_mock.sent_confirmations[0]["user_id"] == "user123"
        assert len(notification_mock.sent_failures) == 0
    
    @pytest.mark.asyncio
    async def test_insufficient_stock_scenario(self, failure_scenario_container):
        """Test handling of insufficient stock."""
        order_service = failure_scenario_container.get(OrderProcessingService)
        
        result = await order_service.process_order(
            user_id="user123",
            product_id="product_1",
            quantity=5,  # More than available (2)
            card_token="valid_card",
            unit_price=25.99
        )
        
        # Verify failure
        assert result["status"] == "failed"
        assert result["reason"] == "insufficient_stock"
        assert result["available"] == 2
    
    @pytest.mark.asyncio
    async def test_payment_failure_with_reservation_cleanup(self, success_scenario_container):
        """Test payment failure and proper reservation cleanup."""
        order_service = success_scenario_container.get(OrderProcessingService)
        inventory_mock = success_scenario_container.get(InventoryService)
        notification_mock = success_scenario_container.get(NotificationService)
        
        # Process order with invalid card
        result = await order_service.process_order(
            user_id="user123",
            product_id="product_1",
            quantity=2,
            card_token="insufficient_funds",  # Will trigger payment failure
            unit_price=25.99
        )
        
        # Verify failure
        assert result["status"] == "failed"
        assert result["reason"] == "payment_failed"
        
        # Verify reservation was released (stock should be back to original)
        remaining_stock = await inventory_mock.check_stock("product_1")
        assert remaining_stock == 10  # Should be restored
        
        # Verify failure notification was sent
        assert len(notification_mock.sent_failures) == 1
        assert notification_mock.sent_failures[0]["error"] == "Insufficient funds"
    
    @pytest.mark.asyncio
    async def test_network_error_handling(self, success_scenario_container):
        """Test handling of network errors during payment."""
        order_service = success_scenario_container.get(OrderProcessingService)
        inventory_mock = success_scenario_container.get(InventoryService)
        
        result = await order_service.process_order(
            user_id="user123",
            product_id="product_1",
            quantity=2,
            card_token="network_error",  # Will trigger exception
            unit_price=25.99
        )
        
        # Verify error handling
        assert result["status"] == "failed"
        assert result["reason"] == "processing_error"
        assert "Network timeout" in result["error"]
        
        # Verify reservation was cleaned up
        remaining_stock = await inventory_mock.check_stock("product_1")
        assert remaining_stock == 10

# Parameterized testing with mocks
class TestParameterizedMockScenarios:
    @pytest.mark.parametrize("card_token,expected_status,expected_reason", [
        ("valid_card", "success", None),
        ("insufficient_funds", "failed", "payment_failed"),
        ("invalid_card", "failed", "payment_failed"),
        ("network_error", "failed", "processing_error"),
    ])
    @pytest.mark.asyncio
    async def test_payment_scenarios(self, card_token, expected_status, expected_reason):
        """Test various payment scenarios using parameterized testing."""
        container = InjectQ()
        
        class ScenarioTestModule(TestModule):
            def configure(self):
                payment_mock = SmartMockFactory.create_payment_gateway_mock()
                inventory_mock = SmartMockFactory.create_inventory_mock({"product_1": 10})
                notification_mock = SmartMockFactory.create_notification_mock()
                
                self.bind(PaymentGateway, payment_mock).singleton()
                self.bind(InventoryService, inventory_mock).singleton()
                self.bind(NotificationService, notification_mock).singleton()
                self.bind(OrderProcessingService, OrderProcessingService).scoped()
        
        container.install(ScenarioTestModule())
        order_service = container.get(OrderProcessingService)
        
        result = await order_service.process_order(
            user_id="user123",
            product_id="product_1",
            quantity=2,
            card_token=card_token,
            unit_price=25.99
        )
        
        assert result["status"] == expected_status
        if expected_reason:
            assert result["reason"] == expected_reason
```

## 📊 Performance Testing

### Load Testing with InjectQ

```python
# test_performance.py
import pytest
import asyncio
import time
import statistics
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any
from injectq import InjectQ, inject, Module

# Service for performance testing
class CacheService:
    def __init__(self):
        self.cache: Dict[str, Any] = {}
        self.hit_count = 0
        self.miss_count = 0
    
    async def get(self, key: str) -> Any:
        if key in self.cache:
            self.hit_count += 1
            return self.cache[key]
        else:
            self.miss_count += 1
            return None
    
    async def set(self, key: str, value: Any):
        self.cache[key] = value
    
    def get_stats(self) -> Dict[str, int]:
        return {
            "hits": self.hit_count,
            "misses": self.miss_count,
            "total_keys": len(self.cache)
        }

class DataProcessor:
    @inject
    def __init__(self, cache_service: CacheService):
        self.cache_service = cache_service
    
    async def process_data(self, data_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process data with caching."""
        # Check cache first
        cached_result = await self.cache_service.get(f"processed_{data_id}")
        if cached_result:
            return cached_result
        
        # Simulate processing time
        await asyncio.sleep(0.01)  # 10ms processing time
        
        # Process data
        result = {
            "id": data_id,
            "processed_data": {k: v * 2 if isinstance(v, (int, float)) else v for k, v in data.items()},
            "timestamp": time.time()
        }
        
        # Cache result
        await self.cache_service.set(f"processed_{data_id}", result)
        
        return result

class PerformanceTestModule(Module):
    def configure(self):
        self.bind(CacheService, CacheService).singleton()
        self.bind(DataProcessor, DataProcessor).scoped()

class TestPerformance:
    @pytest.fixture
    def container(self):
        container = InjectQ()
        container.install(PerformanceTestModule())
        return container
    
    @pytest.mark.asyncio
    async def test_dependency_injection_overhead(self, container):
        """Test performance overhead of dependency injection."""
        
        # Test direct instantiation vs DI
        direct_times = []
        di_times = []
        
        # Direct instantiation timing
        for _ in range(1000):
            start = time.perf_counter()
            cache_service = CacheService()
            processor = DataProcessor(cache_service)
            end = time.perf_counter()
            direct_times.append(end - start)
        
        # DI instantiation timing
        for _ in range(1000):
            start = time.perf_counter()
            processor = container.get(DataProcessor)
            end = time.perf_counter()
            di_times.append(end - start)
        
        # Calculate statistics
        direct_avg = statistics.mean(direct_times)
        di_avg = statistics.mean(di_times)
        overhead_ratio = di_avg / direct_avg
        
        print(f"\nDirect instantiation avg: {direct_avg*1000:.3f}ms")
        print(f"DI instantiation avg: {di_avg*1000:.3f}ms")
        print(f"Overhead ratio: {overhead_ratio:.2f}x")
        
        # Assert reasonable overhead (should be less than 10x)
        assert overhead_ratio < 10.0
    
    @pytest.mark.asyncio
    async def test_concurrent_access_performance(self, container):
        """Test performance under concurrent access."""
        
        async def process_batch(processor: DataProcessor, batch_id: int, batch_size: int):
            """Process a batch of data items."""
            tasks = []
            for i in range(batch_size):
                data_id = f"batch_{batch_id}_item_{i}"
                data = {"value": i, "batch": batch_id}
                tasks.append(processor.process_data(data_id, data))
            
            return await asyncio.gather(*tasks)
        
        # Test with increasing concurrency
        concurrency_levels = [1, 5, 10, 20]
        batch_size = 50
        
        results = {}
        
        for concurrency in concurrency_levels:
            start_time = time.perf_counter()
            
            # Create tasks for concurrent execution
            tasks = []
            for batch_id in range(concurrency):
                # Each batch gets its own processor instance (scoped)
                with container.create_scope() as scope:
                    processor = scope.get(DataProcessor)
                    tasks.append(process_batch(processor, batch_id, batch_size))
            
            # Execute all batches concurrently
            batch_results = await asyncio.gather(*tasks)
            
            end_time = time.perf_counter()
            
            total_items = concurrency * batch_size
            duration = end_time - start_time
            throughput = total_items / duration
            
            results[concurrency] = {
                "duration": duration,
                "throughput": throughput,
                "total_items": total_items
            }
            
            print(f"\nConcurrency {concurrency}: {total_items} items in {duration:.3f}s ({throughput:.1f} items/s)")
        
        # Verify that higher concurrency improves throughput (to a point)
        assert results[5]["throughput"] > results[1]["throughput"]
    
    @pytest.mark.asyncio
    async def test_scope_creation_performance(self, container):
        """Test performance of scope creation and cleanup."""
        
        scope_creation_times = []
        scope_usage_times = []
        
        for _ in range(1000):
            # Test scope creation time
            start = time.perf_counter()
            scope = container.create_scope()
            scope_created = time.perf_counter()
            
            # Test service resolution time within scope
            processor = scope.get(DataProcessor)
            scope_used = time.perf_counter()
            
            # Cleanup
            scope.dispose()
            end = time.perf_counter()
            
            scope_creation_times.append(scope_created - start)
            scope_usage_times.append(scope_used - scope_created)
        
        creation_avg = statistics.mean(scope_creation_times) * 1000  # Convert to ms
        usage_avg = statistics.mean(scope_usage_times) * 1000
        
        print(f"\nScope creation avg: {creation_avg:.3f}ms")
        print(f"Service resolution avg: {usage_avg:.3f}ms")
        
        # Assert reasonable performance
        assert creation_avg < 1.0  # Less than 1ms for scope creation
        assert usage_avg < 1.0     # Less than 1ms for service resolution
    
    @pytest.mark.asyncio
    async def test_memory_usage_stability(self, container):
        """Test memory usage stability over many operations."""
        import gc
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Perform many operations
        for i in range(100):
            with container.create_scope() as scope:
                processor = scope.get(DataProcessor)
                
                # Process multiple items
                tasks = []
                for j in range(10):
                    data_id = f"memory_test_{i}_{j}"
                    data = {"value": j, "iteration": i}
                    tasks.append(processor.process_data(data_id, data))
                
                await asyncio.gather(*tasks)
            
            # Force garbage collection every 10 iterations
            if i % 10 == 0:
                gc.collect()
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        memory_increase_mb = memory_increase / (1024 * 1024)
        
        print(f"\nMemory increase: {memory_increase_mb:.2f} MB")
        
        # Assert reasonable memory usage (less than 50MB increase)
        assert memory_increase_mb < 50.0

# Stress testing
class TestStress:
    @pytest.mark.asyncio
    async def test_high_load_stress(self, container):
        """Stress test with high load."""
        
        async def stress_worker(worker_id: int, operations: int):
            """Worker that performs many operations."""
            for i in range(operations):
                with container.create_scope() as scope:
                    processor = scope.get(DataProcessor)
                    
                    data_id = f"stress_{worker_id}_{i}"
                    data = {"worker": worker_id, "operation": i}
                    
                    await processor.process_data(data_id, data)
        
        # Create many concurrent workers
        num_workers = 50
        operations_per_worker = 100
        
        start_time = time.perf_counter()
        
        tasks = [
            stress_worker(worker_id, operations_per_worker) 
            for worker_id in range(num_workers)
        ]
        
        await asyncio.gather(*tasks)
        
        end_time = time.perf_counter()
        
        total_operations = num_workers * operations_per_worker
        duration = end_time - start_time
        throughput = total_operations / duration
        
        print(f"\nStress test: {total_operations} operations in {duration:.3f}s")
        print(f"Throughput: {throughput:.1f} operations/s")
        
        # Verify system handled the load
        assert duration < 60.0  # Should complete within 60 seconds
        assert throughput > 100  # Should handle at least 100 ops/sec
```

This comprehensive testing guide covers:

1. **Unit Testing**: Basic mocking, dependency injection testing, scope behavior
2. **Integration Testing**: Real dependencies, file/database integration, end-to-end flows
3. **Advanced Mocking**: Smart mock factories, sophisticated scenarios, parameterized testing
4. **Performance Testing**: Load testing, memory usage, concurrent access, stress testing

Key testing principles demonstrated:
- Proper mock configuration and behavior
- Scope lifecycle management in tests
- Real vs. mocked dependency strategies
- Performance benchmarking and validation
- Memory leak detection and prevention
- Concurrent access patterns

Ready to add the debugging and troubleshooting best practices to complete the section?
