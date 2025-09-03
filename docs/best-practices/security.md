# Security Best Practices

This guide covers essential security considerations when using InjectQ in production applications, including dependency validation, secure configuration management, and protection against common vulnerabilities.

## 🔒 Dependency Validation and Security

### Secure Dependency Registration

```python
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type
from injectq import InjectQ, Module, inject
import hashlib
import secrets
from dataclasses import dataclass

class ISecurityValidator(ABC):
    """Interface for dependency security validation."""
    
    @abstractmethod
    def validate_dependency(self, dependency_type: Type, instance: Any) -> bool:
        pass
    
    @abstractmethod
    def validate_configuration(self, config: Dict[str, Any]) -> bool:
        pass

class DependencySecurityValidator(ISecurityValidator):
    """Validates dependencies for security compliance."""
    
    def __init__(self):
        self.allowed_types: set = set()
        self.forbidden_patterns: List[str] = [
            "eval", "exec", "compile", "__import__"
        ]
    
    def validate_dependency(self, dependency_type: Type, instance: Any) -> bool:
        """Validate that a dependency is safe to use."""
        # Check if type is explicitly allowed
        if dependency_type in self.allowed_types:
            return True
        
        # Check for dangerous patterns in type name
        type_name = dependency_type.__name__.lower()
        module_name = getattr(dependency_type, "__module__", "").lower()
        
        for pattern in self.forbidden_patterns:
            if pattern in type_name or pattern in module_name:
                return False
        
        # Validate instance attributes
        if hasattr(instance, "__dict__"):
            for attr_name in instance.__dict__:
                if any(pattern in attr_name.lower() for pattern in self.forbidden_patterns):
                    return False
        
        return True
    
    def validate_configuration(self, config: Dict[str, Any]) -> bool:
        """Validate configuration for security issues."""
        dangerous_keys = ["password", "secret", "key", "token"]
        
        for key, value in config.items():
            # Check for credentials in plain text
            if any(dangerous in key.lower() for dangerous in dangerous_keys):
                if isinstance(value, str) and len(value) > 0:
                    # Should not be plain text
                    if not self._is_encrypted_or_env_var(value):
                        return False
        
        return True
    
    def _is_encrypted_or_env_var(self, value: str) -> bool:
        """Check if value is encrypted or environment variable reference."""
        return (
            value.startswith("${") and value.endswith("}") or  # Environment variable
            value.startswith("enc:") or  # Encrypted value
            len(value) > 32 and all(c in "0123456789abcdef" for c in value.lower())  # Hash
        )

class SecureModule(Module):
    """Base module with security validation."""
    
    def __init__(self):
        super().__init__()
        self.security_validator = DependencySecurityValidator()
    
    def configure(self):
        """Configure module with security checks."""
        self._configure_dependencies()
        self._validate_security()
    
    def _configure_dependencies(self):
        """Override in subclasses."""
        pass
    
    def _validate_security(self):
        """Validate all configured dependencies."""
        # This would be called after dependency configuration
        pass
    
    def bind(self, interface: Type, implementation: Type, **kwargs):
        """Secure binding with validation."""
        # Validate the implementation type
        if hasattr(implementation, "__init__"):
            temp_instance = object.__new__(implementation)
            if not self.security_validator.validate_dependency(implementation, temp_instance):
                raise SecurityError(f"Dependency {implementation} failed security validation")
        
        return super().bind(interface, implementation, **kwargs)

class SecurityError(Exception):
    """Raised when security validation fails."""
    pass
```

### Input Validation and Sanitization

```python
import re
from typing import Any, Dict, Union
from html import escape
import bleach

class InputValidator:
    """Validates and sanitizes user inputs."""
    
    def __init__(self):
        self.sql_injection_patterns = [
            r"(\'|(\')+|(;)+|(\-\-)+|(\s)+(\-\-)+)",
            r"((\%27)|(\'))((\%6F)|o|(\%4F))((\%72)|r|(\%52))",
            r"((\%27)|(\'))union",
            r"exec(\s|\+)+(s|x)p\w+",
            r"select.*from",
            r"insert.*into",
            r"update.*set",
            r"delete.*from",
            r"drop.*table",
            r"create.*table"
        ]
        
        self.xss_patterns = [
            r"<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>",
            r"javascript:",
            r"vbscript:",
            r"onload=",
            r"onerror=",
            r"onclick="
        ]
    
    def validate_sql_injection(self, value: str) -> bool:
        """Check for SQL injection patterns."""
        if not isinstance(value, str):
            return True
        
        value_lower = value.lower()
        for pattern in self.sql_injection_patterns:
            if re.search(pattern, value_lower, re.IGNORECASE):
                return False
        return True
    
    def validate_xss(self, value: str) -> bool:
        """Check for XSS patterns."""
        if not isinstance(value, str):
            return True
        
        for pattern in self.xss_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                return False
        return True
    
    def sanitize_html(self, value: str) -> str:
        """Sanitize HTML content."""
        if not isinstance(value, str):
            return str(value)
        
        # Allow only safe HTML tags
        allowed_tags = ['p', 'br', 'strong', 'em', 'u', 'ol', 'ul', 'li']
        allowed_attributes = {}
        
        return bleach.clean(value, tags=allowed_tags, attributes=allowed_attributes)
    
    def sanitize_input(self, value: Any) -> Any:
        """General input sanitization."""
        if isinstance(value, str):
            # Basic sanitization
            value = escape(value)  # HTML escape
            value = value.strip()  # Remove whitespace
            
            # Validate for common attacks
            if not self.validate_sql_injection(value):
                raise SecurityError("Potential SQL injection detected")
            
            if not self.validate_xss(value):
                raise SecurityError("Potential XSS attack detected")
            
            return value
        
        elif isinstance(value, dict):
            return {k: self.sanitize_input(v) for k, v in value.items()}
        
        elif isinstance(value, list):
            return [self.sanitize_input(item) for item in value]
        
        return value

class SecureDataService:
    """Service that handles data securely."""
    
    @inject
    def __init__(
        self,
        database: Database,
        input_validator: InputValidator,
        audit_logger: AuditLogger
    ):
        self.database = database
        self.validator = input_validator
        self.audit_logger = audit_logger
    
    async def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create user with input validation."""
        # Log the operation
        self.audit_logger.log_operation("create_user", user_data.get("email", "unknown"))
        
        try:
            # Validate and sanitize inputs
            sanitized_data = self.validator.sanitize_input(user_data)
            
            # Additional business validation
            if not self._validate_user_data(sanitized_data):
                raise ValueError("Invalid user data")
            
            # Create user in database
            user = await self.database.create_user(sanitized_data)
            
            # Remove sensitive data from response
            safe_user = self._remove_sensitive_fields(user)
            
            return {"success": True, "user": safe_user}
            
        except Exception as e:
            self.audit_logger.log_error("create_user_failed", str(e))
            raise
    
    def _validate_user_data(self, data: Dict[str, Any]) -> bool:
        """Validate user data according to business rules."""
        required_fields = ["email", "username"]
        
        for field in required_fields:
            if field not in data or not data[field]:
                return False
        
        # Email validation
        email = data["email"]
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, email):
            return False
        
        return True
    
    def _remove_sensitive_fields(self, user: Dict[str, Any]) -> Dict[str, Any]:
        """Remove sensitive fields from user data."""
        sensitive_fields = ["password", "password_hash", "salt", "api_key"]
        return {k: v for k, v in user.items() if k not in sensitive_fields}
```

## 🔐 Configuration Security

### Secure Configuration Management

```python
import os
import base64
from cryptography.fernet import Fernet
from typing import Dict, Any, Optional

class SecureConfigManager:
    """Manages application configuration securely."""
    
    def __init__(self, encryption_key: Optional[bytes] = None):
        if encryption_key is None:
            # Get from environment or generate
            key_str = os.getenv("CONFIG_ENCRYPTION_KEY")
            if key_str:
                self.encryption_key = base64.urlsafe_b64decode(key_str.encode())
            else:
                self.encryption_key = Fernet.generate_key()
        else:
            self.encryption_key = encryption_key
        
        self.cipher = Fernet(self.encryption_key)
        self._config_cache: Dict[str, Any] = {}
    
    def encrypt_value(self, value: str) -> str:
        """Encrypt a configuration value."""
        encrypted = self.cipher.encrypt(value.encode())
        return base64.urlsafe_b64encode(encrypted).decode()
    
    def decrypt_value(self, encrypted_value: str) -> str:
        """Decrypt a configuration value."""
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_value.encode())
            decrypted = self.cipher.decrypt(encrypted_bytes)
            return decrypted.decode()
        except Exception:
            raise SecurityError("Failed to decrypt configuration value")
    
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Get configuration value with decryption if needed."""
        # Check cache first
        if key in self._config_cache:
            return self._config_cache[key]
        
        # Get from environment
        env_value = os.getenv(key, default)
        
        if isinstance(env_value, str):
            # Check if value is encrypted
            if env_value.startswith("enc:"):
                encrypted_value = env_value[4:]  # Remove "enc:" prefix
                decrypted_value = self.decrypt_value(encrypted_value)
                self._config_cache[key] = decrypted_value
                return decrypted_value
            else:
                self._config_cache[key] = env_value
                return env_value
        
        return env_value
    
    def validate_configuration(self) -> bool:
        """Validate that all required secure configurations are present."""
        required_configs = [
            "DATABASE_PASSWORD",
            "JWT_SECRET_KEY",
            "API_SECRET_KEY"
        ]
        
        for config in required_configs:
            value = self.get_config_value(config)
            if not value:
                return False
            
            # Check if sensitive values are encrypted or strong enough
            if not self._is_secure_value(value):
                return False
        
        return True
    
    def _is_secure_value(self, value: str) -> bool:
        """Check if a value meets security requirements."""
        if len(value) < 12:  # Minimum length
            return False
        
        # Should have complexity (letters, numbers, symbols)
        has_lower = any(c.islower() for c in value)
        has_upper = any(c.isupper() for c in value)
        has_digit = any(c.isdigit() for c in value)
        has_symbol = any(not c.isalnum() for c in value)
        
        return sum([has_lower, has_upper, has_digit, has_symbol]) >= 3

@dataclass
class DatabaseConfig:
    host: str
    port: int
    database: str
    username: str
    password: str
    ssl_mode: str = "require"
    
    def __post_init__(self):
        # Validate that password is not empty
        if not self.password:
            raise SecurityError("Database password cannot be empty")

@dataclass
class JWTConfig:
    secret_key: str
    algorithm: str = "HS256"
    expiration_hours: int = 24
    
    def __post_init__(self):
        if len(self.secret_key) < 32:
            raise SecurityError("JWT secret key must be at least 32 characters")

class SecureConfigModule(Module):
    """Module that provides secure configuration."""
    
    def configure(self):
        config_manager = SecureConfigManager()
        
        # Validate configuration
        if not config_manager.validate_configuration():
            raise SecurityError("Configuration validation failed")
        
        # Database configuration
        db_config = DatabaseConfig(
            host=config_manager.get_config_value("DATABASE_HOST", "localhost"),
            port=int(config_manager.get_config_value("DATABASE_PORT", "5432")),
            database=config_manager.get_config_value("DATABASE_NAME", "app"),
            username=config_manager.get_config_value("DATABASE_USER", "app"),
            password=config_manager.get_config_value("DATABASE_PASSWORD"),
            ssl_mode=config_manager.get_config_value("DATABASE_SSL_MODE", "require")
        )
        
        # JWT configuration
        jwt_config = JWTConfig(
            secret_key=config_manager.get_config_value("JWT_SECRET_KEY"),
            algorithm=config_manager.get_config_value("JWT_ALGORITHM", "HS256"),
            expiration_hours=int(config_manager.get_config_value("JWT_EXPIRATION_HOURS", "24"))
        )
        
        # Bind configurations
        self.bind(SecureConfigManager, config_manager).singleton()
        self.bind(DatabaseConfig, db_config).singleton()
        self.bind(JWTConfig, jwt_config).singleton()
        
        # Input validation
        self.bind(InputValidator, InputValidator).singleton()
```

## 🛡️ Authentication and Authorization

### Secure Authentication Service

```python
import jwt
import bcrypt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

class AuthenticationService:
    """Handles user authentication securely."""
    
    @inject
    def __init__(
        self,
        jwt_config: JWTConfig,
        user_repository: IUserRepository,
        audit_logger: AuditLogger
    ):
        self.jwt_config = jwt_config
        self.user_repository = user_repository
        self.audit_logger = audit_logger
        self.failed_attempts: Dict[str, int] = {}
        self.lockout_threshold = 5
        self.lockout_duration = timedelta(minutes=15)
    
    async def authenticate_user(
        self,
        username: str,
        password: str,
        client_ip: str
    ) -> Optional[Dict[str, Any]]:
        """Authenticate user with rate limiting and audit logging."""
        
        # Check for account lockout
        if self._is_account_locked(username):
            self.audit_logger.log_security_event(
                "authentication_blocked_lockout",
                username,
                client_ip
            )
            raise SecurityError("Account temporarily locked due to multiple failed attempts")
        
        try:
            # Find user
            user = await self.user_repository.find_by_username(username)
            if not user:
                self._record_failed_attempt(username)
                self.audit_logger.log_security_event(
                    "authentication_failed_user_not_found",
                    username,
                    client_ip
                )
                return None
            
            # Verify password
            if not self._verify_password(password, user.password_hash):
                self._record_failed_attempt(username)
                self.audit_logger.log_security_event(
                    "authentication_failed_invalid_password",
                    username,
                    client_ip
                )
                return None
            
            # Check if account is active
            if not user.is_active:
                self.audit_logger.log_security_event(
                    "authentication_failed_inactive_account",
                    username,
                    client_ip
                )
                return None
            
            # Reset failed attempts on successful login
            self._reset_failed_attempts(username)
            
            # Generate JWT token
            token = self._generate_jwt_token(user)
            
            # Log successful authentication
            self.audit_logger.log_security_event(
                "authentication_successful",
                username,
                client_ip
            )
            
            return {
                "token": token,
                "user_id": user.id,
                "username": user.username,
                "expires_at": datetime.utcnow() + timedelta(hours=self.jwt_config.expiration_hours)
            }
            
        except Exception as e:
            self.audit_logger.log_error("authentication_error", str(e))
            raise
    
    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password using secure hashing."""
        try:
            return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
        except Exception:
            return False
    
    def _generate_jwt_token(self, user: Any) -> str:
        """Generate JWT token for authenticated user."""
        payload = {
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "roles": user.roles,
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(hours=self.jwt_config.expiration_hours)
        }
        
        return jwt.encode(
            payload,
            self.jwt_config.secret_key,
            algorithm=self.jwt_config.algorithm
        )
    
    def verify_jwt_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify JWT token and return payload."""
        try:
            payload = jwt.decode(
                token,
                self.jwt_config.secret_key,
                algorithms=[self.jwt_config.algorithm]
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise SecurityError("Token has expired")
        except jwt.InvalidTokenError:
            raise SecurityError("Invalid token")
    
    def _is_account_locked(self, username: str) -> bool:
        """Check if account is locked due to failed attempts."""
        if username not in self.failed_attempts:
            return False
        
        attempts, last_attempt = self.failed_attempts[username]
        if attempts >= self.lockout_threshold:
            if datetime.now() - last_attempt < self.lockout_duration:
                return True
            else:
                # Lockout period expired, reset attempts
                self._reset_failed_attempts(username)
        
        return False
    
    def _record_failed_attempt(self, username: str):
        """Record a failed authentication attempt."""
        if username not in self.failed_attempts:
            self.failed_attempts[username] = [1, datetime.now()]
        else:
            attempts, _ = self.failed_attempts[username]
            self.failed_attempts[username] = [attempts + 1, datetime.now()]
    
    def _reset_failed_attempts(self, username: str):
        """Reset failed attempts for a user."""
        self.failed_attempts.pop(username, None)

class AuthorizationService:
    """Handles user authorization and permissions."""
    
    @inject
    def __init__(self, auth_service: AuthenticationService):
        self.auth_service = auth_service
    
    def check_permission(self, token: str, required_permission: str) -> bool:
        """Check if user has required permission."""
        try:
            payload = self.auth_service.verify_jwt_token(token)
            user_roles = payload.get("roles", [])
            
            # Check if user has required permission
            return self._has_permission(user_roles, required_permission)
            
        except SecurityError:
            return False
    
    def require_permission(self, required_permission: str):
        """Decorator to require specific permission."""
        def decorator(func):
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                # Extract token from request context (implementation depends on framework)
                token = self._extract_token_from_context()
                
                if not self.check_permission(token, required_permission):
                    raise SecurityError(f"Permission denied: {required_permission} required")
                
                return await func(*args, **kwargs)
            return wrapper
        return decorator
    
    def _has_permission(self, user_roles: List[str], required_permission: str) -> bool:
        """Check if user roles include required permission."""
        # Define role permissions (in production, this would be in a database)
        role_permissions = {
            "admin": ["*"],  # Admin has all permissions
            "user": ["read_profile", "update_profile"],
            "moderator": ["read_profile", "update_profile", "moderate_content"],
            "editor": ["read_profile", "update_profile", "create_content", "edit_content"]
        }
        
        for role in user_roles:
            permissions = role_permissions.get(role, [])
            if "*" in permissions or required_permission in permissions:
                return True
        
        return False
    
    def _extract_token_from_context(self) -> Optional[str]:
        """Extract JWT token from request context."""
        # Implementation depends on web framework
        # This is a placeholder
        return None
```

## 🚨 Audit Logging and Monitoring

### Security Audit System

```python
import json
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

class SecurityEventType(Enum):
    AUTHENTICATION_SUCCESS = "authentication_success"
    AUTHENTICATION_FAILURE = "authentication_failure"
    AUTHORIZATION_FAILURE = "authorization_failure"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    DATA_ACCESS = "data_access"
    CONFIGURATION_CHANGE = "configuration_change"
    SECURITY_VIOLATION = "security_violation"

@dataclass
class SecurityEvent:
    event_id: str
    event_type: SecurityEventType
    timestamp: datetime
    user_id: Optional[str]
    username: Optional[str]
    client_ip: str
    user_agent: Optional[str]
    resource: Optional[str]
    action: str
    result: str
    details: Dict[str, Any]
    risk_score: int  # 1-10, where 10 is highest risk

class AuditLogger:
    """Comprehensive security audit logging."""
    
    @inject
    def __init__(self, log_storage: ILogStorage, alert_service: IAlertService):
        self.log_storage = log_storage
        self.alert_service = alert_service
        self.high_risk_threshold = 7
    
    def log_security_event(
        self,
        event_type: str,
        username: Optional[str] = None,
        client_ip: str = "unknown",
        user_agent: Optional[str] = None,
        resource: Optional[str] = None,
        action: str = "",
        result: str = "",
        details: Optional[Dict[str, Any]] = None,
        risk_score: int = 5
    ):
        """Log a security event."""
        event = SecurityEvent(
            event_id=str(uuid.uuid4()),
            event_type=SecurityEventType(event_type),
            timestamp=datetime.utcnow(),
            user_id=None,  # Would be extracted from context
            username=username,
            client_ip=client_ip,
            user_agent=user_agent,
            resource=resource,
            action=action,
            result=result,
            details=details or {},
            risk_score=risk_score
        )
        
        # Store the event
        self._store_event(event)
        
        # Check if high-risk event requires immediate alerting
        if risk_score >= self.high_risk_threshold:
            self._send_security_alert(event)
        
        # Check for suspicious patterns
        self._analyze_suspicious_patterns(event)
    
    def log_operation(self, operation: str, target: str, **kwargs):
        """Log a general operation for audit purposes."""
        self.log_security_event(
            event_type="data_access",
            action=operation,
            resource=target,
            details=kwargs,
            risk_score=3
        )
    
    def log_error(self, operation: str, error_message: str, **kwargs):
        """Log an error for security analysis."""
        self.log_security_event(
            event_type="security_violation",
            action=operation,
            result="error",
            details={"error": error_message, **kwargs},
            risk_score=6
        )
    
    def _store_event(self, event: SecurityEvent):
        """Store security event in persistent storage."""
        event_data = {
            "event_id": event.event_id,
            "event_type": event.event_type.value,
            "timestamp": event.timestamp.isoformat(),
            "user_id": event.user_id,
            "username": event.username,
            "client_ip": event.client_ip,
            "user_agent": event.user_agent,
            "resource": event.resource,
            "action": event.action,
            "result": event.result,
            "details": event.details,
            "risk_score": event.risk_score
        }
        
        self.log_storage.store_event(event_data)
    
    def _send_security_alert(self, event: SecurityEvent):
        """Send immediate alert for high-risk events."""
        alert_message = {
            "alert_type": "security_event",
            "severity": "high",
            "event_id": event.event_id,
            "event_type": event.event_type.value,
            "timestamp": event.timestamp.isoformat(),
            "username": event.username,
            "client_ip": event.client_ip,
            "risk_score": event.risk_score,
            "details": event.details
        }
        
        self.alert_service.send_alert(alert_message)
    
    def _analyze_suspicious_patterns(self, event: SecurityEvent):
        """Analyze event for suspicious patterns."""
        # Check for brute force attacks
        if event.event_type == SecurityEventType.AUTHENTICATION_FAILURE:
            recent_failures = self._get_recent_failures(event.client_ip, minutes=10)
            if len(recent_failures) >= 5:
                self._send_security_alert(SecurityEvent(
                    event_id=str(uuid.uuid4()),
                    event_type=SecurityEventType.SUSPICIOUS_ACTIVITY,
                    timestamp=datetime.utcnow(),
                    user_id=None,
                    username=event.username,
                    client_ip=event.client_ip,
                    user_agent=event.user_agent,
                    resource=None,
                    action="brute_force_detected",
                    result="blocked",
                    details={"failure_count": len(recent_failures)},
                    risk_score=9
                ))
        
        # Check for unusual access patterns
        if event.event_type == SecurityEventType.DATA_ACCESS:
            if self._is_unusual_access_pattern(event):
                event.risk_score = min(event.risk_score + 3, 10)
    
    def _get_recent_failures(self, client_ip: str, minutes: int) -> List[Dict]:
        """Get recent authentication failures from this IP."""
        # This would query the log storage
        return []
    
    def _is_unusual_access_pattern(self, event: SecurityEvent) -> bool:
        """Check if access pattern is unusual."""
        # Implement pattern analysis logic
        return False

class ILogStorage(ABC):
    @abstractmethod
    def store_event(self, event_data: Dict[str, Any]):
        pass

class IAlertService(ABC):
    @abstractmethod
    def send_alert(self, alert_data: Dict[str, Any]):
        pass

class DatabaseLogStorage(ILogStorage):
    @inject
    def __init__(self, database: Database):
        self.database = database
    
    def store_event(self, event_data: Dict[str, Any]):
        """Store security event in database."""
        # Insert into security_events table
        pass

class EmailAlertService(IAlertService):
    @inject
    def __init__(self, email_service: EmailService, config: AlertConfig):
        self.email_service = email_service
        self.config = config
    
    def send_alert(self, alert_data: Dict[str, Any]):
        """Send security alert via email."""
        subject = f"Security Alert: {alert_data['event_type']}"
        body = json.dumps(alert_data, indent=2)
        
        self.email_service.send_email(
            to=self.config.security_team_email,
            subject=subject,
            body=body
        )
```

## 🛠️ Security Testing

### Security Test Suite

```python
import pytest
from unittest.mock import Mock, patch
from injectq import InjectQ

class SecurityTestSuite:
    """Comprehensive security test suite."""
    
    def __init__(self, container: InjectQ):
        self.container = container
    
    def test_input_validation(self):
        """Test input validation against common attacks."""
        validator = self.container.get(InputValidator)
        
        # SQL injection tests
        sql_payloads = [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "admin'--",
            "1; DELETE FROM users WHERE 1=1; --"
        ]
        
        for payload in sql_payloads:
            assert not validator.validate_sql_injection(payload), f"SQL injection not detected: {payload}"
        
        # XSS tests
        xss_payloads = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "<svg onload=alert('xss')>"
        ]
        
        for payload in xss_payloads:
            assert not validator.validate_xss(payload), f"XSS not detected: {payload}"
    
    def test_authentication_security(self):
        """Test authentication security measures."""
        auth_service = self.container.get(AuthenticationService)
        
        # Test rate limiting
        for i in range(6):  # Exceed lockout threshold
            try:
                auth_service.authenticate_user("testuser", "wrongpassword", "127.0.0.1")
            except SecurityError:
                pass
        
        # Next attempt should be blocked
        with pytest.raises(SecurityError, match="Account temporarily locked"):
            auth_service.authenticate_user("testuser", "wrongpassword", "127.0.0.1")
    
    def test_configuration_security(self):
        """Test configuration security."""
        config_manager = self.container.get(SecureConfigManager)
        
        # Test that sensitive values are properly encrypted
        assert config_manager.validate_configuration()
        
        # Test encryption/decryption
        test_value = "sensitive_password_123"
        encrypted = config_manager.encrypt_value(test_value)
        decrypted = config_manager.decrypt_value(encrypted)
        
        assert test_value == decrypted
        assert encrypted != test_value
    
    def test_audit_logging(self):
        """Test audit logging functionality."""
        audit_logger = self.container.get(AuditLogger)
        
        with patch.object(audit_logger.log_storage, 'store_event') as mock_store:
            audit_logger.log_security_event(
                "authentication_failure",
                username="testuser",
                client_ip="127.0.0.1",
                risk_score=8
            )
            
            # Verify event was stored
            mock_store.assert_called_once()
            
            # Verify high-risk alert was sent
            with patch.object(audit_logger.alert_service, 'send_alert') as mock_alert:
                audit_logger.log_security_event(
                    "suspicious_activity",
                    risk_score=9
                )
                mock_alert.assert_called_once()

# Security test fixtures
@pytest.fixture
def secure_container():
    """Create container with security modules."""
    container = InjectQ()
    container.install(SecureConfigModule())
    container.install(SecurityModule())
    return container

class SecurityModule(Module):
    def configure(self):
        # Security services
        self.bind(InputValidator, InputValidator).singleton()
        self.bind(AuthenticationService, AuthenticationService).singleton()
        self.bind(AuthorizationService, AuthorizationService).singleton()
        self.bind(AuditLogger, AuditLogger).singleton()
        
        # Mock implementations for testing
        self.bind(ILogStorage, Mock()).singleton()
        self.bind(IAlertService, Mock()).singleton()
        self.bind(IUserRepository, Mock()).singleton()

# Usage
def test_security_suite(secure_container):
    """Run complete security test suite."""
    test_suite = SecurityTestSuite(secure_container)
    
    test_suite.test_input_validation()
    test_suite.test_authentication_security()
    test_suite.test_configuration_security()
    test_suite.test_audit_logging()
```

## 🔒 Security Checklist

### Pre-Production Security Review

- [ ] **Input Validation**
  - [ ] All user inputs are validated and sanitized
  - [ ] SQL injection protection is implemented
  - [ ] XSS protection is in place
  - [ ] File upload validation is secure

- [ ] **Authentication & Authorization**
  - [ ] Strong password policies are enforced
  - [ ] Account lockout mechanisms are implemented
  - [ ] JWT tokens use secure algorithms and keys
  - [ ] Session management is secure
  - [ ] Role-based access control is properly implemented

- [ ] **Configuration Security**
  - [ ] Sensitive configuration is encrypted
  - [ ] No credentials are hardcoded
  - [ ] Environment variables are used for secrets
  - [ ] Configuration validation is implemented

- [ ] **Data Protection**
  - [ ] Personal data is encrypted at rest
  - [ ] Data transmission uses TLS/SSL
  - [ ] Database connections are encrypted
  - [ ] Sensitive data is not logged

- [ ] **Audit & Monitoring**
  - [ ] Security events are logged
  - [ ] Failed authentication attempts are tracked
  - [ ] Suspicious activities trigger alerts
  - [ ] Audit logs are tamper-proof

- [ ] **Dependency Security**
  - [ ] Dependencies are validated for security
  - [ ] Dependency injection is secure
  - [ ] Third-party libraries are up to date
  - [ ] Vulnerable dependencies are avoided

- [ ] **Infrastructure Security**
  - [ ] Network security is properly configured
  - [ ] Database access is restricted
  - [ ] API endpoints are secured
  - [ ] Error messages don't leak sensitive information

Following these security best practices ensures your InjectQ applications are protected against common vulnerabilities and maintain high security standards in production environments.
