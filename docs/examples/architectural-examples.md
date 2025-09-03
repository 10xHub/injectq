# Architectural Examples

This section demonstrates how to implement various architectural patterns and styles using InjectQ to create maintainable, scalable applications.

## 🏛️ Clean Architecture

Clean Architecture separates concerns into distinct layers with dependency inversion. InjectQ makes this pattern natural through interface-based dependency injection.

### Complete Clean Architecture Implementation

```python
# clean_architecture.py - Complete Clean Architecture implementation
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime
from injectq import InjectQ, inject, Module
import asyncio

# ==================== ENTITIES (Core Business Objects) ====================

@dataclass
class User:
    id: str
    username: str
    email: str
    created_at: datetime
    is_active: bool = True

    def deactivate(self):
        """Business rule: User can be deactivated."""
        self.is_active = False

    def can_create_post(self) -> bool:
        """Business rule: Only active users can create posts."""
        return self.is_active

@dataclass
class Post:
    id: str
    title: str
    content: str
    author_id: str
    created_at: datetime
    published: bool = False
    view_count: int = 0

    def publish(self):
        """Business rule: Post can be published."""
        if not self.title.strip():
            raise ValueError("Post must have a title to be published")
        if not self.content.strip():
            raise ValueError("Post must have content to be published")
        self.published = True

    def increment_views(self):
        """Business rule: Track post views."""
        self.view_count += 1

# ==================== USE CASES (Application Layer) ====================

# Input/Output Models
@dataclass
class CreateUserRequest:
    username: str
    email: str

@dataclass
class CreateUserResponse:
    user_id: str
    username: str
    email: str
    success: bool
    error_message: Optional[str] = None

@dataclass
class CreatePostRequest:
    title: str
    content: str
    author_id: str

@dataclass
class CreatePostResponse:
    post_id: str
    title: str
    success: bool
    error_message: Optional[str] = None

@dataclass
class GetPostResponse:
    post: Optional[Post]
    success: bool
    error_message: Optional[str] = None

# Repository Interfaces (Dependency Inversion)
class IUserRepository(ABC):
    @abstractmethod
    async def save(self, user: User) -> User:
        pass
    
    @abstractmethod
    async def find_by_id(self, user_id: str) -> Optional[User]:
        pass
    
    @abstractmethod
    async def find_by_username(self, username: str) -> Optional[User]:
        pass
    
    @abstractmethod
    async def find_by_email(self, email: str) -> Optional[User]:
        pass

class IPostRepository(ABC):
    @abstractmethod
    async def save(self, post: Post) -> Post:
        pass
    
    @abstractmethod
    async def find_by_id(self, post_id: str) -> Optional[Post]:
        pass
    
    @abstractmethod
    async def find_by_author(self, author_id: str) -> List[Post]:
        pass

# External Service Interfaces
class IEmailService(ABC):
    @abstractmethod
    async def send_welcome_email(self, user: User) -> bool:
        pass

class IIdGenerator(ABC):
    @abstractmethod
    def generate_id(self) -> str:
        pass

# Use Case Classes
class CreateUserUseCase:
    @inject
    def __init__(
        self,
        user_repository: IUserRepository,
        email_service: IEmailService,
        id_generator: IIdGenerator
    ):
        self.user_repository = user_repository
        self.email_service = email_service
        self.id_generator = id_generator

    async def execute(self, request: CreateUserRequest) -> CreateUserResponse:
        try:
            # Validate business rules
            if not request.username.strip():
                return CreateUserResponse(
                    user_id="",
                    username=request.username,
                    email=request.email,
                    success=False,
                    error_message="Username cannot be empty"
                )

            if not request.email.strip() or "@" not in request.email:
                return CreateUserResponse(
                    user_id="",
                    username=request.username,
                    email=request.email,
                    success=False,
                    error_message="Invalid email address"
                )

            # Check if user already exists
            existing_user = await self.user_repository.find_by_username(request.username)
            if existing_user:
                return CreateUserResponse(
                    user_id="",
                    username=request.username,
                    email=request.email,
                    success=False,
                    error_message="Username already exists"
                )

            existing_email = await self.user_repository.find_by_email(request.email)
            if existing_email:
                return CreateUserResponse(
                    user_id="",
                    username=request.username,
                    email=request.email,
                    success=False,
                    error_message="Email already exists"
                )

            # Create user entity
            user = User(
                id=self.id_generator.generate_id(),
                username=request.username,
                email=request.email,
                created_at=datetime.now()
            )

            # Save user
            saved_user = await self.user_repository.save(user)

            # Send welcome email (external service)
            await self.email_service.send_welcome_email(saved_user)

            return CreateUserResponse(
                user_id=saved_user.id,
                username=saved_user.username,
                email=saved_user.email,
                success=True
            )

        except Exception as e:
            return CreateUserResponse(
                user_id="",
                username=request.username,
                email=request.email,
                success=False,
                error_message=f"Unexpected error: {str(e)}"
            )

class CreatePostUseCase:
    @inject
    def __init__(
        self,
        post_repository: IPostRepository,
        user_repository: IUserRepository,
        id_generator: IIdGenerator
    ):
        self.post_repository = post_repository
        self.user_repository = user_repository
        self.id_generator = id_generator

    async def execute(self, request: CreatePostRequest) -> CreatePostResponse:
        try:
            # Find the author
            author = await self.user_repository.find_by_id(request.author_id)
            if not author:
                return CreatePostResponse(
                    post_id="",
                    title=request.title,
                    success=False,
                    error_message="Author not found"
                )

            # Check business rules
            if not author.can_create_post():
                return CreatePostResponse(
                    post_id="",
                    title=request.title,
                    success=False,
                    error_message="User is not active and cannot create posts"
                )

            # Create post entity
            post = Post(
                id=self.id_generator.generate_id(),
                title=request.title,
                content=request.content,
                author_id=request.author_id,
                created_at=datetime.now()
            )

            # Save post
            saved_post = await self.post_repository.save(post)

            return CreatePostResponse(
                post_id=saved_post.id,
                title=saved_post.title,
                success=True
            )

        except Exception as e:
            return CreatePostResponse(
                post_id="",
                title=request.title,
                success=False,
                error_message=f"Unexpected error: {str(e)}"
            )

class GetPostUseCase:
    @inject
    def __init__(self, post_repository: IPostRepository):
        self.post_repository = post_repository

    async def execute(self, post_id: str) -> GetPostResponse:
        try:
            post = await self.post_repository.find_by_id(post_id)
            
            if not post:
                return GetPostResponse(
                    post=None,
                    success=False,
                    error_message="Post not found"
                )

            # Business rule: Increment view count
            post.increment_views()
            await self.post_repository.save(post)

            return GetPostResponse(
                post=post,
                success=True
            )

        except Exception as e:
            return GetPostResponse(
                post=None,
                success=False,
                error_message=f"Unexpected error: {str(e)}"
            )

# ==================== INTERFACE ADAPTERS (Infrastructure Layer) ====================

# Database Implementations
class DatabaseUserRepository(IUserRepository):
    @inject
    def __init__(self, database_connection: DatabaseConnection):
        self.db = database_connection
        self.users: Dict[str, User] = {}  # In-memory for demo

    async def save(self, user: User) -> User:
        self.users[user.id] = user
        return user

    async def find_by_id(self, user_id: str) -> Optional[User]:
        return self.users.get(user_id)

    async def find_by_username(self, username: str) -> Optional[User]:
        for user in self.users.values():
            if user.username == username:
                return user
        return None

    async def find_by_email(self, email: str) -> Optional[User]:
        for user in self.users.values():
            if user.email == email:
                return user
        return None

class DatabasePostRepository(IPostRepository):
    @inject
    def __init__(self, database_connection: DatabaseConnection):
        self.db = database_connection
        self.posts: Dict[str, Post] = {}  # In-memory for demo

    async def save(self, post: Post) -> Post:
        self.posts[post.id] = post
        return post

    async def find_by_id(self, post_id: str) -> Optional[Post]:
        return self.posts.get(post_id)

    async def find_by_author(self, author_id: str) -> List[Post]:
        return [post for post in self.posts.values() if post.author_id == author_id]

# External Service Implementations
class EmailServiceImpl(IEmailService):
    @inject
    def __init__(self, email_config: EmailConfig):
        self.config = email_config

    async def send_welcome_email(self, user: User) -> bool:
        print(f"Sending welcome email to {user.email}")
        await asyncio.sleep(0.1)  # Simulate network delay
        return True

class UUIDGenerator(IIdGenerator):
    def generate_id(self) -> str:
        import uuid
        return str(uuid.uuid4())

# Configuration
class DatabaseConnection:
    @inject
    def __init__(self, db_config: DatabaseConfig):
        self.config = db_config

class DatabaseConfig:
    def __init__(self, host: str, port: int, database: str):
        self.host = host
        self.port = port
        self.database = database

class EmailConfig:
    def __init__(self, smtp_host: str, smtp_port: int):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port

# ==================== FRAMEWORKS & DRIVERS (Presentation Layer) ====================

# Web Controllers (FastAPI example)
class UserController:
    @inject
    def __init__(self, create_user_use_case: CreateUserUseCase):
        self.create_user_use_case = create_user_use_case

    async def create_user(self, user_data: Dict[str, str]) -> Dict[str, Any]:
        request = CreateUserRequest(
            username=user_data["username"],
            email=user_data["email"]
        )
        
        response = await self.create_user_use_case.execute(request)
        
        if response.success:
            return {
                "status": "success",
                "data": {
                    "user_id": response.user_id,
                    "username": response.username,
                    "email": response.email
                }
            }
        else:
            return {
                "status": "error",
                "message": response.error_message
            }

class PostController:
    @inject
    def __init__(
        self,
        create_post_use_case: CreatePostUseCase,
        get_post_use_case: GetPostUseCase
    ):
        self.create_post_use_case = create_post_use_case
        self.get_post_use_case = get_post_use_case

    async def create_post(self, post_data: Dict[str, str]) -> Dict[str, Any]:
        request = CreatePostRequest(
            title=post_data["title"],
            content=post_data["content"],
            author_id=post_data["author_id"]
        )
        
        response = await self.create_post_use_case.execute(request)
        
        if response.success:
            return {
                "status": "success",
                "data": {
                    "post_id": response.post_id,
                    "title": response.title
                }
            }
        else:
            return {
                "status": "error",
                "message": response.error_message
            }

    async def get_post(self, post_id: str) -> Dict[str, Any]:
        response = await self.get_post_use_case.execute(post_id)
        
        if response.success and response.post:
            post = response.post
            return {
                "status": "success",
                "data": {
                    "id": post.id,
                    "title": post.title,
                    "content": post.content,
                    "author_id": post.author_id,
                    "created_at": post.created_at.isoformat(),
                    "published": post.published,
                    "view_count": post.view_count
                }
            }
        else:
            return {
                "status": "error",
                "message": response.error_message
            }

# Application Orchestrator
class BlogApplication:
    @inject
    def __init__(
        self,
        user_controller: UserController,
        post_controller: PostController
    ):
        self.user_controller = user_controller
        self.post_controller = post_controller

    async def run_demo(self):
        """Demonstrate the clean architecture in action."""
        print("=== Clean Architecture Demo ===\n")

        # Create a user
        print("1. Creating a user...")
        user_result = await self.user_controller.create_user({
            "username": "john_doe",
            "email": "john@example.com"
        })
        print(f"Result: {user_result}\n")

        if user_result["status"] == "success":
            user_id = user_result["data"]["user_id"]

            # Create a post
            print("2. Creating a post...")
            post_result = await self.post_controller.create_post({
                "title": "My First Blog Post",
                "content": "This is the content of my first blog post using Clean Architecture!",
                "author_id": user_id
            })
            print(f"Result: {post_result}\n")

            if post_result["status"] == "success":
                post_id = post_result["data"]["post_id"]

                # Get the post (should increment view count)
                print("3. Getting the post...")
                get_result = await self.post_controller.get_post(post_id)
                print(f"Result: {get_result}\n")

                # Get the post again (view count should increment)
                print("4. Getting the post again...")
                get_result2 = await self.post_controller.get_post(post_id)
                print(f"Result: {get_result2}\n")

        # Test validation
        print("5. Testing validation - creating user with invalid email...")
        invalid_user_result = await self.user_controller.create_user({
            "username": "invalid_user",
            "email": "invalid-email"
        })
        print(f"Result: {invalid_user_result}\n")

# ==================== DEPENDENCY INJECTION CONFIGURATION ====================

class CleanArchitectureModule(Module):
    def configure(self):
        # Infrastructure Configuration
        self.bind(DatabaseConfig, DatabaseConfig(
            host="localhost",
            port=5432,
            database="blog_db"
        )).singleton()

        self.bind(EmailConfig, EmailConfig(
            smtp_host="smtp.example.com",
            smtp_port=587
        )).singleton()

        # Infrastructure Services
        self.bind(DatabaseConnection, DatabaseConnection).singleton()
        self.bind(IIdGenerator, UUIDGenerator).singleton()
        self.bind(IEmailService, EmailServiceImpl).singleton()

        # Repositories (Interface Adapters)
        self.bind(IUserRepository, DatabaseUserRepository).scoped()
        self.bind(IPostRepository, DatabasePostRepository).scoped()

        # Use Cases (Application Layer)
        self.bind(CreateUserUseCase, CreateUserUseCase).scoped()
        self.bind(CreatePostUseCase, CreatePostUseCase).scoped()
        self.bind(GetPostUseCase, GetPostUseCase).scoped()

        # Controllers (Presentation Layer)
        self.bind(UserController, UserController).scoped()
        self.bind(PostController, PostController).scoped()

        # Application
        self.bind(BlogApplication, BlogApplication).singleton()

# Usage Example
async def clean_architecture_example():
    container = InjectQ()
    container.install(CleanArchitectureModule())

    app = container.get(BlogApplication)
    await app.run_demo()
```

## 🎯 Domain-Driven Design (DDD)

DDD focuses on the business domain and uses ubiquitous language. InjectQ supports DDD patterns through careful dependency management.

```python
# ddd_example.py - Domain-Driven Design implementation
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from enum import Enum
from injectq import InjectQ, inject, Module

# ==================== VALUE OBJECTS ====================

@dataclass(frozen=True)
class Money:
    amount: float
    currency: str = "USD"

    def __post_init__(self):
        if self.amount < 0:
            raise ValueError("Amount cannot be negative")
        if not self.currency:
            raise ValueError("Currency is required")

    def add(self, other: 'Money') -> 'Money':
        if self.currency != other.currency:
            raise ValueError("Cannot add different currencies")
        return Money(self.amount + other.amount, self.currency)

    def subtract(self, other: 'Money') -> 'Money':
        if self.currency != other.currency:
            raise ValueError("Cannot subtract different currencies")
        result = self.amount - other.amount
        if result < 0:
            raise ValueError("Insufficient funds")
        return Money(result, self.currency)

    def multiply(self, factor: float) -> 'Money':
        return Money(self.amount * factor, self.currency)

@dataclass(frozen=True)
class CustomerId:
    value: str

    def __post_init__(self):
        if not self.value or not self.value.strip():
            raise ValueError("Customer ID cannot be empty")

@dataclass(frozen=True)
class ProductId:
    value: str

    def __post_init__(self):
        if not self.value or not self.value.strip():
            raise ValueError("Product ID cannot be empty")

@dataclass(frozen=True)
class OrderId:
    value: str

    def __post_init__(self):
        if not self.value or not self.value.strip():
            raise ValueError("Order ID cannot be empty")

@dataclass(frozen=True)
class EmailAddress:
    value: str

    def __post_init__(self):
        if not self.value or "@" not in self.value:
            raise ValueError("Invalid email address")

# ==================== ENUMERATIONS ====================

class OrderStatus(Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"

class CustomerType(Enum):
    REGULAR = "regular"
    PREMIUM = "premium"
    VIP = "vip"

# ==================== ENTITIES ====================

class Customer:
    def __init__(
        self,
        customer_id: CustomerId,
        name: str,
        email: EmailAddress,
        customer_type: CustomerType = CustomerType.REGULAR
    ):
        self.id = customer_id
        self.name = name
        self.email = email
        self.customer_type = customer_type
        self.created_at = datetime.now()
        self._order_history: List[OrderId] = []

    def add_order(self, order_id: OrderId):
        """Domain behavior: Add order to customer history."""
        self._order_history.append(order_id)

    def get_order_count(self) -> int:
        """Domain behavior: Get total number of orders."""
        return len(self._order_history)

    def can_get_discount(self) -> bool:
        """Domain rule: VIP customers always get discount, Premium with 5+ orders."""
        if self.customer_type == CustomerType.VIP:
            return True
        elif self.customer_type == CustomerType.PREMIUM:
            return self.get_order_count() >= 5
        return False

    def get_discount_percentage(self) -> float:
        """Domain rule: Calculate discount percentage."""
        if self.customer_type == CustomerType.VIP:
            return 0.15  # 15%
        elif self.customer_type == CustomerType.PREMIUM and self.get_order_count() >= 5:
            return 0.10  # 10%
        return 0.0

class Product:
    def __init__(
        self,
        product_id: ProductId,
        name: str,
        price: Money,
        stock_quantity: int
    ):
        self.id = product_id
        self.name = name
        self.price = price
        self.stock_quantity = stock_quantity

    def is_available(self, quantity: int) -> bool:
        """Domain rule: Check if product is available in required quantity."""
        return self.stock_quantity >= quantity

    def reduce_stock(self, quantity: int):
        """Domain behavior: Reduce stock quantity."""
        if not self.is_available(quantity):
            raise ValueError(f"Insufficient stock. Available: {self.stock_quantity}, Requested: {quantity}")
        self.stock_quantity -= quantity

    def increase_stock(self, quantity: int):
        """Domain behavior: Increase stock quantity."""
        self.stock_quantity += quantity

# ==================== AGGREGATES ====================

@dataclass
class OrderItem:
    product_id: ProductId
    product_name: str
    unit_price: Money
    quantity: int

    @property
    def total_price(self) -> Money:
        return self.unit_price.multiply(self.quantity)

class Order:  # Aggregate Root
    def __init__(
        self,
        order_id: OrderId,
        customer_id: CustomerId
    ):
        self.id = order_id
        self.customer_id = customer_id
        self.status = OrderStatus.PENDING
        self.created_at = datetime.now()
        self._items: List[OrderItem] = []
        self._discount_percentage: float = 0.0

    def add_item(self, product: Product, quantity: int):
        """Domain behavior: Add item to order."""
        if self.status != OrderStatus.PENDING:
            raise ValueError("Cannot modify confirmed order")

        if not product.is_available(quantity):
            raise ValueError(f"Product {product.name} is not available in quantity {quantity}")

        # Check if item already exists
        for item in self._items:
            if item.product_id == product.id:
                item.quantity += quantity
                return

        # Add new item
        order_item = OrderItem(
            product_id=product.id,
            product_name=product.name,
            unit_price=product.price,
            quantity=quantity
        )
        self._items.append(order_item)

    def remove_item(self, product_id: ProductId):
        """Domain behavior: Remove item from order."""
        if self.status != OrderStatus.PENDING:
            raise ValueError("Cannot modify confirmed order")

        self._items = [item for item in self._items if item.product_id != product_id]

    def apply_customer_discount(self, customer: Customer):
        """Domain behavior: Apply customer-specific discount."""
        if customer.can_get_discount():
            self._discount_percentage = customer.get_discount_percentage()

    def get_subtotal(self) -> Money:
        """Domain calculation: Calculate subtotal before discounts."""
        if not self._items:
            return Money(0.0)

        total = self._items[0].total_price
        for item in self._items[1:]:
            total = total.add(item.total_price)
        return total

    def get_discount_amount(self) -> Money:
        """Domain calculation: Calculate discount amount."""
        subtotal = self.get_subtotal()
        return subtotal.multiply(self._discount_percentage)

    def get_total(self) -> Money:
        """Domain calculation: Calculate final total."""
        subtotal = self.get_subtotal()
        discount = self.get_discount_amount()
        return subtotal.subtract(discount)

    def confirm(self):
        """Domain behavior: Confirm the order."""
        if not self._items:
            raise ValueError("Cannot confirm empty order")
        if self.status != OrderStatus.PENDING:
            raise ValueError("Order already confirmed")

        self.status = OrderStatus.CONFIRMED

    def ship(self):
        """Domain behavior: Ship the order."""
        if self.status != OrderStatus.CONFIRMED:
            raise ValueError("Can only ship confirmed orders")
        self.status = OrderStatus.SHIPPED

    def deliver(self):
        """Domain behavior: Mark order as delivered."""
        if self.status != OrderStatus.SHIPPED:
            raise ValueError("Can only deliver shipped orders")
        self.status = OrderStatus.DELIVERED

    def cancel(self):
        """Domain behavior: Cancel the order."""
        if self.status in [OrderStatus.SHIPPED, OrderStatus.DELIVERED]:
            raise ValueError("Cannot cancel shipped or delivered orders")
        self.status = OrderStatus.CANCELLED

    @property
    def items(self) -> List[OrderItem]:
        """Read-only access to order items."""
        return self._items.copy()

# ==================== DOMAIN SERVICES ====================

class PricingService:
    """Domain service for complex pricing logic."""

    def calculate_shipping_cost(self, order: Order, customer: Customer) -> Money:
        """Calculate shipping cost based on order and customer."""
        subtotal = order.get_subtotal()
        
        # Free shipping for VIP customers
        if customer.customer_type == CustomerType.VIP:
            return Money(0.0)
        
        # Free shipping for orders over $100
        if subtotal.amount >= 100.0:
            return Money(0.0)
        
        # Premium customers get reduced shipping
        if customer.customer_type == CustomerType.PREMIUM:
            return Money(5.0)
        
        # Regular shipping cost
        return Money(10.0)

    def calculate_tax(self, order: Order) -> Money:
        """Calculate tax for the order."""
        subtotal = order.get_subtotal()
        discount = order.get_discount_amount()
        taxable_amount = subtotal.subtract(discount)
        
        # 8.5% tax rate
        return taxable_amount.multiply(0.085)

class InventoryService:
    """Domain service for inventory management."""

    @inject
    def __init__(self, product_repository: 'IProductRepository'):
        self.product_repository = product_repository

    async def reserve_inventory(self, order: Order) -> bool:
        """Reserve inventory for order items."""
        try:
            # Check availability for all items first
            for item in order.items:
                product = await self.product_repository.find_by_id(item.product_id)
                if not product or not product.is_available(item.quantity):
                    return False

            # Reserve inventory for all items
            for item in order.items:
                product = await self.product_repository.find_by_id(item.product_id)
                product.reduce_stock(item.quantity)
                await self.product_repository.save(product)

            return True

        except Exception:
            # Rollback logic would go here in a real implementation
            return False

    async def release_inventory(self, order: Order) -> bool:
        """Release reserved inventory (e.g., when order is cancelled)."""
        try:
            for item in order.items:
                product = await self.product_repository.find_by_id(item.product_id)
                if product:
                    product.increase_stock(item.quantity)
                    await self.product_repository.save(product)

            return True

        except Exception:
            return False

# ==================== REPOSITORIES (INTERFACES) ====================

class ICustomerRepository(ABC):
    @abstractmethod
    async def find_by_id(self, customer_id: CustomerId) -> Optional[Customer]:
        pass

    @abstractmethod
    async def save(self, customer: Customer) -> Customer:
        pass

class IProductRepository(ABC):
    @abstractmethod
    async def find_by_id(self, product_id: ProductId) -> Optional[Product]:
        pass

    @abstractmethod
    async def save(self, product: Product) -> Product:
        pass

class IOrderRepository(ABC):
    @abstractmethod
    async def find_by_id(self, order_id: OrderId) -> Optional[Order]:
        pass

    @abstractmethod
    async def save(self, order: Order) -> Order:
        pass

    @abstractmethod
    async def find_by_customer(self, customer_id: CustomerId) -> List[Order]:
        pass

# ==================== APPLICATION SERVICES ====================

class OrderApplicationService:
    """Application service orchestrating domain objects."""

    @inject
    def __init__(
        self,
        order_repository: IOrderRepository,
        customer_repository: ICustomerRepository,
        product_repository: IProductRepository,
        pricing_service: PricingService,
        inventory_service: InventoryService
    ):
        self.order_repository = order_repository
        self.customer_repository = customer_repository
        self.product_repository = product_repository
        self.pricing_service = pricing_service
        self.inventory_service = inventory_service

    async def create_order(self, customer_id: CustomerId, order_id: OrderId) -> Order:
        """Create a new order."""
        customer = await self.customer_repository.find_by_id(customer_id)
        if not customer:
            raise ValueError("Customer not found")

        order = Order(order_id, customer_id)
        await self.order_repository.save(order)
        return order

    async def add_item_to_order(
        self,
        order_id: OrderId,
        product_id: ProductId,
        quantity: int
    ) -> Order:
        """Add item to an existing order."""
        order = await self.order_repository.find_by_id(order_id)
        if not order:
            raise ValueError("Order not found")

        product = await self.product_repository.find_by_id(product_id)
        if not product:
            raise ValueError("Product not found")

        order.add_item(product, quantity)
        await self.order_repository.save(order)
        return order

    async def confirm_order(self, order_id: OrderId) -> Dict[str, Any]:
        """Confirm an order with full business logic."""
        order = await self.order_repository.find_by_id(order_id)
        if not order:
            raise ValueError("Order not found")

        customer = await self.customer_repository.find_by_id(order.customer_id)
        if not customer:
            raise ValueError("Customer not found")

        # Apply domain logic
        order.apply_customer_discount(customer)

        # Reserve inventory
        inventory_reserved = await self.inventory_service.reserve_inventory(order)
        if not inventory_reserved:
            raise ValueError("Unable to reserve inventory")

        # Confirm order
        order.confirm()

        # Calculate final amounts
        subtotal = order.get_subtotal()
        discount = order.get_discount_amount()
        tax = self.pricing_service.calculate_tax(order)
        shipping = self.pricing_service.calculate_shipping_cost(order, customer)
        total = order.get_total().add(tax).add(shipping)

        # Update customer order history
        customer.add_order(order.id)

        # Save changes
        await self.order_repository.save(order)
        await self.customer_repository.save(customer)

        return {
            "order_id": order.id.value,
            "status": order.status.value,
            "subtotal": subtotal.amount,
            "discount": discount.amount,
            "tax": tax.amount,
            "shipping": shipping.amount,
            "total": total.amount,
            "currency": total.currency
        }

# ==================== INFRASTRUCTURE ====================

# Repository Implementations
class InMemoryCustomerRepository(ICustomerRepository):
    def __init__(self):
        self._customers: Dict[str, Customer] = {}

    async def find_by_id(self, customer_id: CustomerId) -> Optional[Customer]:
        return self._customers.get(customer_id.value)

    async def save(self, customer: Customer) -> Customer:
        self._customers[customer.id.value] = customer
        return customer

class InMemoryProductRepository(IProductRepository):
    def __init__(self):
        self._products: Dict[str, Product] = {}

    async def find_by_id(self, product_id: ProductId) -> Optional[Product]:
        return self._products.get(product_id.value)

    async def save(self, product: Product) -> Product:
        self._products[product.id.value] = product
        return product

class InMemoryOrderRepository(IOrderRepository):
    def __init__(self):
        self._orders: Dict[str, Order] = {}

    async def find_by_id(self, order_id: OrderId) -> Optional[Order]:
        return self._orders.get(order_id.value)

    async def save(self, order: Order) -> Order:
        self._orders[order.id.value] = order
        return order

    async def find_by_customer(self, customer_id: CustomerId) -> List[Order]:
        return [
            order for order in self._orders.values()
            if order.customer_id == customer_id
        ]

# ==================== MODULE CONFIGURATION ====================

class DDDModule(Module):
    def configure(self):
        # Repositories
        self.bind(ICustomerRepository, InMemoryCustomerRepository).singleton()
        self.bind(IProductRepository, InMemoryProductRepository).singleton()
        self.bind(IOrderRepository, InMemoryOrderRepository).singleton()

        # Domain Services
        self.bind(PricingService, PricingService).singleton()
        self.bind(InventoryService, InventoryService).singleton()

        # Application Services
        self.bind(OrderApplicationService, OrderApplicationService).singleton()

# ==================== DEMO APPLICATION ====================

class DDDDemo:
    @inject
    def __init__(
        self,
        customer_repository: ICustomerRepository,
        product_repository: IProductRepository,
        order_service: OrderApplicationService
    ):
        self.customer_repository = customer_repository
        self.product_repository = product_repository
        self.order_service = order_service

    async def run_demo(self):
        """Demonstrate DDD patterns."""
        print("=== Domain-Driven Design Demo ===\n")

        # Setup test data
        await self._setup_test_data()

        # Create and process an order
        customer_id = CustomerId("customer-123")
        order_id = OrderId("order-456")

        print("1. Creating order...")
        order = await self.order_service.create_order(customer_id, order_id)
        print(f"Created order: {order.id.value}\n")

        print("2. Adding items to order...")
        await self.order_service.add_item_to_order(
            order_id,
            ProductId("laptop-001"),
            1
        )
        await self.order_service.add_item_to_order(
            order_id,
            ProductId("mouse-001"),
            2
        )
        print("Items added to order\n")

        print("3. Confirming order...")
        result = await self.order_service.confirm_order(order_id)
        print(f"Order confirmed: {result}\n")

    async def _setup_test_data(self):
        """Setup test customers and products."""
        # Create customers
        customer = Customer(
            CustomerId("customer-123"),
            "John Doe",
            EmailAddress("john@example.com"),
            CustomerType.PREMIUM
        )
        await self.customer_repository.save(customer)

        # Create products
        laptop = Product(
            ProductId("laptop-001"),
            "Gaming Laptop",
            Money(999.99),
            10
        )
        await self.product_repository.save(laptop)

        mouse = Product(
            ProductId("mouse-001"),
            "Wireless Mouse",
            Money(29.99),
            50
        )
        await self.product_repository.save(mouse)

# Usage Example
async def ddd_example():
    container = InjectQ()
    container.install(DDDModule())

    demo = container.get(DDDDemo)
    await demo.run_demo()
```

This architectural examples section demonstrates:

1. **Clean Architecture**: Complete implementation with proper layer separation and dependency inversion
2. **Domain-Driven Design**: Rich domain models with value objects, entities, aggregates, and domain services

Key architectural principles shown:
- Dependency inversion through interfaces
- Separation of concerns across layers
- Rich domain models with business logic
- Application services orchestrating domain operations
- Infrastructure implementations hidden behind abstractions
- Proper error handling and validation
- Comprehensive dependency injection configuration

Ready to continue with more architectural patterns or move to the next documentation section?
