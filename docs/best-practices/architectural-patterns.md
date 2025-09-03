# Architectural Design Patterns

This guide demonstrates how to implement clean, maintainable architectures using InjectQ's dependency injection capabilities with proven design patterns and architectural principles.

## 🏗️ Layered Architecture

### Classic Three-Layer Architecture

```python
# layered_architecture.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from injectq import InjectQ, inject, Module

# ==================== DATA LAYER ====================

class IRepository(ABC):
    """Base repository interface."""
    
    @abstractmethod
    async def save(self, entity) -> Any:
        pass
    
    @abstractmethod
    async def find_by_id(self, id: Any) -> Optional[Any]:
        pass
    
    @abstractmethod
    async def find_all(self) -> List[Any]:
        pass
    
    @abstractmethod
    async def delete(self, id: Any) -> bool:
        pass

class IUnitOfWork(ABC):
    """Unit of Work pattern for managing transactions."""
    
    @abstractmethod
    async def begin_transaction(self):
        pass
    
    @abstractmethod
    async def commit(self):
        pass
    
    @abstractmethod
    async def rollback(self):
        pass

@dataclass
class User:
    id: Optional[str] = None
    name: str = ""
    email: str = ""

@dataclass 
class Product:
    id: Optional[str] = None
    name: str = ""
    price: float = 0.0
    category_id: str = ""

class UserRepository(IRepository):
    @inject
    def __init__(self, database: Database, unit_of_work: IUnitOfWork):
        self.db = database
        self.uow = unit_of_work
        self._users: Dict[str, User] = {}  # In-memory for demo
    
    async def save(self, user: User) -> User:
        if not user.id:
            user.id = f"user_{len(self._users) + 1}"
        self._users[user.id] = user
        return user
    
    async def find_by_id(self, user_id: str) -> Optional[User]:
        return self._users.get(user_id)
    
    async def find_all(self) -> List[User]:
        return list(self._users.values())
    
    async def delete(self, user_id: str) -> bool:
        return self._users.pop(user_id, None) is not None
    
    async def find_by_email(self, email: str) -> Optional[User]:
        for user in self._users.values():
            if user.email == email:
                return user
        return None

class ProductRepository(IRepository):
    @inject
    def __init__(self, database: Database, unit_of_work: IUnitOfWork):
        self.db = database
        self.uow = unit_of_work
        self._products: Dict[str, Product] = {}  # In-memory for demo
    
    async def save(self, product: Product) -> Product:
        if not product.id:
            product.id = f"product_{len(self._products) + 1}"
        self._products[product.id] = product
        return product
    
    async def find_by_id(self, product_id: str) -> Optional[Product]:
        return self._products.get(product_id)
    
    async def find_all(self) -> List[Product]:
        return list(self._products.values())
    
    async def delete(self, product_id: str) -> bool:
        return self._products.pop(product_id, None) is not None
    
    async def find_by_category(self, category_id: str) -> List[Product]:
        return [p for p in self._products.values() if p.category_id == category_id]

class Database:
    """Database connection and operations."""
    
    @inject
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.connected = False
    
    async def connect(self):
        self.connected = True
        print(f"Connected to database: {self.config.host}:{self.config.port}")
    
    async def disconnect(self):
        self.connected = False

class UnitOfWork(IUnitOfWork):
    """Concrete implementation of Unit of Work."""
    
    @inject
    def __init__(self, database: Database):
        self.database = database
        self.in_transaction = False
    
    async def begin_transaction(self):
        self.in_transaction = True
        print("Transaction started")
    
    async def commit(self):
        if self.in_transaction:
            print("Transaction committed")
            self.in_transaction = False
    
    async def rollback(self):
        if self.in_transaction:
            print("Transaction rolled back")
            self.in_transaction = False

# ==================== BUSINESS LAYER ====================

class IBusinessService(ABC):
    """Base interface for business services."""
    pass

class UserBusinessService(IBusinessService):
    """Business logic for user operations."""
    
    @inject
    def __init__(
        self,
        user_repository: UserRepository,
        email_service: EmailService,
        unit_of_work: IUnitOfWork
    ):
        self.user_repository = user_repository
        self.email_service = email_service
        self.unit_of_work = unit_of_work
    
    async def create_user(self, name: str, email: str) -> User:
        """Create user with business validation."""
        # Business rule: Check if email already exists
        existing_user = await self.user_repository.find_by_email(email)
        if existing_user:
            raise ValueError("User with this email already exists")
        
        # Business rule: Validate email format
        if "@" not in email:
            raise ValueError("Invalid email format")
        
        await self.unit_of_work.begin_transaction()
        try:
            user = User(name=name, email=email)
            saved_user = await self.user_repository.save(user)
            
            # Business rule: Send welcome email
            await self.email_service.send_welcome_email(saved_user)
            
            await self.unit_of_work.commit()
            return saved_user
            
        except Exception as e:
            await self.unit_of_work.rollback()
            raise
    
    async def update_user(self, user_id: str, updates: Dict[str, Any]) -> Optional[User]:
        """Update user with business validation."""
        user = await self.user_repository.find_by_id(user_id)
        if not user:
            return None
        
        # Business rule: Email cannot be changed to existing email
        if "email" in updates:
            existing_user = await self.user_repository.find_by_email(updates["email"])
            if existing_user and existing_user.id != user_id:
                raise ValueError("Email already in use")
        
        # Apply updates
        for key, value in updates.items():
            if hasattr(user, key):
                setattr(user, key, value)
        
        return await self.user_repository.save(user)
    
    async def deactivate_user(self, user_id: str) -> bool:
        """Deactivate user (business operation)."""
        # In real implementation, this might set an 'active' flag
        # For demo, we'll just log the operation
        user = await self.user_repository.find_by_id(user_id)
        if user:
            print(f"User {user.name} has been deactivated")
            return True
        return False

class ProductBusinessService(IBusinessService):
    """Business logic for product operations."""
    
    @inject
    def __init__(
        self,
        product_repository: ProductRepository,
        pricing_service: PricingService,
        unit_of_work: IUnitOfWork
    ):
        self.product_repository = product_repository
        self.pricing_service = pricing_service
        self.unit_of_work = unit_of_work
    
    async def create_product(self, name: str, base_price: float, category_id: str) -> Product:
        """Create product with business logic."""
        # Business rule: Apply pricing strategy
        final_price = await self.pricing_service.calculate_price(base_price, category_id)
        
        await self.unit_of_work.begin_transaction()
        try:
            product = Product(name=name, price=final_price, category_id=category_id)
            saved_product = await self.product_repository.save(product)
            
            await self.unit_of_work.commit()
            return saved_product
            
        except Exception as e:
            await self.unit_of_work.rollback()
            raise
    
    async def update_product_price(self, product_id: str, new_base_price: float) -> Optional[Product]:
        """Update product price with business rules."""
        product = await self.product_repository.find_by_id(product_id)
        if not product:
            return None
        
        # Business rule: Apply pricing strategy
        final_price = await self.pricing_service.calculate_price(new_base_price, product.category_id)
        product.price = final_price
        
        return await self.product_repository.save(product)

class PricingService:
    """Business service for pricing calculations."""
    
    async def calculate_price(self, base_price: float, category_id: str) -> float:
        """Calculate final price based on category and business rules."""
        # Business rule: Different markup for different categories
        markup_rates = {
            "electronics": 1.15,  # 15% markup
            "books": 1.05,        # 5% markup
            "clothing": 1.20      # 20% markup
        }
        
        markup = markup_rates.get(category_id, 1.10)  # Default 10% markup
        return base_price * markup

class EmailService:
    """Service for email operations."""
    
    async def send_welcome_email(self, user: User):
        """Send welcome email to new user."""
        print(f"Sending welcome email to {user.email}")

# ==================== PRESENTATION LAYER ====================

class IController(ABC):
    """Base interface for controllers."""
    pass

class UserController(IController):
    """Handles user-related HTTP requests."""
    
    @inject
    def __init__(self, user_service: UserBusinessService):
        self.user_service = user_service
    
    async def create_user_endpoint(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle POST /users endpoint."""
        try:
            user = await self.user_service.create_user(
                name=request_data["name"],
                email=request_data["email"]
            )
            
            return {
                "status": "success",
                "data": {
                    "id": user.id,
                    "name": user.name,
                    "email": user.email
                }
            }
            
        except ValueError as e:
            return {
                "status": "error",
                "message": str(e)
            }
        except Exception as e:
            return {
                "status": "error",
                "message": "Internal server error"
            }
    
    async def update_user_endpoint(self, user_id: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle PUT /users/{id} endpoint."""
        try:
            user = await self.user_service.update_user(user_id, request_data)
            
            if user:
                return {
                    "status": "success",
                    "data": {
                        "id": user.id,
                        "name": user.name,
                        "email": user.email
                    }
                }
            else:
                return {
                    "status": "error",
                    "message": "User not found"
                }
                
        except ValueError as e:
            return {
                "status": "error",
                "message": str(e)
            }

class ProductController(IController):
    """Handles product-related HTTP requests."""
    
    @inject
    def __init__(self, product_service: ProductBusinessService):
        self.product_service = product_service
    
    async def create_product_endpoint(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle POST /products endpoint."""
        try:
            product = await self.product_service.create_product(
                name=request_data["name"],
                base_price=request_data["base_price"],
                category_id=request_data["category_id"]
            )
            
            return {
                "status": "success",
                "data": {
                    "id": product.id,
                    "name": product.name,
                    "price": product.price,
                    "category_id": product.category_id
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": "Internal server error"
            }

# ==================== CONFIGURATION ====================

@dataclass
class DatabaseConfig:
    host: str
    port: int
    database: str

class LayeredArchitectureModule(Module):
    """Module configuration for layered architecture."""
    
    def configure(self):
        # Configuration
        self.bind(DatabaseConfig, DatabaseConfig(
            host="localhost",
            port=5432,
            database="app_db"
        )).singleton()
        
        # Data Layer
        self.bind(Database, Database).singleton()
        self.bind(IUnitOfWork, UnitOfWork).scoped()
        self.bind(UserRepository, UserRepository).scoped()
        self.bind(ProductRepository, ProductRepository).scoped()
        
        # Business Layer
        self.bind(PricingService, PricingService).singleton()
        self.bind(EmailService, EmailService).singleton()
        self.bind(UserBusinessService, UserBusinessService).scoped()
        self.bind(ProductBusinessService, ProductBusinessService).scoped()
        
        # Presentation Layer
        self.bind(UserController, UserController).scoped()
        self.bind(ProductController, ProductController).scoped()

# Demo Application
class LayeredApplication:
    @inject
    def __init__(
        self,
        database: Database,
        user_controller: UserController,
        product_controller: ProductController
    ):
        self.database = database
        self.user_controller = user_controller
        self.product_controller = product_controller
    
    async def start(self):
        """Start the application."""
        await self.database.connect()
        print("Layered Architecture Application started")
    
    async def run_demo(self):
        """Demonstrate layered architecture."""
        print("=== Layered Architecture Demo ===\n")
        
        # Create a user
        user_result = await self.user_controller.create_user_endpoint({
            "name": "John Doe",
            "email": "john@example.com"
        })
        print(f"Created user: {user_result}\n")
        
        # Create a product
        product_result = await self.product_controller.create_product_endpoint({
            "name": "Laptop",
            "base_price": 999.99,
            "category_id": "electronics"
        })
        print(f"Created product: {product_result}\n")
        
        # Try to create duplicate user
        duplicate_result = await self.user_controller.create_user_endpoint({
            "name": "Jane Doe",
            "email": "john@example.com"  # Same email
        })
        print(f"Duplicate user attempt: {duplicate_result}")

async def layered_architecture_example():
    container = InjectQ()
    container.install(LayeredArchitectureModule())
    
    app = container.get(LayeredApplication)
    await app.start()
    await app.run_demo()
```

## 🎯 Hexagonal Architecture (Ports and Adapters)

### Domain-Driven Hexagonal Architecture

```python
# hexagonal_architecture.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Protocol
from injectq import InjectQ, inject, Module
from enum import Enum

# ==================== DOMAIN CORE ====================

class OrderStatus(Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"

@dataclass
class OrderItem:
    product_id: str
    product_name: str
    quantity: int
    unit_price: float
    
    @property
    def total_price(self) -> float:
        return self.quantity * self.unit_price

@dataclass
class Order:
    id: Optional[str] = None
    customer_id: str = ""
    items: List[OrderItem] = None
    status: OrderStatus = OrderStatus.PENDING
    total_amount: float = 0.0
    
    def __post_init__(self):
        if self.items is None:
            self.items = []
    
    def add_item(self, item: OrderItem):
        """Domain behavior: Add item to order."""
        self.items.append(item)
        self._calculate_total()
    
    def remove_item(self, product_id: str):
        """Domain behavior: Remove item from order."""
        self.items = [item for item in self.items if item.product_id != product_id]
        self._calculate_total()
    
    def confirm(self):
        """Domain behavior: Confirm the order."""
        if not self.items:
            raise ValueError("Cannot confirm empty order")
        if self.status != OrderStatus.PENDING:
            raise ValueError("Order is not in pending status")
        
        self.status = OrderStatus.CONFIRMED
    
    def cancel(self):
        """Domain behavior: Cancel the order."""
        if self.status in [OrderStatus.SHIPPED, OrderStatus.DELIVERED]:
            raise ValueError("Cannot cancel shipped or delivered order")
        
        self.status = OrderStatus.CANCELLED
    
    def _calculate_total(self):
        """Calculate total amount."""
        self.total_amount = sum(item.total_price for item in self.items)

# ==================== PORTS (INTERFACES) ====================

# Primary Ports (Driving Adapters)
class OrderManagementPort(ABC):
    """Primary port for order management operations."""
    
    @abstractmethod
    async def create_order(self, customer_id: str) -> Order:
        pass
    
    @abstractmethod
    async def add_item_to_order(self, order_id: str, product_id: str, quantity: int) -> Order:
        pass
    
    @abstractmethod
    async def confirm_order(self, order_id: str) -> Order:
        pass
    
    @abstractmethod
    async def cancel_order(self, order_id: str) -> Order:
        pass
    
    @abstractmethod
    async def get_order(self, order_id: str) -> Optional[Order]:
        pass

# Secondary Ports (Driven Adapters)
class OrderRepositoryPort(ABC):
    """Secondary port for order persistence."""
    
    @abstractmethod
    async def save(self, order: Order) -> Order:
        pass
    
    @abstractmethod
    async def find_by_id(self, order_id: str) -> Optional[Order]:
        pass
    
    @abstractmethod
    async def find_by_customer(self, customer_id: str) -> List[Order]:
        pass

class ProductServicePort(ABC):
    """Secondary port for product information."""
    
    @abstractmethod
    async def get_product(self, product_id: str) -> Optional[Dict[str, Any]]:
        pass
    
    @abstractmethod
    async def check_availability(self, product_id: str, quantity: int) -> bool:
        pass

class NotificationPort(ABC):
    """Secondary port for notifications."""
    
    @abstractmethod
    async def send_order_confirmation(self, order: Order) -> bool:
        pass
    
    @abstractmethod
    async def send_cancellation_notice(self, order: Order) -> bool:
        pass

class PaymentPort(ABC):
    """Secondary port for payment processing."""
    
    @abstractmethod
    async def process_payment(self, order: Order) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    async def refund_payment(self, order: Order) -> Dict[str, Any]:
        pass

# ==================== DOMAIN SERVICE (APPLICATION CORE) ====================

class OrderService(OrderManagementPort):
    """Core application service implementing the primary port."""
    
    @inject
    def __init__(
        self,
        order_repository: OrderRepositoryPort,
        product_service: ProductServicePort,
        notification_service: NotificationPort,
        payment_service: PaymentPort
    ):
        self.order_repository = order_repository
        self.product_service = product_service
        self.notification_service = notification_service
        self.payment_service = payment_service
    
    async def create_order(self, customer_id: str) -> Order:
        """Create a new order."""
        order = Order(customer_id=customer_id)
        return await self.order_repository.save(order)
    
    async def add_item_to_order(self, order_id: str, product_id: str, quantity: int) -> Order:
        """Add item to an existing order."""
        # Find the order
        order = await self.order_repository.find_by_id(order_id)
        if not order:
            raise ValueError("Order not found")
        
        if order.status != OrderStatus.PENDING:
            raise ValueError("Cannot modify non-pending order")
        
        # Check product availability
        product = await self.product_service.get_product(product_id)
        if not product:
            raise ValueError("Product not found")
        
        available = await self.product_service.check_availability(product_id, quantity)
        if not available:
            raise ValueError("Product not available in requested quantity")
        
        # Add item to order
        order_item = OrderItem(
            product_id=product_id,
            product_name=product["name"],
            quantity=quantity,
            unit_price=product["price"]
        )
        
        order.add_item(order_item)
        return await self.order_repository.save(order)
    
    async def confirm_order(self, order_id: str) -> Order:
        """Confirm an order."""
        order = await self.order_repository.find_by_id(order_id)
        if not order:
            raise ValueError("Order not found")
        
        # Process payment
        payment_result = await self.payment_service.process_payment(order)
        if not payment_result.get("success"):
            raise ValueError("Payment processing failed")
        
        # Confirm the order
        order.confirm()
        saved_order = await self.order_repository.save(order)
        
        # Send confirmation
        await self.notification_service.send_order_confirmation(saved_order)
        
        return saved_order
    
    async def cancel_order(self, order_id: str) -> Order:
        """Cancel an order."""
        order = await self.order_repository.find_by_id(order_id)
        if not order:
            raise ValueError("Order not found")
        
        # If confirmed, process refund
        if order.status == OrderStatus.CONFIRMED:
            refund_result = await self.payment_service.refund_payment(order)
            if not refund_result.get("success"):
                raise ValueError("Refund processing failed")
        
        # Cancel the order
        order.cancel()
        saved_order = await self.order_repository.save(order)
        
        # Send cancellation notice
        await self.notification_service.send_cancellation_notice(saved_order)
        
        return saved_order
    
    async def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID."""
        return await self.order_repository.find_by_id(order_id)

# ==================== ADAPTERS ====================

# Primary Adapters (Driving)
class WebOrderController:
    """Web adapter for order operations."""
    
    @inject
    def __init__(self, order_service: OrderManagementPort):
        self.order_service = order_service
    
    async def create_order_endpoint(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle POST /orders."""
        try:
            order = await self.order_service.create_order(request_data["customer_id"])
            return {
                "status": "success",
                "data": {
                    "order_id": order.id,
                    "customer_id": order.customer_id,
                    "status": order.status.value
                }
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def add_item_endpoint(self, order_id: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle POST /orders/{id}/items."""
        try:
            order = await self.order_service.add_item_to_order(
                order_id,
                request_data["product_id"],
                request_data["quantity"]
            )
            return {
                "status": "success",
                "data": {
                    "order_id": order.id,
                    "total_amount": order.total_amount,
                    "items_count": len(order.items)
                }
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

class CLIOrderInterface:
    """Command-line adapter for order operations."""
    
    @inject
    def __init__(self, order_service: OrderManagementPort):
        self.order_service = order_service
    
    async def create_order_command(self, customer_id: str):
        """CLI command to create order."""
        try:
            order = await self.order_service.create_order(customer_id)
            print(f"Order created successfully: {order.id}")
        except Exception as e:
            print(f"Error creating order: {e}")

# Secondary Adapters (Driven)
class DatabaseOrderRepository(OrderRepositoryPort):
    """Database adapter for order persistence."""
    
    @inject
    def __init__(self, database: Database):
        self.database = database
        self._orders: Dict[str, Order] = {}  # In-memory for demo
        self._counter = 0
    
    async def save(self, order: Order) -> Order:
        if not order.id:
            self._counter += 1
            order.id = f"order_{self._counter}"
        
        self._orders[order.id] = order
        return order
    
    async def find_by_id(self, order_id: str) -> Optional[Order]:
        return self._orders.get(order_id)
    
    async def find_by_customer(self, customer_id: str) -> List[Order]:
        return [order for order in self._orders.values() if order.customer_id == customer_id]

class ExternalProductService(ProductServicePort):
    """External service adapter for product information."""
    
    def __init__(self):
        # Mock product data
        self._products = {
            "prod1": {"name": "Laptop", "price": 999.99, "stock": 10},
            "prod2": {"name": "Mouse", "price": 29.99, "stock": 50},
            "prod3": {"name": "Keyboard", "price": 79.99, "stock": 25}
        }
    
    async def get_product(self, product_id: str) -> Optional[Dict[str, Any]]:
        return self._products.get(product_id)
    
    async def check_availability(self, product_id: str, quantity: int) -> bool:
        product = self._products.get(product_id)
        return product and product["stock"] >= quantity

class EmailNotificationService(NotificationPort):
    """Email adapter for notifications."""
    
    async def send_order_confirmation(self, order: Order) -> bool:
        print(f"Sending order confirmation email for order {order.id}")
        return True
    
    async def send_cancellation_notice(self, order: Order) -> bool:
        print(f"Sending cancellation notice for order {order.id}")
        return True

class StripePaymentService(PaymentPort):
    """Stripe adapter for payment processing."""
    
    async def process_payment(self, order: Order) -> Dict[str, Any]:
        # Mock payment processing
        print(f"Processing payment for order {order.id}, amount: ${order.total_amount}")
        return {"success": True, "transaction_id": f"txn_{order.id}"}
    
    async def refund_payment(self, order: Order) -> Dict[str, Any]:
        # Mock refund processing
        print(f"Processing refund for order {order.id}, amount: ${order.total_amount}")
        return {"success": True, "refund_id": f"refund_{order.id}"}

# ==================== CONFIGURATION ====================

class HexagonalArchitectureModule(Module):
    """Module configuration for hexagonal architecture."""
    
    def configure(self):
        # Infrastructure
        self.bind(Database, Database).singleton()
        
        # Primary Ports (implemented by domain services)
        self.bind(OrderManagementPort, OrderService).scoped()
        
        # Secondary Ports (implemented by adapters)
        self.bind(OrderRepositoryPort, DatabaseOrderRepository).singleton()
        self.bind(ProductServicePort, ExternalProductService).singleton()
        self.bind(NotificationPort, EmailNotificationService).singleton()
        self.bind(PaymentPort, StripePaymentService).singleton()
        
        # Primary Adapters
        self.bind(WebOrderController, WebOrderController).scoped()
        self.bind(CLIOrderInterface, CLIOrderInterface).scoped()

# Demo Application
class HexagonalApplication:
    @inject
    def __init__(
        self,
        web_controller: WebOrderController,
        cli_interface: CLIOrderInterface
    ):
        self.web_controller = web_controller
        self.cli_interface = cli_interface
    
    async def run_demo(self):
        """Demonstrate hexagonal architecture."""
        print("=== Hexagonal Architecture Demo ===\n")
        
        # Web interface demo
        print("1. Creating order via Web API:")
        web_result = await self.web_controller.create_order_endpoint({
            "customer_id": "customer123"
        })
        print(f"Result: {web_result}\n")
        
        if web_result["status"] == "success":
            order_id = web_result["data"]["order_id"]
            
            # Add items via Web API
            print("2. Adding items via Web API:")
            add_result = await self.web_controller.add_item_endpoint(order_id, {
                "product_id": "prod1",
                "quantity": 1
            })
            print(f"Result: {add_result}\n")
        
        # CLI interface demo
        print("3. Creating order via CLI:")
        await self.cli_interface.create_order_command("customer456")

async def hexagonal_architecture_example():
    container = InjectQ()
    container.install(HexagonalArchitectureModule())
    
    app = container.get(HexagonalApplication)
    await app.run_demo()
```

## 🚌 Event-Driven Architecture

### CQRS with Event Sourcing

```python
# event_driven_architecture.py
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Type
from datetime import datetime
from enum import Enum
import json
import uuid
from injectq import InjectQ, inject, Module

# ==================== EVENTS ====================

@dataclass
class DomainEvent:
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = ""
    aggregate_id: str = ""
    aggregate_version: int = 0
    event_data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

class AccountEvents:
    """Domain events for account aggregate."""
    
    @dataclass
    class AccountCreated(DomainEvent):
        event_type: str = "account_created"
    
    @dataclass
    class MoneyDeposited(DomainEvent):
        event_type: str = "money_deposited"
    
    @dataclass
    class MoneyWithdrawn(DomainEvent):
        event_type: str = "money_withdrawn"
    
    @dataclass
    class AccountClosed(DomainEvent):
        event_type: str = "account_closed"

# ==================== AGGREGATES ====================

class Account:
    """Account aggregate root with event sourcing."""
    
    def __init__(self, account_id: str):
        self.id = account_id
        self.balance = 0.0
        self.is_closed = False
        self.version = 0
        self._uncommitted_events: List[DomainEvent] = []
    
    def create_account(self, initial_balance: float = 0.0):
        """Create account business operation."""
        if self.version > 0:
            raise ValueError("Account already exists")
        
        event = AccountEvents.AccountCreated(
            aggregate_id=self.id,
            aggregate_version=self.version + 1,
            event_data={"initial_balance": initial_balance}
        )
        
        self._apply_event(event)
        self._uncommitted_events.append(event)
    
    def deposit(self, amount: float):
        """Deposit money business operation."""
        if amount <= 0:
            raise ValueError("Deposit amount must be positive")
        if self.is_closed:
            raise ValueError("Cannot deposit to closed account")
        
        event = AccountEvents.MoneyDeposited(
            aggregate_id=self.id,
            aggregate_version=self.version + 1,
            event_data={"amount": amount, "new_balance": self.balance + amount}
        )
        
        self._apply_event(event)
        self._uncommitted_events.append(event)
    
    def withdraw(self, amount: float):
        """Withdraw money business operation."""
        if amount <= 0:
            raise ValueError("Withdrawal amount must be positive")
        if self.is_closed:
            raise ValueError("Cannot withdraw from closed account")
        if self.balance < amount:
            raise ValueError("Insufficient funds")
        
        event = AccountEvents.MoneyWithdrawn(
            aggregate_id=self.id,
            aggregate_version=self.version + 1,
            event_data={"amount": amount, "new_balance": self.balance - amount}
        )
        
        self._apply_event(event)
        self._uncommitted_events.append(event)
    
    def close_account(self):
        """Close account business operation."""
        if self.is_closed:
            raise ValueError("Account already closed")
        if self.balance > 0:
            raise ValueError("Cannot close account with positive balance")
        
        event = AccountEvents.AccountClosed(
            aggregate_id=self.id,
            aggregate_version=self.version + 1,
            event_data={}
        )
        
        self._apply_event(event)
        self._uncommitted_events.append(event)
    
    def _apply_event(self, event: DomainEvent):
        """Apply event to aggregate state."""
        if isinstance(event, AccountEvents.AccountCreated):
            self.balance = event.event_data["initial_balance"]
        elif isinstance(event, AccountEvents.MoneyDeposited):
            self.balance = event.event_data["new_balance"]
        elif isinstance(event, AccountEvents.MoneyWithdrawn):
            self.balance = event.event_data["new_balance"]
        elif isinstance(event, AccountEvents.AccountClosed):
            self.is_closed = True
        
        self.version = event.aggregate_version
    
    def get_uncommitted_events(self) -> List[DomainEvent]:
        """Get uncommitted events for persistence."""
        return self._uncommitted_events.copy()
    
    def mark_events_as_committed(self):
        """Mark events as committed after persistence."""
        self._uncommitted_events.clear()
    
    @classmethod
    def from_events(cls, account_id: str, events: List[DomainEvent]) -> 'Account':
        """Reconstitute aggregate from events."""
        account = cls(account_id)
        for event in events:
            account._apply_event(event)
        return account

# ==================== COMMANDS ====================

@dataclass
class Command:
    command_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    aggregate_id: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)

@dataclass
class CreateAccountCommand(Command):
    initial_balance: float = 0.0

@dataclass
class DepositMoneyCommand(Command):
    amount: float = 0.0

@dataclass
class WithdrawMoneyCommand(Command):
    amount: float = 0.0

@dataclass
class CloseAccountCommand(Command):
    pass

# ==================== QUERIES ====================

@dataclass
class Query:
    query_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)

@dataclass
class GetAccountBalanceQuery(Query):
    account_id: str = ""

@dataclass
class GetAccountHistoryQuery(Query):
    account_id: str = ""

# ==================== CQRS INTERFACES ====================

class ICommandHandler(ABC):
    @abstractmethod
    async def handle(self, command: Command):
        pass

class IQueryHandler(ABC):
    @abstractmethod
    async def handle(self, query: Query) -> Any:
        pass

class IEventStore(ABC):
    @abstractmethod
    async def save_events(self, aggregate_id: str, events: List[DomainEvent], expected_version: int):
        pass
    
    @abstractmethod
    async def get_events(self, aggregate_id: str) -> List[DomainEvent]:
        pass

class IEventBus(ABC):
    @abstractmethod
    async def publish(self, events: List[DomainEvent]):
        pass

class IReadModelUpdater(ABC):
    @abstractmethod
    async def update(self, event: DomainEvent):
        pass

# ==================== COMMAND HANDLERS ====================

class AccountCommandHandler(ICommandHandler):
    @inject
    def __init__(self, event_store: IEventStore, event_bus: IEventBus):
        self.event_store = event_store
        self.event_bus = event_bus
    
    async def handle(self, command: Command):
        if isinstance(command, CreateAccountCommand):
            await self._handle_create_account(command)
        elif isinstance(command, DepositMoneyCommand):
            await self._handle_deposit_money(command)
        elif isinstance(command, WithdrawMoneyCommand):
            await self._handle_withdraw_money(command)
        elif isinstance(command, CloseAccountCommand):
            await self._handle_close_account(command)
        else:
            raise ValueError(f"Unknown command type: {type(command)}")
    
    async def _handle_create_account(self, command: CreateAccountCommand):
        account = Account(command.aggregate_id)
        account.create_account(command.initial_balance)
        
        await self._save_and_publish(account)
    
    async def _handle_deposit_money(self, command: DepositMoneyCommand):
        account = await self._load_account(command.aggregate_id)
        account.deposit(command.amount)
        
        await self._save_and_publish(account)
    
    async def _handle_withdraw_money(self, command: WithdrawMoneyCommand):
        account = await self._load_account(command.aggregate_id)
        account.withdraw(command.amount)
        
        await self._save_and_publish(account)
    
    async def _handle_close_account(self, command: CloseAccountCommand):
        account = await self._load_account(command.aggregate_id)
        account.close_account()
        
        await self._save_and_publish(account)
    
    async def _load_account(self, account_id: str) -> Account:
        events = await self.event_store.get_events(account_id)
        if not events:
            raise ValueError(f"Account {account_id} not found")
        return Account.from_events(account_id, events)
    
    async def _save_and_publish(self, account: Account):
        events = account.get_uncommitted_events()
        if events:
            await self.event_store.save_events(account.id, events, account.version - len(events))
            await self.event_bus.publish(events)
            account.mark_events_as_committed()

# ==================== QUERY HANDLERS ====================

@dataclass
class AccountReadModel:
    account_id: str
    balance: float
    is_closed: bool
    last_updated: datetime

class AccountQueryHandler(IQueryHandler):
    @inject
    def __init__(self, read_model_store: Dict[str, AccountReadModel]):
        self.read_model_store = read_model_store
    
    async def handle(self, query: Query) -> Any:
        if isinstance(query, GetAccountBalanceQuery):
            return await self._handle_get_balance(query)
        elif isinstance(query, GetAccountHistoryQuery):
            return await self._handle_get_history(query)
        else:
            raise ValueError(f"Unknown query type: {type(query)}")
    
    async def _handle_get_balance(self, query: GetAccountBalanceQuery) -> Dict[str, Any]:
        read_model = self.read_model_store.get(query.account_id)
        if not read_model:
            return {"error": "Account not found"}
        
        return {
            "account_id": read_model.account_id,
            "balance": read_model.balance,
            "is_closed": read_model.is_closed
        }
    
    async def _handle_get_history(self, query: GetAccountHistoryQuery) -> Dict[str, Any]:
        # In a real implementation, this would query a separate history store
        return {
            "account_id": query.account_id,
            "transactions": []  # Placeholder
        }

# ==================== READ MODEL UPDATER ====================

class AccountReadModelUpdater(IReadModelUpdater):
    @inject
    def __init__(self, read_model_store: Dict[str, AccountReadModel]):
        self.read_model_store = read_model_store
    
    async def update(self, event: DomainEvent):
        if isinstance(event, AccountEvents.AccountCreated):
            await self._handle_account_created(event)
        elif isinstance(event, (AccountEvents.MoneyDeposited, AccountEvents.MoneyWithdrawn)):
            await self._handle_balance_changed(event)
        elif isinstance(event, AccountEvents.AccountClosed):
            await self._handle_account_closed(event)
    
    async def _handle_account_created(self, event: AccountEvents.AccountCreated):
        read_model = AccountReadModel(
            account_id=event.aggregate_id,
            balance=event.event_data["initial_balance"],
            is_closed=False,
            last_updated=event.timestamp
        )
        self.read_model_store[event.aggregate_id] = read_model
    
    async def _handle_balance_changed(self, event: DomainEvent):
        read_model = self.read_model_store.get(event.aggregate_id)
        if read_model:
            read_model.balance = event.event_data["new_balance"]
            read_model.last_updated = event.timestamp
    
    async def _handle_account_closed(self, event: AccountEvents.AccountClosed):
        read_model = self.read_model_store.get(event.aggregate_id)
        if read_model:
            read_model.is_closed = True
            read_model.last_updated = event.timestamp

# ==================== INFRASTRUCTURE ====================

class InMemoryEventStore(IEventStore):
    def __init__(self):
        self._events: Dict[str, List[DomainEvent]] = {}
    
    async def save_events(self, aggregate_id: str, events: List[DomainEvent], expected_version: int):
        current_events = self._events.get(aggregate_id, [])
        
        if len(current_events) != expected_version:
            raise ValueError("Concurrency conflict")
        
        if aggregate_id not in self._events:
            self._events[aggregate_id] = []
        
        self._events[aggregate_id].extend(events)
    
    async def get_events(self, aggregate_id: str) -> List[DomainEvent]:
        return self._events.get(aggregate_id, [])

class InMemoryEventBus(IEventBus):
    @inject
    def __init__(self, read_model_updater: IReadModelUpdater):
        self.read_model_updater = read_model_updater
    
    async def publish(self, events: List[DomainEvent]):
        for event in events:
            await self.read_model_updater.update(event)
            print(f"Published event: {event.event_type} for aggregate {event.aggregate_id}")

# ==================== APPLICATION SERVICE ====================

class BankingApplicationService:
    @inject
    def __init__(
        self,
        command_handler: AccountCommandHandler,
        query_handler: AccountQueryHandler
    ):
        self.command_handler = command_handler
        self.query_handler = query_handler
    
    async def create_account(self, account_id: str, initial_balance: float = 0.0):
        command = CreateAccountCommand(
            aggregate_id=account_id,
            initial_balance=initial_balance
        )
        await self.command_handler.handle(command)
    
    async def deposit_money(self, account_id: str, amount: float):
        command = DepositMoneyCommand(
            aggregate_id=account_id,
            amount=amount
        )
        await self.command_handler.handle(command)
    
    async def withdraw_money(self, account_id: str, amount: float):
        command = WithdrawMoneyCommand(
            aggregate_id=account_id,
            amount=amount
        )
        await self.command_handler.handle(command)
    
    async def get_account_balance(self, account_id: str) -> Dict[str, Any]:
        query = GetAccountBalanceQuery(account_id=account_id)
        return await self.query_handler.handle(query)

# ==================== CONFIGURATION ====================

class EventDrivenModule(Module):
    def configure(self):
        # Shared read model store
        read_model_store: Dict[str, AccountReadModel] = {}
        self.bind(Dict[str, AccountReadModel], read_model_store).singleton()
        
        # Infrastructure
        self.bind(IEventStore, InMemoryEventStore).singleton()
        self.bind(IReadModelUpdater, AccountReadModelUpdater).singleton()
        self.bind(IEventBus, InMemoryEventBus).singleton()
        
        # CQRS handlers
        self.bind(AccountCommandHandler, AccountCommandHandler).singleton()
        self.bind(AccountQueryHandler, AccountQueryHandler).singleton()
        
        # Application service
        self.bind(BankingApplicationService, BankingApplicationService).singleton()

# Demo Application
class EventDrivenApplication:
    @inject
    def __init__(self, banking_service: BankingApplicationService):
        self.banking_service = banking_service
    
    async def run_demo(self):
        """Demonstrate event-driven architecture."""
        print("=== Event-Driven Architecture (CQRS + Event Sourcing) Demo ===\n")
        
        account_id = "account123"
        
        # Create account
        print("1. Creating account...")
        await self.banking_service.create_account(account_id, 100.0)
        
        # Check balance
        print("2. Checking initial balance...")
        balance = await self.banking_service.get_account_balance(account_id)
        print(f"Balance: {balance}\n")
        
        # Deposit money
        print("3. Depositing $50...")
        await self.banking_service.deposit_money(account_id, 50.0)
        
        # Check balance
        balance = await self.banking_service.get_account_balance(account_id)
        print(f"Balance after deposit: {balance}\n")
        
        # Withdraw money
        print("4. Withdrawing $30...")
        await self.banking_service.withdraw_money(account_id, 30.0)
        
        # Check final balance
        balance = await self.banking_service.get_account_balance(account_id)
        print(f"Final balance: {balance}")

async def event_driven_architecture_example():
    container = InjectQ()
    container.install(EventDrivenModule())
    
    app = container.get(EventDrivenApplication)
    await app.run_demo()

# Usage Examples
async def main():
    print("Running architectural pattern examples...\n")
    
    await layered_architecture_example()
    print("\n" + "="*60 + "\n")
    
    await hexagonal_architecture_example()
    print("\n" + "="*60 + "\n")
    
    await event_driven_architecture_example()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

This architectural design patterns guide demonstrates:

1. **Layered Architecture**: Traditional three-layer pattern with proper separation of concerns
2. **Hexagonal Architecture**: Ports and adapters pattern with domain isolation
3. **Event-Driven Architecture**: CQRS with event sourcing for scalable systems

Key architectural principles shown:
- Dependency inversion and interface segregation
- Separation of business logic from infrastructure
- Clean boundaries between layers/components
- Testable and maintainable design
- Scalable patterns for complex applications

Each pattern includes complete implementations with proper dependency injection configuration using InjectQ, demonstrating how to build robust, maintainable applications with clear architectural boundaries.

Ready to continue with the final sections of the best practices documentation?
