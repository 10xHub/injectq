# Practical Examples

This section provides comprehensive, real-world examples of using InjectQ in various application scenarios and design patterns.

## 🚀 Web Application Example

### FastAPI E-commerce Application

```python
# main.py - Complete e-commerce application
from fastapi import FastAPI, Depends, HTTPException
from injectq import InjectQ, inject, Module
from typing import List, Optional
import asyncio

# Domain Models
class User:
    def __init__(self, id: str, name: str, email: str):
        self.id = id
        self.name = name
        self.email = email

class Product:
    def __init__(self, id: str, name: str, price: float, inventory: int):
        self.id = id
        self.name = name
        self.price = price
        self.inventory = inventory

class Order:
    def __init__(self, id: str, user_id: str, items: List[dict], total: float):
        self.id = id
        self.user_id = user_id
        self.items = items
        self.total = total

# Repository Layer
from abc import ABC, abstractmethod

class IUserRepository(ABC):
    @abstractmethod
    async def find_by_id(self, user_id: str) -> Optional[User]:
        pass
    
    @abstractmethod
    async def create(self, user: User) -> User:
        pass

class IProductRepository(ABC):
    @abstractmethod
    async def find_by_id(self, product_id: str) -> Optional[Product]:
        pass
    
    @abstractmethod
    async def update_inventory(self, product_id: str, quantity: int) -> bool:
        pass

class IOrderRepository(ABC):
    @abstractmethod
    async def create(self, order: Order) -> Order:
        pass
    
    @abstractmethod
    async def find_by_user(self, user_id: str) -> List[Order]:
        pass

# Concrete Implementations
class DatabaseUserRepository(IUserRepository):
    @inject
    async def __init__(self, db_connection: DatabaseConnection):
        self.db = db_connection

    async def find_by_id(self, user_id: str) -> Optional[User]:
        # Simulate database query
        await asyncio.sleep(0.01)
        return User(user_id, f"User {user_id}", f"user{user_id}@example.com")

    async def create(self, user: User) -> User:
        # Simulate database insert
        await asyncio.sleep(0.01)
        return user

class DatabaseProductRepository(IProductRepository):
    @inject
    async def __init__(self, db_connection: DatabaseConnection, cache: CacheService):
        self.db = db_connection
        self.cache = cache

    async def find_by_id(self, product_id: str) -> Optional[Product]:
        # Check cache first
        cached = await self.cache.get(f"product:{product_id}")
        if cached:
            return cached

        # Simulate database query
        await asyncio.sleep(0.01)
        product = Product(product_id, f"Product {product_id}", 99.99, 10)
        
        # Cache the result
        await self.cache.set(f"product:{product_id}", product, ttl=300)
        return product

    async def update_inventory(self, product_id: str, quantity: int) -> bool:
        # Simulate inventory update
        await asyncio.sleep(0.01)
        await self.cache.delete(f"product:{product_id}")  # Invalidate cache
        return True

class DatabaseOrderRepository(IOrderRepository):
    @inject
    async def __init__(self, db_connection: DatabaseConnection):
        self.db = db_connection

    async def create(self, order: Order) -> Order:
        # Simulate database insert
        await asyncio.sleep(0.01)
        return order

    async def find_by_user(self, user_id: str) -> List[Order]:
        # Simulate database query
        await asyncio.sleep(0.01)
        return []

# Service Layer
class UserService:
    @inject
    def __init__(self, user_repo: IUserRepository, email_service: EmailService):
        self.user_repo = user_repo
        self.email_service = email_service

    async def get_user(self, user_id: str) -> Optional[User]:
        return await self.user_repo.find_by_id(user_id)

    async def create_user(self, user_data: dict) -> User:
        user = User(
            id=user_data["id"],
            name=user_data["name"],
            email=user_data["email"]
        )
        
        created_user = await self.user_repo.create(user)
        
        # Send welcome email
        await self.email_service.send_welcome_email(created_user)
        
        return created_user

class ProductService:
    @inject
    def __init__(self, product_repo: IProductRepository):
        self.product_repo = product_repo

    async def get_product(self, product_id: str) -> Optional[Product]:
        return await self.product_repo.find_by_id(product_id)

    async def check_availability(self, product_id: str, quantity: int) -> bool:
        product = await self.product_repo.find_by_id(product_id)
        return product and product.inventory >= quantity

class OrderService:
    @inject
    def __init__(
        self,
        order_repo: IOrderRepository,
        product_service: ProductService,
        payment_service: PaymentService,
        notification_service: NotificationService
    ):
        self.order_repo = order_repo
        self.product_service = product_service
        self.payment_service = payment_service
        self.notification_service = notification_service

    async def create_order(self, user_id: str, items: List[dict]) -> Order:
        # Validate inventory
        for item in items:
            available = await self.product_service.check_availability(
                item["product_id"], item["quantity"]
            )
            if not available:
                raise HTTPException(
                    status_code=400,
                    detail=f"Product {item['product_id']} not available"
                )

        # Calculate total
        total = 0.0
        for item in items:
            product = await self.product_service.get_product(item["product_id"])
            total += product.price * item["quantity"]

        # Process payment
        payment_result = await self.payment_service.process_payment(user_id, total)
        if not payment_result.success:
            raise HTTPException(status_code=400, detail="Payment failed")

        # Create order
        order = Order(
            id=f"order_{user_id}_{len(items)}",
            user_id=user_id,
            items=items,
            total=total
        )

        created_order = await self.order_repo.create(order)

        # Send notifications
        await self.notification_service.send_order_confirmation(created_order)

        return created_order

# Infrastructure Services
class DatabaseConnection:
    @inject
    async def __init__(self, config: DatabaseConfig):
        self.config = config
        await self.connect()

    async def connect(self):
        # Simulate database connection
        await asyncio.sleep(0.1)

class CacheService:
    def __init__(self):
        self._cache = {}

    async def get(self, key: str):
        return self._cache.get(key)

    async def set(self, key: str, value, ttl: int = 300):
        self._cache[key] = value

    async def delete(self, key: str):
        self._cache.pop(key, None)

class EmailService:
    @inject
    def __init__(self, email_config: EmailConfig):
        self.config = email_config

    async def send_welcome_email(self, user: User):
        print(f"Sending welcome email to {user.email}")

class PaymentService:
    @inject
    def __init__(self, payment_config: PaymentConfig):
        self.config = payment_config

    async def process_payment(self, user_id: str, amount: float):
        # Simulate payment processing
        await asyncio.sleep(0.1)
        return PaymentResult(success=True, transaction_id=f"txn_{user_id}")

class NotificationService:
    @inject
    def __init__(self, notification_config: NotificationConfig):
        self.config = notification_config

    async def send_order_confirmation(self, order: Order):
        print(f"Order confirmation sent for order {order.id}")

# Configuration Classes
class DatabaseConfig:
    def __init__(self, host: str, port: int, database: str):
        self.host = host
        self.port = port
        self.database = database

class EmailConfig:
    def __init__(self, smtp_host: str, smtp_port: int):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port

class PaymentConfig:
    def __init__(self, api_key: str, endpoint: str):
        self.api_key = api_key
        self.endpoint = endpoint

class NotificationConfig:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

class PaymentResult:
    def __init__(self, success: bool, transaction_id: str):
        self.success = success
        self.transaction_id = transaction_id

# Application Module
class ECommerceModule(Module):
    def configure(self):
        # Configuration
        self.bind(DatabaseConfig, DatabaseConfig(
            host="localhost",
            port=5432,
            database="ecommerce"
        )).singleton()

        self.bind(EmailConfig, EmailConfig(
            smtp_host="smtp.example.com",
            smtp_port=587
        )).singleton()

        self.bind(PaymentConfig, PaymentConfig(
            api_key="test_key",
            endpoint="https://api.payment.com"
        )).singleton()

        self.bind(NotificationConfig, NotificationConfig(
            webhook_url="https://notifications.example.com"
        )).singleton()

        # Infrastructure
        self.bind(DatabaseConnection, DatabaseConnection).singleton()
        self.bind(CacheService, CacheService).singleton()
        self.bind(EmailService, EmailService).singleton()
        self.bind(PaymentService, PaymentService).singleton()
        self.bind(NotificationService, NotificationService).singleton()

        # Repositories
        self.bind(IUserRepository, DatabaseUserRepository).scoped()
        self.bind(IProductRepository, DatabaseProductRepository).scoped()
        self.bind(IOrderRepository, DatabaseOrderRepository).scoped()

        # Services
        self.bind(UserService, UserService).scoped()
        self.bind(ProductService, ProductService).scoped()
        self.bind(OrderService, OrderService).scoped()

# FastAPI Application
app = FastAPI(title="E-commerce API")

# Setup DI container
container = InjectQ()
container.install(ECommerceModule())

# Dependency provider for FastAPI
def get_container():
    return container

# API Endpoints
@app.post("/users")
async def create_user(
    user_data: dict,
    container: InjectQ = Depends(get_container)
):
    user_service = container.get(UserService)
    user = await user_service.create_user(user_data)
    return {"id": user.id, "name": user.name, "email": user.email}

@app.get("/users/{user_id}")
async def get_user(
    user_id: str,
    container: InjectQ = Depends(get_container)
):
    user_service = container.get(UserService)
    user = await user_service.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"id": user.id, "name": user.name, "email": user.email}

@app.get("/products/{product_id}")
async def get_product(
    product_id: str,
    container: InjectQ = Depends(get_container)
):
    product_service = container.get(ProductService)
    product = await product_service.get_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return {
        "id": product.id,
        "name": product.name,
        "price": product.price,
        "inventory": product.inventory
    }

@app.post("/orders")
async def create_order(
    order_data: dict,
    container: InjectQ = Depends(get_container)
):
    order_service = container.get(OrderService)
    order = await order_service.create_order(
        order_data["user_id"],
        order_data["items"]
    )
    return {
        "id": order.id,
        "user_id": order.user_id,
        "items": order.items,
        "total": order.total
    }

# Application startup
@app.on_event("startup")
async def startup_event():
    print("E-commerce API started successfully!")

# Run with: uvicorn main:app --reload
```

## 🧮 Scientific Computing Example

### Data Processing Pipeline

```python
# data_pipeline.py - Scientific data processing pipeline
import numpy as np
import pandas as pd
from abc import ABC, abstractmethod
from injectq import InjectQ, inject, Module
import asyncio
from typing import List, Dict, Any

# Data Models
class Dataset:
    def __init__(self, name: str, data: pd.DataFrame):
        self.name = name
        self.data = data
        self.metadata = {}

class ProcessingResult:
    def __init__(self, dataset_name: str, results: Dict[str, Any]):
        self.dataset_name = dataset_name
        self.results = results
        self.timestamp = pd.Timestamp.now()

# Data Source Interfaces
class IDataSource(ABC):
    @abstractmethod
    async def load_data(self, source_id: str) -> Dataset:
        pass

class IDataSink(ABC):
    @abstractmethod
    async def save_results(self, results: ProcessingResult) -> bool:
        pass

# Data Processing Interfaces
class IDataProcessor(ABC):
    @abstractmethod
    async def process(self, dataset: Dataset) -> ProcessingResult:
        pass

class IDataValidator(ABC):
    @abstractmethod
    async def validate(self, dataset: Dataset) -> bool:
        pass

# Concrete Implementations
class CSVDataSource(IDataSource):
    @inject
    def __init__(self, config: DataSourceConfig):
        self.config = config

    async def load_data(self, source_id: str) -> Dataset:
        # Simulate loading CSV data
        await asyncio.sleep(0.1)
        
        # Generate sample data
        np.random.seed(42)
        data = pd.DataFrame({
            'timestamp': pd.date_range('2023-01-01', periods=1000, freq='H'),
            'temperature': np.random.normal(20, 5, 1000),
            'humidity': np.random.normal(60, 10, 1000),
            'pressure': np.random.normal(1013, 20, 1000)
        })
        
        return Dataset(name=f"dataset_{source_id}", data=data)

class DatabaseDataSink(IDataSink):
    @inject
    def __init__(self, db_connection: DatabaseConnection):
        self.db = db_connection

    async def save_results(self, results: ProcessingResult) -> bool:
        # Simulate saving to database
        await asyncio.sleep(0.05)
        print(f"Saved results for {results.dataset_name} to database")
        return True

class StatisticalProcessor(IDataProcessor):
    @inject
    def __init__(self, stats_config: StatisticsConfig):
        self.config = stats_config

    async def process(self, dataset: Dataset) -> ProcessingResult:
        # Perform statistical analysis
        data = dataset.data
        
        results = {
            'mean_temperature': data['temperature'].mean(),
            'std_temperature': data['temperature'].std(),
            'mean_humidity': data['humidity'].mean(),
            'std_humidity': data['humidity'].std(),
            'correlation_temp_humidity': data['temperature'].corr(data['humidity']),
            'total_records': len(data)
        }
        
        return ProcessingResult(dataset.name, results)

class AnomalyDetectionProcessor(IDataProcessor):
    @inject
    def __init__(self, anomaly_config: AnomalyConfig):
        self.config = anomaly_config

    async def process(self, dataset: Dataset) -> ProcessingResult:
        # Detect anomalies using Z-score
        data = dataset.data
        
        z_scores = np.abs((data['temperature'] - data['temperature'].mean()) / data['temperature'].std())
        anomalies = data[z_scores > self.config.threshold]
        
        results = {
            'anomaly_count': len(anomalies),
            'anomaly_percentage': (len(anomalies) / len(data)) * 100,
            'max_z_score': z_scores.max(),
            'anomaly_timestamps': anomalies['timestamp'].tolist()
        }
        
        return ProcessingResult(dataset.name, results)

class DataQualityValidator(IDataValidator):
    @inject
    def __init__(self, quality_config: QualityConfig):
        self.config = quality_config

    async def validate(self, dataset: Dataset) -> bool:
        data = dataset.data
        
        # Check for missing values
        missing_percentage = (data.isnull().sum().sum() / (len(data) * len(data.columns))) * 100
        if missing_percentage > self.config.max_missing_percentage:
            return False
        
        # Check for outliers
        for column in ['temperature', 'humidity', 'pressure']:
            z_scores = np.abs((data[column] - data[column].mean()) / data[column].std())
            outlier_percentage = (len(data[z_scores > 3]) / len(data)) * 100
            if outlier_percentage > self.config.max_outlier_percentage:
                return False
        
        return True

# Data Pipeline Orchestrator
class DataPipeline:
    @inject
    def __init__(
        self,
        data_source: IDataSource,
        data_sink: IDataSink,
        processors: List[IDataProcessor],
        validator: IDataValidator,
        logger: LoggingService
    ):
        self.data_source = data_source
        self.data_sink = data_sink
        self.processors = processors
        self.validator = validator
        self.logger = logger

    async def process_dataset(self, source_id: str) -> List[ProcessingResult]:
        """Process a single dataset through the entire pipeline."""
        try:
            # Load data
            self.logger.info(f"Loading dataset {source_id}")
            dataset = await self.data_source.load_data(source_id)
            
            # Validate data quality
            self.logger.info(f"Validating dataset {dataset.name}")
            is_valid = await self.validator.validate(dataset)
            if not is_valid:
                self.logger.error(f"Dataset {dataset.name} failed validation")
                return []
            
            # Process data with all processors
            results = []
            for processor in self.processors:
                self.logger.info(f"Processing {dataset.name} with {processor.__class__.__name__}")
                result = await processor.process(dataset)
                results.append(result)
                
                # Save results
                await self.data_sink.save_results(result)
            
            self.logger.info(f"Pipeline completed for dataset {dataset.name}")
            return results
            
        except Exception as e:
            self.logger.error(f"Pipeline failed for dataset {source_id}: {str(e)}")
            raise

    async def process_multiple_datasets(self, source_ids: List[str]) -> Dict[str, List[ProcessingResult]]:
        """Process multiple datasets concurrently."""
        tasks = [self.process_dataset(source_id) for source_id in source_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {
            source_id: result if not isinstance(result, Exception) else []
            for source_id, result in zip(source_ids, results)
        }

# Configuration Classes
class DataSourceConfig:
    def __init__(self, base_path: str, file_format: str = "csv"):
        self.base_path = base_path
        self.file_format = file_format

class StatisticsConfig:
    def __init__(self, confidence_level: float = 0.95):
        self.confidence_level = confidence_level

class AnomalyConfig:
    def __init__(self, threshold: float = 3.0):
        self.threshold = threshold

class QualityConfig:
    def __init__(self, max_missing_percentage: float = 5.0, max_outlier_percentage: float = 1.0):
        self.max_missing_percentage = max_missing_percentage
        self.max_outlier_percentage = max_outlier_percentage

# Logging Service
class LoggingService:
    def __init__(self):
        import logging
        self.logger = logging.getLogger("DataPipeline")
        self.logger.setLevel(logging.INFO)
        
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def info(self, message: str):
        self.logger.info(message)

    def error(self, message: str):
        self.logger.error(message)

    def warning(self, message: str):
        self.logger.warning(message)

# Data Processing Module
class DataProcessingModule(Module):
    def configure(self):
        # Configuration
        self.bind(DataSourceConfig, DataSourceConfig(
            base_path="/data/input",
            file_format="csv"
        )).singleton()
        
        self.bind(StatisticsConfig, StatisticsConfig(
            confidence_level=0.95
        )).singleton()
        
        self.bind(AnomalyConfig, AnomalyConfig(
            threshold=3.0
        )).singleton()
        
        self.bind(QualityConfig, QualityConfig(
            max_missing_percentage=5.0,
            max_outlier_percentage=1.0
        )).singleton()

        # Infrastructure
        self.bind(DatabaseConnection, DatabaseConnection).singleton()
        self.bind(LoggingService, LoggingService).singleton()

        # Data Sources and Sinks
        self.bind(IDataSource, CSVDataSource).singleton()
        self.bind(IDataSink, DatabaseDataSink).singleton()

        # Validators
        self.bind(IDataValidator, DataQualityValidator).singleton()

        # Processors (multiple implementations)
        self.bind(IDataProcessor, StatisticalProcessor, name="stats").singleton()
        self.bind(IDataProcessor, AnomalyDetectionProcessor, name="anomaly").singleton()

        # Pipeline
        self.bind(List[IDataProcessor], lambda: [
            self.container.get(IDataProcessor, name="stats"),
            self.container.get(IDataProcessor, name="anomaly")
        ]).singleton()
        
        self.bind(DataPipeline, DataPipeline).singleton()

# Example Usage
async def main():
    # Setup container
    container = InjectQ()
    container.install(DataProcessingModule())

    # Get pipeline
    pipeline = container.get(DataPipeline)

    # Process multiple datasets
    source_ids = ["weather_station_1", "weather_station_2", "weather_station_3"]
    results = await pipeline.process_multiple_datasets(source_ids)

    # Display results
    for source_id, dataset_results in results.items():
        print(f"\nResults for {source_id}:")
        for result in dataset_results:
            print(f"  Processor: {result.dataset_name}")
            for key, value in result.results.items():
                print(f"    {key}: {value}")

if __name__ == "__main__":
    asyncio.run(main())
```

## 🤖 Microservices Example

### Event-Driven Microservice

```python
# microservice.py - Event-driven microservice with InjectQ
from injectq import InjectQ, inject, Module
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Callable
import asyncio
import json
from dataclasses import dataclass, asdict
from datetime import datetime

# Event System
@dataclass
class Event:
    event_type: str
    event_id: str
    timestamp: datetime
    data: Dict
    source: str

class IEventBus(ABC):
    @abstractmethod
    async def publish(self, event: Event) -> bool:
        pass
    
    @abstractmethod
    async def subscribe(self, event_type: str, handler: Callable) -> bool:
        pass

class IEventStore(ABC):
    @abstractmethod
    async def store_event(self, event: Event) -> bool:
        pass
    
    @abstractmethod
    async def get_events(self, event_type: str, limit: int = 100) -> List[Event]:
        pass

# Command and Query Separation
@dataclass
class Command:
    command_type: str
    command_id: str
    data: Dict
    timestamp: datetime

@dataclass
class Query:
    query_type: str
    query_id: str
    parameters: Dict
    timestamp: datetime

class ICommandHandler(ABC):
    @abstractmethod
    async def handle(self, command: Command) -> Dict:
        pass

class IQueryHandler(ABC):
    @abstractmethod
    async def handle(self, query: Query) -> Dict:
        pass

# Domain Models
@dataclass
class Order:
    id: str
    customer_id: str
    items: List[Dict]
    total_amount: float
    status: str
    created_at: datetime

@dataclass
class Customer:
    id: str
    name: str
    email: str
    created_at: datetime

# Repositories
class IOrderRepository(ABC):
    @abstractmethod
    async def save(self, order: Order) -> Order:
        pass
    
    @abstractmethod
    async def find_by_id(self, order_id: str) -> Optional[Order]:
        pass
    
    @abstractmethod
    async def find_by_customer(self, customer_id: str) -> List[Order]:
        pass

class ICustomerRepository(ABC):
    @abstractmethod
    async def save(self, customer: Customer) -> Customer:
        pass
    
    @abstractmethod
    async def find_by_id(self, customer_id: str) -> Optional[Customer]:
        pass

# Event Bus Implementation
class InMemoryEventBus(IEventBus):
    def __init__(self):
        self.subscribers: Dict[str, List[Callable]] = {}

    async def publish(self, event: Event) -> bool:
        handlers = self.subscribers.get(event.event_type, [])
        
        for handler in handlers:
            try:
                await handler(event)
            except Exception as e:
                print(f"Error handling event {event.event_id}: {e}")
        
        return True

    async def subscribe(self, event_type: str, handler: Callable) -> bool:
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        
        self.subscribers[event_type].append(handler)
        return True

class DatabaseEventStore(IEventStore):
    @inject
    def __init__(self, db_connection: DatabaseConnection):
        self.db = db_connection
        self.events = []  # In-memory for demo

    async def store_event(self, event: Event) -> bool:
        # Simulate database storage
        self.events.append(event)
        return True

    async def get_events(self, event_type: str, limit: int = 100) -> List[Event]:
        # Filter events by type
        filtered_events = [e for e in self.events if e.event_type == event_type]
        return filtered_events[:limit]

# Repository Implementations
class DatabaseOrderRepository(IOrderRepository):
    @inject
    def __init__(self, db_connection: DatabaseConnection, event_bus: IEventBus):
        self.db = db_connection
        self.event_bus = event_bus
        self.orders = {}  # In-memory for demo

    async def save(self, order: Order) -> Order:
        self.orders[order.id] = order
        
        # Publish event
        event = Event(
            event_type="order.created" if order.id not in self.orders else "order.updated",
            event_id=f"event_{order.id}_{datetime.now().timestamp()}",
            timestamp=datetime.now(),
            data=asdict(order),
            source="order_service"
        )
        await self.event_bus.publish(event)
        
        return order

    async def find_by_id(self, order_id: str) -> Optional[Order]:
        return self.orders.get(order_id)

    async def find_by_customer(self, customer_id: str) -> List[Order]:
        return [order for order in self.orders.values() if order.customer_id == customer_id]

class DatabaseCustomerRepository(ICustomerRepository):
    @inject
    def __init__(self, db_connection: DatabaseConnection, event_bus: IEventBus):
        self.db = db_connection
        self.event_bus = event_bus
        self.customers = {}  # In-memory for demo

    async def save(self, customer: Customer) -> Customer:
        self.customers[customer.id] = customer
        
        # Publish event
        event = Event(
            event_type="customer.created" if customer.id not in self.customers else "customer.updated",
            event_id=f"event_{customer.id}_{datetime.now().timestamp()}",
            timestamp=datetime.now(),
            data=asdict(customer),
            source="customer_service"
        )
        await self.event_bus.publish(event)
        
        return customer

    async def find_by_id(self, customer_id: str) -> Optional[Customer]:
        return self.customers.get(customer_id)

# Command Handlers
class CreateOrderCommandHandler(ICommandHandler):
    @inject
    def __init__(
        self,
        order_repo: IOrderRepository,
        customer_repo: ICustomerRepository,
        event_store: IEventStore
    ):
        self.order_repo = order_repo
        self.customer_repo = customer_repo
        self.event_store = event_store

    async def handle(self, command: Command) -> Dict:
        if command.command_type != "create_order":
            raise ValueError(f"Unsupported command type: {command.command_type}")

        data = command.data
        
        # Validate customer exists
        customer = await self.customer_repo.find_by_id(data["customer_id"])
        if not customer:
            return {"success": False, "error": "Customer not found"}

        # Create order
        order = Order(
            id=data["order_id"],
            customer_id=data["customer_id"],
            items=data["items"],
            total_amount=data["total_amount"],
            status="created",
            created_at=datetime.now()
        )

        # Save order
        saved_order = await self.order_repo.save(order)

        # Store command as event
        command_event = Event(
            event_type="command.executed",
            event_id=command.command_id,
            timestamp=command.timestamp,
            data={"command": asdict(command), "result": asdict(saved_order)},
            source="order_service"
        )
        await self.event_store.store_event(command_event)

        return {"success": True, "order_id": saved_order.id}

class CreateCustomerCommandHandler(ICommandHandler):
    @inject
    def __init__(self, customer_repo: ICustomerRepository, event_store: IEventStore):
        self.customer_repo = customer_repo
        self.event_store = event_store

    async def handle(self, command: Command) -> Dict:
        if command.command_type != "create_customer":
            raise ValueError(f"Unsupported command type: {command.command_type}")

        data = command.data

        # Create customer
        customer = Customer(
            id=data["customer_id"],
            name=data["name"],
            email=data["email"],
            created_at=datetime.now()
        )

        # Save customer
        saved_customer = await self.customer_repo.save(customer)

        # Store command as event
        command_event = Event(
            event_type="command.executed",
            event_id=command.command_id,
            timestamp=command.timestamp,
            data={"command": asdict(command), "result": asdict(saved_customer)},
            source="customer_service"
        )
        await self.event_store.store_event(command_event)

        return {"success": True, "customer_id": saved_customer.id}

# Query Handlers
class GetOrderQueryHandler(IQueryHandler):
    @inject
    def __init__(self, order_repo: IOrderRepository):
        self.order_repo = order_repo

    async def handle(self, query: Query) -> Dict:
        if query.query_type != "get_order":
            raise ValueError(f"Unsupported query type: {query.query_type}")

        order_id = query.parameters["order_id"]
        order = await self.order_repo.find_by_id(order_id)

        if order:
            return {"success": True, "order": asdict(order)}
        else:
            return {"success": False, "error": "Order not found"}

class GetCustomerOrdersQueryHandler(IQueryHandler):
    @inject
    def __init__(self, order_repo: IOrderRepository):
        self.order_repo = order_repo

    async def handle(self, query: Query) -> Dict:
        if query.query_type != "get_customer_orders":
            raise ValueError(f"Unsupported query type: {query.query_type}")

        customer_id = query.parameters["customer_id"]
        orders = await self.order_repo.find_by_customer(customer_id)

        return {
            "success": True,
            "orders": [asdict(order) for order in orders]
        }

# Event Handlers
class OrderEventHandler:
    @inject
    def __init__(self, notification_service: NotificationService):
        self.notification_service = notification_service

    async def handle_order_created(self, event: Event):
        order_data = event.data
        print(f"Order created: {order_data['id']}")
        
        # Send notification
        await self.notification_service.send_order_confirmation(order_data)

    async def handle_order_updated(self, event: Event):
        order_data = event.data
        print(f"Order updated: {order_data['id']}")

class CustomerEventHandler:
    @inject
    def __init__(self, email_service: EmailService):
        self.email_service = email_service

    async def handle_customer_created(self, event: Event):
        customer_data = event.data
        print(f"Customer created: {customer_data['id']}")
        
        # Send welcome email
        await self.email_service.send_welcome_email(customer_data)

# Application Services
class CommandDispatcher:
    @inject
    def __init__(self):
        self.handlers: Dict[str, ICommandHandler] = {}

    def register_handler(self, command_type: str, handler: ICommandHandler):
        self.handlers[command_type] = handler

    async def dispatch(self, command: Command) -> Dict:
        handler = self.handlers.get(command.command_type)
        if not handler:
            raise ValueError(f"No handler for command type: {command.command_type}")
        
        return await handler.handle(command)

class QueryDispatcher:
    @inject
    def __init__(self):
        self.handlers: Dict[str, IQueryHandler] = {}

    def register_handler(self, query_type: str, handler: IQueryHandler):
        self.handlers[query_type] = handler

    async def dispatch(self, query: Query) -> Dict:
        handler = self.handlers.get(query.query_type)
        if not handler:
            raise ValueError(f"No handler for query type: {query.query_type}")
        
        return await handler.handle(query)

# Infrastructure Services
class NotificationService:
    def __init__(self):
        pass

    async def send_order_confirmation(self, order_data: Dict):
        print(f"Sending order confirmation for order {order_data['id']}")

class EmailService:
    def __init__(self):
        pass

    async def send_welcome_email(self, customer_data: Dict):
        print(f"Sending welcome email to {customer_data['email']}")

# Microservice Application
class MicroserviceApplication:
    @inject
    def __init__(
        self,
        event_bus: IEventBus,
        command_dispatcher: CommandDispatcher,
        query_dispatcher: QueryDispatcher,
        order_event_handler: OrderEventHandler,
        customer_event_handler: CustomerEventHandler
    ):
        self.event_bus = event_bus
        self.command_dispatcher = command_dispatcher
        self.query_dispatcher = query_dispatcher
        self.order_event_handler = order_event_handler
        self.customer_event_handler = customer_event_handler

    async def initialize(self):
        """Initialize the microservice."""
        # Register event handlers
        await self.event_bus.subscribe("order.created", self.order_event_handler.handle_order_created)
        await self.event_bus.subscribe("order.updated", self.order_event_handler.handle_order_updated)
        await self.event_bus.subscribe("customer.created", self.customer_event_handler.handle_customer_created)

        print("Microservice initialized successfully")

    async def process_command(self, command_data: Dict) -> Dict:
        """Process a command."""
        command = Command(
            command_type=command_data["command_type"],
            command_id=command_data["command_id"],
            data=command_data["data"],
            timestamp=datetime.now()
        )
        
        return await self.command_dispatcher.dispatch(command)

    async def process_query(self, query_data: Dict) -> Dict:
        """Process a query."""
        query = Query(
            query_type=query_data["query_type"],
            query_id=query_data["query_id"],
            parameters=query_data["parameters"],
            timestamp=datetime.now()
        )
        
        return await self.query_dispatcher.dispatch(query)

# Module Configuration
class MicroserviceModule(Module):
    def configure(self):
        # Infrastructure
        self.bind(DatabaseConnection, DatabaseConnection).singleton()
        self.bind(IEventBus, InMemoryEventBus).singleton()
        self.bind(IEventStore, DatabaseEventStore).singleton()
        
        # Repositories
        self.bind(IOrderRepository, DatabaseOrderRepository).singleton()
        self.bind(ICustomerRepository, DatabaseCustomerRepository).singleton()
        
        # Command Handlers
        self.bind(ICommandHandler, CreateOrderCommandHandler, name="create_order").singleton()
        self.bind(ICommandHandler, CreateCustomerCommandHandler, name="create_customer").singleton()
        
        # Query Handlers
        self.bind(IQueryHandler, GetOrderQueryHandler, name="get_order").singleton()
        self.bind(IQueryHandler, GetCustomerOrdersQueryHandler, name="get_customer_orders").singleton()
        
        # Dispatchers
        self.bind(CommandDispatcher, self.create_command_dispatcher).singleton()
        self.bind(QueryDispatcher, self.create_query_dispatcher).singleton()
        
        # Event Handlers
        self.bind(OrderEventHandler, OrderEventHandler).singleton()
        self.bind(CustomerEventHandler, CustomerEventHandler).singleton()
        
        # Services
        self.bind(NotificationService, NotificationService).singleton()
        self.bind(EmailService, EmailService).singleton()
        
        # Application
        self.bind(MicroserviceApplication, MicroserviceApplication).singleton()

    def create_command_dispatcher(self) -> CommandDispatcher:
        dispatcher = CommandDispatcher()
        dispatcher.register_handler("create_order", self.container.get(ICommandHandler, name="create_order"))
        dispatcher.register_handler("create_customer", self.container.get(ICommandHandler, name="create_customer"))
        return dispatcher

    def create_query_dispatcher(self) -> QueryDispatcher:
        dispatcher = QueryDispatcher()
        dispatcher.register_handler("get_order", self.container.get(IQueryHandler, name="get_order"))
        dispatcher.register_handler("get_customer_orders", self.container.get(IQueryHandler, name="get_customer_orders"))
        return dispatcher

# Example Usage
async def main():
    # Setup container
    container = InjectQ()
    container.install(MicroserviceModule())

    # Get application
    app = container.get(MicroserviceApplication)
    await app.initialize()

    # Create customer
    customer_command = {
        "command_type": "create_customer",
        "command_id": "cmd_001",
        "data": {
            "customer_id": "cust_001",
            "name": "John Doe",
            "email": "john@example.com"
        }
    }
    
    result = await app.process_command(customer_command)
    print(f"Customer creation result: {result}")

    # Create order
    order_command = {
        "command_type": "create_order",
        "command_id": "cmd_002",
        "data": {
            "order_id": "order_001",
            "customer_id": "cust_001",
            "items": [{"product_id": "prod_001", "quantity": 2, "price": 50.0}],
            "total_amount": 100.0
        }
    }
    
    result = await app.process_command(order_command)
    print(f"Order creation result: {result}")

    # Query order
    order_query = {
        "query_type": "get_order",
        "query_id": "query_001",
        "parameters": {"order_id": "order_001"}
    }
    
    result = await app.process_query(order_query)
    print(f"Order query result: {result}")

    # Query customer orders
    customer_orders_query = {
        "query_type": "get_customer_orders",
        "query_id": "query_002",
        "parameters": {"customer_id": "cust_001"}
    }
    
    result = await app.process_query(customer_orders_query)
    print(f"Customer orders query result: {result}")

if __name__ == "__main__":
    asyncio.run(main())
```

This examples section provides comprehensive, real-world examples that demonstrate:

1. **Web Application Example**: Complete FastAPI e-commerce application showing layered architecture with repositories, services, and proper dependency injection
2. **Scientific Computing Example**: Data processing pipeline with multiple processors, validators, and async processing capabilities
3. **Microservices Example**: Event-driven microservice with CQRS pattern, event sourcing, and proper separation of concerns

Each example shows:
- Proper interface usage and abstraction
- Module configuration and dependency binding
- Async/await patterns
- Error handling and validation
- Testing considerations
- Real-world architectural patterns

Ready to continue with more examples or move to the next section?
