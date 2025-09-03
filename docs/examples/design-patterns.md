# Design Patterns with InjectQ

This guide demonstrates how to implement common design patterns using InjectQ's dependency injection capabilities.

## 🏭 Factory Pattern

The Factory pattern provides a way to create objects without specifying their exact class. InjectQ makes this pattern elegant through named bindings and conditional injection.

### Simple Factory

```python
# simple_factory.py
from abc import ABC, abstractmethod
from injectq import InjectQ, inject, Module
from typing import Dict, Type

# Product Interface
class INotificationService(ABC):
    @abstractmethod
    async def send(self, message: str, recipient: str) -> bool:
        pass

# Concrete Products
class EmailNotificationService(INotificationService):
    @inject
    def __init__(self, email_config: EmailConfig):
        self.config = email_config

    async def send(self, message: str, recipient: str) -> bool:
        print(f"Sending email to {recipient}: {message}")
        return True

class SMSNotificationService(INotificationService):
    @inject
    def __init__(self, sms_config: SMSConfig):
        self.config = sms_config

    async def send(self, message: str, recipient: str) -> bool:
        print(f"Sending SMS to {recipient}: {message}")
        return True

class PushNotificationService(INotificationService):
    @inject
    def __init__(self, push_config: PushConfig):
        self.config = push_config

    async def send(self, message: str, recipient: str) -> bool:
        print(f"Sending push notification to {recipient}: {message}")
        return True

# Configuration Classes
class EmailConfig:
    def __init__(self, smtp_host: str, smtp_port: int):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port

class SMSConfig:
    def __init__(self, api_key: str, endpoint: str):
        self.api_key = api_key
        self.endpoint = endpoint

class PushConfig:
    def __init__(self, app_id: str, api_key: str):
        self.app_id = app_id
        self.api_key = api_key

# Factory Interface
class INotificationFactory(ABC):
    @abstractmethod
    def create_notification_service(self, notification_type: str) -> INotificationService:
        pass

# Factory Implementation
class NotificationFactory(INotificationFactory):
    @inject
    def __init__(self, container: InjectQ):
        self.container = container
        self._service_map = {
            "email": "email_service",
            "sms": "sms_service",
            "push": "push_service"
        }

    def create_notification_service(self, notification_type: str) -> INotificationService:
        service_name = self._service_map.get(notification_type)
        if not service_name:
            raise ValueError(f"Unsupported notification type: {notification_type}")
        
        return self.container.get(INotificationService, name=service_name)

# Client Code
class NotificationManager:
    @inject
    def __init__(self, notification_factory: INotificationFactory):
        self.factory = notification_factory

    async def send_notification(self, notification_type: str, message: str, recipient: str) -> bool:
        service = self.factory.create_notification_service(notification_type)
        return await service.send(message, recipient)

    async def send_multi_channel(self, message: str, recipient: str, channels: list) -> Dict[str, bool]:
        results = {}
        for channel in channels:
            try:
                service = self.factory.create_notification_service(channel)
                results[channel] = await service.send(message, recipient)
            except Exception as e:
                print(f"Failed to send {channel} notification: {e}")
                results[channel] = False
        return results

# Module Configuration
class NotificationModule(Module):
    def configure(self):
        # Configuration
        self.bind(EmailConfig, EmailConfig("smtp.example.com", 587)).singleton()
        self.bind(SMSConfig, SMSConfig("sms_api_key", "https://api.sms.com")).singleton()
        self.bind(PushConfig, PushConfig("app_123", "push_api_key")).singleton()

        # Named service bindings
        self.bind(INotificationService, EmailNotificationService, name="email_service").singleton()
        self.bind(INotificationService, SMSNotificationService, name="sms_service").singleton()
        self.bind(INotificationService, PushNotificationService, name="push_service").singleton()

        # Factory
        self.bind(INotificationFactory, NotificationFactory).singleton()
        self.bind(NotificationManager, NotificationManager).singleton()

# Usage Example
async def factory_example():
    container = InjectQ()
    container.install(NotificationModule())

    manager = container.get(NotificationManager)

    # Send single notification
    result = await manager.send_notification("email", "Hello World!", "user@example.com")
    print(f"Email sent: {result}")

    # Send multi-channel notification
    results = await manager.send_multi_channel(
        "Important Alert!",
        "user@example.com",
        ["email", "sms", "push"]
    )
    print(f"Multi-channel results: {results}")
```

### Abstract Factory

```python
# abstract_factory.py
from abc import ABC, abstractmethod
from injectq import InjectQ, inject, Module
from enum import Enum

class Environment(Enum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TESTING = "testing"

# Abstract Products
class IDatabase(ABC):
    @abstractmethod
    async def connect(self) -> bool:
        pass
    
    @abstractmethod
    async def query(self, sql: str) -> list:
        pass

class ICache(ABC):
    @abstractmethod
    async def get(self, key: str):
        pass
    
    @abstractmethod
    async def set(self, key: str, value, ttl: int = 300):
        pass

class ILogger(ABC):
    @abstractmethod
    def log(self, level: str, message: str):
        pass

# Development Environment Products
class SQLiteDatabase(IDatabase):
    @inject
    def __init__(self, config: DatabaseConfig):
        self.config = config

    async def connect(self) -> bool:
        print("Connected to SQLite database")
        return True

    async def query(self, sql: str) -> list:
        print(f"SQLite query: {sql}")
        return []

class InMemoryCache(ICache):
    def __init__(self):
        self._cache = {}

    async def get(self, key: str):
        return self._cache.get(key)

    async def set(self, key: str, value, ttl: int = 300):
        self._cache[key] = value

class ConsoleLogger(ILogger):
    def log(self, level: str, message: str):
        print(f"[{level}] {message}")

# Production Environment Products
class PostgreSQLDatabase(IDatabase):
    @inject
    def __init__(self, config: DatabaseConfig):
        self.config = config

    async def connect(self) -> bool:
        print("Connected to PostgreSQL database")
        return True

    async def query(self, sql: str) -> list:
        print(f"PostgreSQL query: {sql}")
        return []

class RedisCache(ICache):
    @inject
    def __init__(self, cache_config: CacheConfig):
        self.config = cache_config

    async def get(self, key: str):
        print(f"Redis GET: {key}")
        return None

    async def set(self, key: str, value, ttl: int = 300):
        print(f"Redis SET: {key} = {value} (TTL: {ttl})")

class FileLogger(ILogger):
    @inject
    def __init__(self, logger_config: LoggerConfig):
        self.config = logger_config

    def log(self, level: str, message: str):
        print(f"File log [{level}]: {message}")

# Testing Environment Products
class MockDatabase(IDatabase):
    async def connect(self) -> bool:
        print("Connected to mock database")
        return True

    async def query(self, sql: str) -> list:
        print(f"Mock query: {sql}")
        return [{"id": 1, "name": "test"}]

class MockCache(ICache):
    async def get(self, key: str):
        return f"mock_value_for_{key}"

    async def set(self, key: str, value, ttl: int = 300):
        pass

class MockLogger(ILogger):
    def log(self, level: str, message: str):
        pass  # Silent in tests

# Configuration Classes
class DatabaseConfig:
    def __init__(self, host: str, port: int, database: str):
        self.host = host
        self.port = port
        self.database = database

class CacheConfig:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port

class LoggerConfig:
    def __init__(self, log_file: str, level: str):
        self.log_file = log_file
        self.level = level

# Abstract Factory
class IInfrastructureFactory(ABC):
    @abstractmethod
    def create_database(self) -> IDatabase:
        pass
    
    @abstractmethod
    def create_cache(self) -> ICache:
        pass
    
    @abstractmethod
    def create_logger(self) -> ILogger:
        pass

# Concrete Factories
class DevelopmentInfrastructureFactory(IInfrastructureFactory):
    @inject
    def __init__(self, container: InjectQ):
        self.container = container

    def create_database(self) -> IDatabase:
        return self.container.get(IDatabase, name="sqlite")

    def create_cache(self) -> ICache:
        return self.container.get(ICache, name="memory")

    def create_logger(self) -> ILogger:
        return self.container.get(ILogger, name="console")

class ProductionInfrastructureFactory(IInfrastructureFactory):
    @inject
    def __init__(self, container: InjectQ):
        self.container = container

    def create_database(self) -> IDatabase:
        return self.container.get(IDatabase, name="postgresql")

    def create_cache(self) -> ICache:
        return self.container.get(ICache, name="redis")

    def create_logger(self) -> ILogger:
        return self.container.get(ILogger, name="file")

class TestingInfrastructureFactory(IInfrastructureFactory):
    @inject
    def __init__(self, container: InjectQ):
        self.container = container

    def create_database(self) -> IDatabase:
        return self.container.get(IDatabase, name="mock")

    def create_cache(self) -> ICache:
        return self.container.get(ICache, name="mock_cache")

    def create_logger(self) -> ILogger:
        return self.container.get(ILogger, name="mock_logger")

# Application Service
class ApplicationService:
    @inject
    def __init__(self, infrastructure_factory: IInfrastructureFactory):
        self.factory = infrastructure_factory
        self.database = None
        self.cache = None
        self.logger = None

    async def initialize(self):
        """Initialize infrastructure components."""
        self.database = self.factory.create_database()
        self.cache = self.factory.create_cache()
        self.logger = self.factory.create_logger()

        await self.database.connect()
        self.logger.log("INFO", "Application initialized")

    async def process_data(self, data: dict):
        """Process some data using infrastructure."""
        self.logger.log("INFO", f"Processing data: {data}")

        # Check cache first
        cache_key = f"data_{data.get('id')}"
        cached_result = await self.cache.get(cache_key)
        
        if cached_result:
            self.logger.log("INFO", "Cache hit")
            return cached_result

        # Query database
        result = await self.database.query(f"SELECT * FROM data WHERE id = {data.get('id')}")
        
        # Cache result
        await self.cache.set(cache_key, result)
        
        self.logger.log("INFO", "Data processed successfully")
        return result

# Environment-specific Modules
class DevelopmentModule(Module):
    def configure(self):
        # Configuration
        self.bind(DatabaseConfig, DatabaseConfig("localhost", 5432, "dev_db")).singleton()
        
        # Infrastructure components
        self.bind(IDatabase, SQLiteDatabase, name="sqlite").singleton()
        self.bind(ICache, InMemoryCache, name="memory").singleton()
        self.bind(ILogger, ConsoleLogger, name="console").singleton()
        
        # Factory
        self.bind(IInfrastructureFactory, DevelopmentInfrastructureFactory).singleton()

class ProductionModule(Module):
    def configure(self):
        # Configuration
        self.bind(DatabaseConfig, DatabaseConfig("prod-db.example.com", 5432, "prod_db")).singleton()
        self.bind(CacheConfig, CacheConfig("redis.example.com", 6379)).singleton()
        self.bind(LoggerConfig, LoggerConfig("/var/log/app.log", "INFO")).singleton()
        
        # Infrastructure components
        self.bind(IDatabase, PostgreSQLDatabase, name="postgresql").singleton()
        self.bind(ICache, RedisCache, name="redis").singleton()
        self.bind(ILogger, FileLogger, name="file").singleton()
        
        # Factory
        self.bind(IInfrastructureFactory, ProductionInfrastructureFactory).singleton()

class TestingModule(Module):
    def configure(self):
        # Infrastructure components
        self.bind(IDatabase, MockDatabase, name="mock").singleton()
        self.bind(ICache, MockCache, name="mock_cache").singleton()
        self.bind(ILogger, MockLogger, name="mock_logger").singleton()
        
        # Factory
        self.bind(IInfrastructureFactory, TestingInfrastructureFactory).singleton()

# Factory Provider
class InfrastructureFactoryProvider:
    @staticmethod
    def get_module(environment: Environment) -> Module:
        if environment == Environment.DEVELOPMENT:
            return DevelopmentModule()
        elif environment == Environment.PRODUCTION:
            return ProductionModule()
        elif environment == Environment.TESTING:
            return TestingModule()
        else:
            raise ValueError(f"Unsupported environment: {environment}")

# Usage Example
async def abstract_factory_example():
    # Change environment here
    current_env = Environment.DEVELOPMENT
    
    container = InjectQ()
    module = InfrastructureFactoryProvider.get_module(current_env)
    container.install(module)
    
    # Application always works the same regardless of environment
    service = container.get(ApplicationService)
    await service.initialize()
    
    result = await service.process_data({"id": 123, "name": "test"})
    print(f"Processing result: {result}")
```

## 🔍 Observer Pattern

The Observer pattern allows objects to be notified of changes without tight coupling. InjectQ makes this pattern clean through interface injection.

```python
# observer_pattern.py
from abc import ABC, abstractmethod
from injectq import InjectQ, inject, Module
from typing import List, Dict, Any
import asyncio

# Subject Interface
class ISubject(ABC):
    @abstractmethod
    def attach(self, observer: 'IObserver'):
        pass
    
    @abstractmethod
    def detach(self, observer: 'IObserver'):
        pass
    
    @abstractmethod
    async def notify(self, event_type: str, data: Dict[str, Any]):
        pass

# Observer Interface
class IObserver(ABC):
    @abstractmethod
    async def update(self, subject: ISubject, event_type: str, data: Dict[str, Any]):
        pass

# Concrete Subject
class UserManager(ISubject):
    def __init__(self):
        self._observers: List[IObserver] = []
        self._users: Dict[str, Dict] = {}

    def attach(self, observer: IObserver):
        if observer not in self._observers:
            self._observers.append(observer)

    def detach(self, observer: IObserver):
        if observer in self._observers:
            self._observers.remove(observer)

    async def notify(self, event_type: str, data: Dict[str, Any]):
        for observer in self._observers:
            try:
                await observer.update(self, event_type, data)
            except Exception as e:
                print(f"Error notifying observer {observer.__class__.__name__}: {e}")

    async def create_user(self, user_id: str, user_data: Dict[str, Any]):
        self._users[user_id] = user_data
        await self.notify("user_created", {"user_id": user_id, "user_data": user_data})

    async def update_user(self, user_id: str, updates: Dict[str, Any]):
        if user_id in self._users:
            old_data = self._users[user_id].copy()
            self._users[user_id].update(updates)
            await self.notify("user_updated", {
                "user_id": user_id,
                "old_data": old_data,
                "new_data": self._users[user_id]
            })

    async def delete_user(self, user_id: str):
        if user_id in self._users:
            user_data = self._users.pop(user_id)
            await self.notify("user_deleted", {"user_id": user_id, "user_data": user_data})

    def get_user(self, user_id: str) -> Dict[str, Any]:
        return self._users.get(user_id, {})

# Concrete Observers
class EmailNotificationObserver(IObserver):
    @inject
    def __init__(self, email_service: EmailService):
        self.email_service = email_service

    async def update(self, subject: ISubject, event_type: str, data: Dict[str, Any]):
        if event_type == "user_created":
            await self._send_welcome_email(data)
        elif event_type == "user_updated":
            await self._send_update_notification(data)
        elif event_type == "user_deleted":
            await self._send_goodbye_email(data)

    async def _send_welcome_email(self, data: Dict[str, Any]):
        user_data = data["user_data"]
        await self.email_service.send_email(
            to=user_data.get("email"),
            subject="Welcome!",
            body="Welcome to our platform!"
        )

    async def _send_update_notification(self, data: Dict[str, Any]):
        user_data = data["new_data"]
        await self.email_service.send_email(
            to=user_data.get("email"),
            subject="Profile Updated",
            body="Your profile has been updated."
        )

    async def _send_goodbye_email(self, data: Dict[str, Any]):
        user_data = data["user_data"]
        await self.email_service.send_email(
            to=user_data.get("email"),
            subject="Account Deleted",
            body="Sorry to see you go!"
        )

class AuditLogObserver(IObserver):
    @inject
    def __init__(self, audit_service: AuditService):
        self.audit_service = audit_service

    async def update(self, subject: ISubject, event_type: str, data: Dict[str, Any]):
        await self.audit_service.log_event(event_type, data)

class AnalyticsObserver(IObserver):
    @inject
    def __init__(self, analytics_service: AnalyticsService):
        self.analytics_service = analytics_service

    async def update(self, subject: ISubject, event_type: str, data: Dict[str, Any]):
        if event_type == "user_created":
            await self.analytics_service.track_user_registration(data["user_id"])
        elif event_type == "user_deleted":
            await self.analytics_service.track_user_churn(data["user_id"])

class CacheInvalidationObserver(IObserver):
    @inject
    def __init__(self, cache_service: CacheService):
        self.cache_service = cache_service

    async def update(self, subject: ISubject, event_type: str, data: Dict[str, Any]):
        user_id = data["user_id"]
        cache_keys = [
            f"user:{user_id}",
            f"user_profile:{user_id}",
            f"user_permissions:{user_id}"
        ]
        
        for key in cache_keys:
            await self.cache_service.delete(key)

# Supporting Services
class EmailService:
    async def send_email(self, to: str, subject: str, body: str):
        print(f"Sending email to {to}: {subject}")
        await asyncio.sleep(0.1)  # Simulate network delay

class AuditService:
    def __init__(self):
        self.audit_log = []

    async def log_event(self, event_type: str, data: Dict[str, Any]):
        log_entry = {
            "timestamp": asyncio.get_event_loop().time(),
            "event_type": event_type,
            "data": data
        }
        self.audit_log.append(log_entry)
        print(f"Audit log: {event_type} - {data}")

class AnalyticsService:
    def __init__(self):
        self.metrics = {"registrations": 0, "churn": 0}

    async def track_user_registration(self, user_id: str):
        self.metrics["registrations"] += 1
        print(f"Analytics: User registration tracked for {user_id}")

    async def track_user_churn(self, user_id: str):
        self.metrics["churn"] += 1
        print(f"Analytics: User churn tracked for {user_id}")

class CacheService:
    def __init__(self):
        self.cache = {}

    async def delete(self, key: str):
        self.cache.pop(key, None)
        print(f"Cache: Invalidated key {key}")

# Observer Manager
class ObserverManager:
    @inject
    def __init__(
        self,
        user_manager: UserManager,
        email_observer: EmailNotificationObserver,
        audit_observer: AuditLogObserver,
        analytics_observer: AnalyticsObserver,
        cache_observer: CacheInvalidationObserver
    ):
        self.user_manager = user_manager
        self.observers = [
            email_observer,
            audit_observer,
            analytics_observer,
            cache_observer
        ]

    def setup_observers(self):
        """Attach all observers to the subject."""
        for observer in self.observers:
            self.user_manager.attach(observer)

    def teardown_observers(self):
        """Detach all observers from the subject."""
        for observer in self.observers:
            self.user_manager.detach(observer)

# Module Configuration
class ObserverModule(Module):
    def configure(self):
        # Services
        self.bind(EmailService, EmailService).singleton()
        self.bind(AuditService, AuditService).singleton()
        self.bind(AnalyticsService, AnalyticsService).singleton()
        self.bind(CacheService, CacheService).singleton()

        # Subject
        self.bind(UserManager, UserManager).singleton()

        # Observers
        self.bind(EmailNotificationObserver, EmailNotificationObserver).singleton()
        self.bind(AuditLogObserver, AuditLogObserver).singleton()
        self.bind(AnalyticsObserver, AnalyticsObserver).singleton()
        self.bind(CacheInvalidationObserver, CacheInvalidationObserver).singleton()

        # Manager
        self.bind(ObserverManager, ObserverManager).singleton()

# Usage Example
async def observer_example():
    container = InjectQ()
    container.install(ObserverModule())

    # Setup observer pattern
    observer_manager = container.get(ObserverManager)
    observer_manager.setup_observers()

    user_manager = container.get(UserManager)

    # Perform user operations - observers will be notified automatically
    await user_manager.create_user("user123", {
        "name": "John Doe",
        "email": "john@example.com",
        "age": 30
    })

    await user_manager.update_user("user123", {"age": 31})

    await user_manager.delete_user("user123")

    # Cleanup
    observer_manager.teardown_observers()
```

## 🎭 Strategy Pattern

The Strategy pattern enables selecting algorithms at runtime. InjectQ makes strategy injection and swapping elegant.

```python
# strategy_pattern.py
from abc import ABC, abstractmethod
from injectq import InjectQ, inject, Module
from typing import List, Dict, Any
from enum import Enum

# Strategy Interface
class IPaymentStrategy(ABC):
    @abstractmethod
    async def process_payment(self, amount: float, payment_details: Dict[str, Any]) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    def get_fees(self, amount: float) -> float:
        pass

# Concrete Strategies
class CreditCardStrategy(IPaymentStrategy):
    @inject
    def __init__(self, card_processor: CardProcessor):
        self.processor = card_processor

    async def process_payment(self, amount: float, payment_details: Dict[str, Any]) -> Dict[str, Any]:
        card_number = payment_details["card_number"]
        cvv = payment_details["cvv"]
        expiry = payment_details["expiry"]

        # Validate card
        if not self._validate_card(card_number, cvv, expiry):
            return {"success": False, "error": "Invalid card details"}

        # Process payment
        result = await self.processor.charge_card(card_number, amount)
        
        return {
            "success": result["success"],
            "transaction_id": result.get("transaction_id"),
            "fees": self.get_fees(amount),
            "method": "credit_card"
        }

    def get_fees(self, amount: float) -> float:
        return amount * 0.029  # 2.9% fee

    def _validate_card(self, card_number: str, cvv: str, expiry: str) -> bool:
        # Simplified validation
        return len(card_number) == 16 and len(cvv) == 3

class PayPalStrategy(IPaymentStrategy):
    @inject
    def __init__(self, paypal_client: PayPalClient):
        self.client = paypal_client

    async def process_payment(self, amount: float, payment_details: Dict[str, Any]) -> Dict[str, Any]:
        email = payment_details["email"]
        
        # Process through PayPal
        result = await self.client.create_payment(email, amount)
        
        return {
            "success": result["success"],
            "transaction_id": result.get("transaction_id"),
            "fees": self.get_fees(amount),
            "method": "paypal",
            "redirect_url": result.get("redirect_url")
        }

    def get_fees(self, amount: float) -> float:
        return amount * 0.035 + 0.30  # 3.5% + $0.30

class BankTransferStrategy(IPaymentStrategy):
    @inject
    def __init__(self, bank_client: BankClient):
        self.client = bank_client

    async def process_payment(self, amount: float, payment_details: Dict[str, Any]) -> Dict[str, Any]:
        account_number = payment_details["account_number"]
        routing_number = payment_details["routing_number"]
        
        # Process bank transfer
        result = await self.client.initiate_transfer(account_number, routing_number, amount)
        
        return {
            "success": result["success"],
            "transaction_id": result.get("transaction_id"),
            "fees": self.get_fees(amount),
            "method": "bank_transfer",
            "processing_time": "3-5 business days"
        }

    def get_fees(self, amount: float) -> float:
        return 1.00 if amount > 100 else 0.50  # Flat fee

class CryptocurrencyStrategy(IPaymentStrategy):
    @inject
    def __init__(self, crypto_client: CryptoClient):
        self.client = crypto_client

    async def process_payment(self, amount: float, payment_details: Dict[str, Any]) -> Dict[str, Any]:
        wallet_address = payment_details["wallet_address"]
        crypto_type = payment_details.get("crypto_type", "BTC")
        
        # Convert USD to crypto
        crypto_amount = await self.client.convert_usd_to_crypto(amount, crypto_type)
        
        # Process crypto payment
        result = await self.client.send_crypto(wallet_address, crypto_amount, crypto_type)
        
        return {
            "success": result["success"],
            "transaction_id": result.get("transaction_id"),
            "fees": self.get_fees(amount),
            "method": "cryptocurrency",
            "crypto_amount": crypto_amount,
            "crypto_type": crypto_type
        }

    def get_fees(self, amount: float) -> float:
        return amount * 0.015  # 1.5% fee

# Payment Processors
class CardProcessor:
    async def charge_card(self, card_number: str, amount: float) -> Dict[str, Any]:
        # Simulate card processing
        import random
        success = random.random() > 0.1  # 90% success rate
        
        if success:
            return {
                "success": True,
                "transaction_id": f"cc_{card_number[-4:]}_{int(amount*100)}"
            }
        else:
            return {"success": False, "error": "Card declined"}

class PayPalClient:
    async def create_payment(self, email: str, amount: float) -> Dict[str, Any]:
        # Simulate PayPal API call
        return {
            "success": True,
            "transaction_id": f"pp_{email.split('@')[0]}_{int(amount*100)}",
            "redirect_url": f"https://paypal.com/checkout?amount={amount}"
        }

class BankClient:
    async def initiate_transfer(self, account: str, routing: str, amount: float) -> Dict[str, Any]:
        # Simulate bank transfer
        return {
            "success": True,
            "transaction_id": f"bt_{account[-4:]}_{int(amount*100)}"
        }

class CryptoClient:
    async def convert_usd_to_crypto(self, usd_amount: float, crypto_type: str) -> float:
        # Simulate conversion rates
        rates = {"BTC": 0.000025, "ETH": 0.0005, "LTC": 0.01}
        return usd_amount * rates.get(crypto_type, 0.000025)

    async def send_crypto(self, wallet: str, amount: float, crypto_type: str) -> Dict[str, Any]:
        # Simulate crypto transaction
        return {
            "success": True,
            "transaction_id": f"crypto_{crypto_type}_{wallet[-8:]}_{int(amount*1000000)}"
        }

# Context Class
class PaymentProcessor:
    @inject
    def __init__(self):
        self._strategy: IPaymentStrategy = None

    def set_strategy(self, strategy: IPaymentStrategy):
        """Set the payment strategy at runtime."""
        self._strategy = strategy

    async def process_payment(self, amount: float, payment_details: Dict[str, Any]) -> Dict[str, Any]:
        if not self._strategy:
            raise ValueError("Payment strategy not set")
        
        return await self._strategy.process_payment(amount, payment_details)

    def calculate_total_with_fees(self, amount: float) -> float:
        if not self._strategy:
            raise ValueError("Payment strategy not set")
        
        fees = self._strategy.get_fees(amount)
        return amount + fees

# Strategy Factory
class PaymentStrategyFactory:
    @inject
    def __init__(self, container: InjectQ):
        self.container = container
        self._strategies = {
            "credit_card": "credit_card_strategy",
            "paypal": "paypal_strategy",
            "bank_transfer": "bank_transfer_strategy",
            "cryptocurrency": "crypto_strategy"
        }

    def create_strategy(self, payment_method: str) -> IPaymentStrategy:
        strategy_name = self._strategies.get(payment_method)
        if not strategy_name:
            raise ValueError(f"Unsupported payment method: {payment_method}")
        
        return self.container.get(IPaymentStrategy, name=strategy_name)

# Payment Service
class PaymentService:
    @inject
    def __init__(
        self,
        processor: PaymentProcessor,
        strategy_factory: PaymentStrategyFactory
    ):
        self.processor = processor
        self.factory = strategy_factory

    async def process_payment_with_method(
        self,
        payment_method: str,
        amount: float,
        payment_details: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process payment with specified method."""
        try:
            # Get appropriate strategy
            strategy = self.factory.create_strategy(payment_method)
            
            # Set strategy
            self.processor.set_strategy(strategy)
            
            # Calculate total with fees
            total_amount = self.processor.calculate_total_with_fees(amount)
            
            # Process payment
            result = await self.processor.process_payment(amount, payment_details)
            result["original_amount"] = amount
            result["total_amount"] = total_amount
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "method": payment_method
            }

    async def find_best_payment_method(
        self,
        amount: float,
        available_methods: List[str]
    ) -> Dict[str, Any]:
        """Find the payment method with lowest fees."""
        best_method = None
        lowest_fees = float('inf')
        
        for method in available_methods:
            try:
                strategy = self.factory.create_strategy(method)
                fees = strategy.get_fees(amount)
                
                if fees < lowest_fees:
                    lowest_fees = fees
                    best_method = method
            except ValueError:
                continue  # Skip unsupported methods
        
        if best_method:
            return {
                "method": best_method,
                "fees": lowest_fees,
                "total": amount + lowest_fees
            }
        else:
            return {"error": "No supported payment methods found"}

# Module Configuration
class PaymentModule(Module):
    def configure(self):
        # Payment processors
        self.bind(CardProcessor, CardProcessor).singleton()
        self.bind(PayPalClient, PayPalClient).singleton()
        self.bind(BankClient, BankClient).singleton()
        self.bind(CryptoClient, CryptoClient).singleton()

        # Payment strategies
        self.bind(IPaymentStrategy, CreditCardStrategy, name="credit_card_strategy").scoped()
        self.bind(IPaymentStrategy, PayPalStrategy, name="paypal_strategy").scoped()
        self.bind(IPaymentStrategy, BankTransferStrategy, name="bank_transfer_strategy").scoped()
        self.bind(IPaymentStrategy, CryptocurrencyStrategy, name="crypto_strategy").scoped()

        # Context and factory
        self.bind(PaymentProcessor, PaymentProcessor).scoped()
        self.bind(PaymentStrategyFactory, PaymentStrategyFactory).singleton()

        # Service
        self.bind(PaymentService, PaymentService).scoped()

# Usage Examples
async def strategy_example():
    container = InjectQ()
    container.install(PaymentModule())

    service = container.get(PaymentService)

    # Process credit card payment
    cc_result = await service.process_payment_with_method(
        "credit_card",
        100.0,
        {
            "card_number": "1234567890123456",
            "cvv": "123",
            "expiry": "12/25"
        }
    )
    print(f"Credit card payment: {cc_result}")

    # Process PayPal payment
    paypal_result = await service.process_payment_with_method(
        "paypal",
        100.0,
        {"email": "user@example.com"}
    )
    print(f"PayPal payment: {paypal_result}")

    # Find best payment method
    best_method = await service.find_best_payment_method(
        100.0,
        ["credit_card", "paypal", "bank_transfer", "cryptocurrency"]
    )
    print(f"Best payment method: {best_method}")

    # Process with best method
    if "method" in best_method:
        best_result = await service.process_payment_with_method(
            best_method["method"],
            100.0,
            {"account_number": "123456789", "routing_number": "987654321"}
        )
        print(f"Best method payment: {best_result}")
```

## 🏗️ Builder Pattern

The Builder pattern constructs complex objects step by step. InjectQ can inject builders and their dependencies cleanly.

```python
# builder_pattern.py
from abc import ABC, abstractmethod
from injectq import InjectQ, inject, Module
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field

# Product Classes
@dataclass
class DatabaseConfig:
    host: str = "localhost"
    port: int = 5432
    database: str = "app"
    username: Optional[str] = None
    password: Optional[str] = None
    ssl_enabled: bool = False
    connection_pool_size: int = 10
    timeout: int = 30
    retry_attempts: int = 3

@dataclass
class CacheConfig:
    host: str = "localhost"
    port: int = 6379
    password: Optional[str] = None
    database: int = 0
    ttl: int = 300
    max_connections: int = 10

@dataclass
class LoggingConfig:
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_path: Optional[str] = None
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    console_output: bool = True

@dataclass
class SecurityConfig:
    jwt_secret: str = "default_secret"
    jwt_expiration: int = 3600
    password_hash_rounds: int = 12
    require_https: bool = False
    cors_origins: List[str] = field(default_factory=list)
    rate_limit_requests: int = 100
    rate_limit_window: int = 60

@dataclass
class ApplicationConfig:
    app_name: str = "MyApp"
    version: str = "1.0.0"
    debug: bool = False
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    custom_settings: Dict[str, Any] = field(default_factory=dict)

# Builder Interface
class IConfigBuilder(ABC):
    @abstractmethod
    def reset(self) -> 'IConfigBuilder':
        pass
    
    @abstractmethod
    def build(self) -> ApplicationConfig:
        pass

# Concrete Builder
class ApplicationConfigBuilder(IConfigBuilder):
    @inject
    def __init__(self, default_provider: DefaultConfigProvider):
        self.default_provider = default_provider
        self.reset()

    def reset(self) -> 'ApplicationConfigBuilder':
        """Reset the builder to start fresh."""
        self._config = ApplicationConfig()
        return self

    def build(self) -> ApplicationConfig:
        """Build and return the final configuration."""
        # Apply any default validations or final processing
        self._validate_config()
        return self._config

    # App-level configuration
    def with_app_info(self, name: str, version: str = "1.0.0") -> 'ApplicationConfigBuilder':
        self._config.app_name = name
        self._config.version = version
        return self

    def with_debug(self, debug: bool = True) -> 'ApplicationConfigBuilder':
        self._config.debug = debug
        return self

    # Database configuration
    def with_database(
        self,
        host: str = "localhost",
        port: int = 5432,
        database: str = "app",
        username: Optional[str] = None,
        password: Optional[str] = None
    ) -> 'ApplicationConfigBuilder':
        self._config.database = DatabaseConfig(
            host=host,
            port=port,
            database=database,
            username=username,
            password=password
        )
        return self

    def with_database_ssl(self, enabled: bool = True) -> 'ApplicationConfigBuilder':
        self._config.database.ssl_enabled = enabled
        return self

    def with_database_pool(
        self,
        pool_size: int = 10,
        timeout: int = 30,
        retry_attempts: int = 3
    ) -> 'ApplicationConfigBuilder':
        self._config.database.connection_pool_size = pool_size
        self._config.database.timeout = timeout
        self._config.database.retry_attempts = retry_attempts
        return self

    # Cache configuration
    def with_cache(
        self,
        host: str = "localhost",
        port: int = 6379,
        password: Optional[str] = None,
        database: int = 0
    ) -> 'ApplicationConfigBuilder':
        self._config.cache = CacheConfig(
            host=host,
            port=port,
            password=password,
            database=database
        )
        return self

    def with_cache_settings(
        self,
        ttl: int = 300,
        max_connections: int = 10
    ) -> 'ApplicationConfigBuilder':
        self._config.cache.ttl = ttl
        self._config.cache.max_connections = max_connections
        return self

    # Logging configuration
    def with_logging(
        self,
        level: str = "INFO",
        console_output: bool = True
    ) -> 'ApplicationConfigBuilder':
        self._config.logging = LoggingConfig(
            level=level,
            console_output=console_output
        )
        return self

    def with_file_logging(
        self,
        file_path: str,
        max_size: int = 10 * 1024 * 1024,
        backup_count: int = 5
    ) -> 'ApplicationConfigBuilder':
        self._config.logging.file_path = file_path
        self._config.logging.max_file_size = max_size
        self._config.logging.backup_count = backup_count
        return self

    def with_log_format(self, format_string: str) -> 'ApplicationConfigBuilder':
        self._config.logging.format = format_string
        return self

    # Security configuration
    def with_security(
        self,
        jwt_secret: str,
        jwt_expiration: int = 3600,
        password_hash_rounds: int = 12
    ) -> 'ApplicationConfigBuilder':
        self._config.security = SecurityConfig(
            jwt_secret=jwt_secret,
            jwt_expiration=jwt_expiration,
            password_hash_rounds=password_hash_rounds
        )
        return self

    def with_https(self, require_https: bool = True) -> 'ApplicationConfigBuilder':
        self._config.security.require_https = require_https
        return self

    def with_cors(self, origins: List[str]) -> 'ApplicationConfigBuilder':
        self._config.security.cors_origins = origins
        return self

    def with_rate_limiting(
        self,
        requests: int = 100,
        window: int = 60
    ) -> 'ApplicationConfigBuilder':
        self._config.security.rate_limit_requests = requests
        self._config.security.rate_limit_window = window
        return self

    # Custom settings
    def with_custom_setting(self, key: str, value: Any) -> 'ApplicationConfigBuilder':
        self._config.custom_settings[key] = value
        return self

    def with_custom_settings(self, settings: Dict[str, Any]) -> 'ApplicationConfigBuilder':
        self._config.custom_settings.update(settings)
        return self

    # Preset configurations
    def for_development(self) -> 'ApplicationConfigBuilder':
        """Apply development preset."""
        return (self
                .with_debug(True)
                .with_database("localhost", 5432, "dev_db")
                .with_cache("localhost", 6379)
                .with_logging("DEBUG", console_output=True)
                .with_security("dev_secret", jwt_expiration=7200)
                .with_cors(["http://localhost:3000", "http://localhost:8080"]))

    def for_production(self) -> 'ApplicationConfigBuilder':
        """Apply production preset."""
        prod_secret = self.default_provider.get_jwt_secret()
        db_config = self.default_provider.get_production_database_config()
        
        return (self
                .with_debug(False)
                .with_database(
                    db_config["host"],
                    db_config["port"],
                    db_config["database"],
                    db_config["username"],
                    db_config["password"]
                )
                .with_database_ssl(True)
                .with_database_pool(20, 60, 5)
                .with_cache("redis-prod.example.com", 6379, password="redis_password")
                .with_cache_settings(ttl=600, max_connections=20)
                .with_logging("INFO", console_output=False)
                .with_file_logging("/var/log/app.log", 50 * 1024 * 1024, 10)
                .with_security(prod_secret, jwt_expiration=3600, password_hash_rounds=15)
                .with_https(True)
                .with_rate_limiting(500, 60))

    def for_testing(self) -> 'ApplicationConfigBuilder':
        """Apply testing preset."""
        return (self
                .with_debug(True)
                .with_database("localhost", 5432, "test_db")
                .with_cache("localhost", 6379, database=1)
                .with_logging("DEBUG", console_output=False)
                .with_security("test_secret", jwt_expiration=300))

    def _validate_config(self):
        """Validate the configuration."""
        if not self._config.app_name:
            raise ValueError("App name is required")
        
        if self._config.security.require_https and self._config.debug:
            print("Warning: HTTPS required but debug mode is enabled")
        
        if self._config.database.connection_pool_size < 1:
            raise ValueError("Database connection pool size must be at least 1")

# Configuration Provider
class DefaultConfigProvider:
    @inject
    def __init__(self, env_reader: EnvironmentReader):
        self.env_reader = env_reader

    def get_jwt_secret(self) -> str:
        """Get JWT secret from environment or generate default."""
        secret = self.env_reader.get("JWT_SECRET")
        if not secret:
            import secrets
            secret = secrets.token_hex(32)
            print(f"Generated JWT secret: {secret}")
        return secret

    def get_production_database_config(self) -> Dict[str, Any]:
        """Get production database configuration."""
        return {
            "host": self.env_reader.get("DB_HOST", "localhost"),
            "port": int(self.env_reader.get("DB_PORT", "5432")),
            "database": self.env_reader.get("DB_NAME", "prod_db"),
            "username": self.env_reader.get("DB_USER", "postgres"),
            "password": self.env_reader.get("DB_PASSWORD", "")
        }

class EnvironmentReader:
    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get environment variable."""
        import os
        return os.getenv(key, default)

# Director Class
class ConfigurationDirector:
    @inject
    def __init__(self, builder: ApplicationConfigBuilder):
        self.builder = builder

    def create_development_config(self, app_name: str) -> ApplicationConfig:
        """Create a development configuration."""
        return (self.builder
                .reset()
                .with_app_info(app_name, "1.0.0-dev")
                .for_development()
                .with_custom_setting("hot_reload", True)
                .with_custom_setting("mock_external_apis", True)
                .build())

    def create_production_config(self, app_name: str, version: str) -> ApplicationConfig:
        """Create a production configuration."""
        return (self.builder
                .reset()
                .with_app_info(app_name, version)
                .for_production()
                .with_custom_setting("monitoring_enabled", True)
                .with_custom_setting("metrics_collection", True)
                .build())

    def create_testing_config(self, app_name: str) -> ApplicationConfig:
        """Create a testing configuration."""
        return (self.builder
                .reset()
                .with_app_info(app_name, "test")
                .for_testing()
                .with_custom_setting("test_mode", True)
                .with_custom_setting("disable_external_calls", True)
                .build())

    def create_microservice_config(
        self,
        service_name: str,
        service_port: int,
        dependencies: List[str]
    ) -> ApplicationConfig:
        """Create a microservice configuration."""
        return (self.builder
                .reset()
                .with_app_info(service_name)
                .for_production()
                .with_custom_setting("service_port", service_port)
                .with_custom_setting("service_dependencies", dependencies)
                .with_custom_setting("health_check_enabled", True)
                .with_custom_setting("distributed_tracing", True)
                .build())

# Configuration Manager
class ConfigurationManager:
    @inject
    def __init__(self, director: ConfigurationDirector):
        self.director = director
        self._configs: Dict[str, ApplicationConfig] = {}

    def get_or_create_config(
        self,
        config_type: str,
        app_name: str,
        **kwargs
    ) -> ApplicationConfig:
        """Get or create configuration by type."""
        cache_key = f"{config_type}_{app_name}"
        
        if cache_key not in self._configs:
            if config_type == "development":
                config = self.director.create_development_config(app_name)
            elif config_type == "production":
                version = kwargs.get("version", "1.0.0")
                config = self.director.create_production_config(app_name, version)
            elif config_type == "testing":
                config = self.director.create_testing_config(app_name)
            elif config_type == "microservice":
                service_port = kwargs.get("service_port", 8080)
                dependencies = kwargs.get("dependencies", [])
                config = self.director.create_microservice_config(
                    app_name, service_port, dependencies
                )
            else:
                raise ValueError(f"Unknown configuration type: {config_type}")
            
            self._configs[cache_key] = config
        
        return self._configs[cache_key]

    def clear_cache(self):
        """Clear configuration cache."""
        self._configs.clear()

# Module Configuration
class BuilderModule(Module):
    def configure(self):
        # Utilities
        self.bind(EnvironmentReader, EnvironmentReader).singleton()
        self.bind(DefaultConfigProvider, DefaultConfigProvider).singleton()

        # Builder
        self.bind(ApplicationConfigBuilder, ApplicationConfigBuilder).scoped()

        # Director
        self.bind(ConfigurationDirector, ConfigurationDirector).scoped()

        # Manager
        self.bind(ConfigurationManager, ConfigurationManager).singleton()

# Usage Examples
async def builder_example():
    container = InjectQ()
    container.install(BuilderModule())

    # Using builder directly
    builder = container.get(ApplicationConfigBuilder)
    
    custom_config = (builder
                     .reset()
                     .with_app_info("CustomApp", "2.0.0")
                     .with_debug(True)
                     .with_database("custom-db.example.com", 5432, "custom_db", "user", "pass")
                     .with_database_ssl(True)
                     .with_cache("redis.example.com", 6379, password="redis_pass")
                     .with_logging("DEBUG")
                     .with_file_logging("/var/log/custom.log")
                     .with_security("super_secret", jwt_expiration=7200)
                     .with_cors(["https://example.com"])
                     .with_custom_settings({"feature_flags": {"new_ui": True}})
                     .build())

    print(f"Custom config: {custom_config.app_name} v{custom_config.version}")

    # Using director for preset configurations
    director = container.get(ConfigurationDirector)
    
    dev_config = director.create_development_config("MyApp")
    print(f"Dev config debug: {dev_config.debug}")
    
    prod_config = director.create_production_config("MyApp", "1.2.3")
    print(f"Prod config HTTPS: {prod_config.security.require_https}")

    # Using configuration manager
    manager = container.get(ConfigurationManager)
    
    test_config = manager.get_or_create_config("testing", "TestApp")
    print(f"Test config: {test_config.custom_settings}")
    
    microservice_config = manager.get_or_create_config(
        "microservice",
        "UserService",
        service_port=8001,
        dependencies=["database", "cache", "auth-service"]
    )
    print(f"Microservice config: {microservice_config.custom_settings}")

if __name__ == "__main__":
    import asyncio
    
    async def main():
        await factory_example()
        print("\n" + "="*50 + "\n")
        await abstract_factory_example()
        print("\n" + "="*50 + "\n")
        await observer_example()
        print("\n" + "="*50 + "\n")
        await strategy_example()
        print("\n" + "="*50 + "\n")
        await builder_example()

    asyncio.run(main())
```

This design patterns section demonstrates:

1. **Factory Pattern**: Creating notification services with named bindings and conditional logic
2. **Abstract Factory**: Environment-specific infrastructure with multiple related products
3. **Observer Pattern**: Event-driven architecture with automatic notifications
4. **Strategy Pattern**: Runtime algorithm selection for payment processing
5. **Builder Pattern**: Complex configuration construction with fluent interface and presets

Each pattern shows:
- Clean interface design
- Proper dependency injection usage
- Realistic business scenarios
- Module configuration patterns
- Error handling and validation
- Testing considerations

Ready to continue with more design patterns or move to the next documentation section?
