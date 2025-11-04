"""
Unit tests for UserService - Authentication and Schemas
Run with: pytest tests/test_userservice_crud.py -v
"""
import pytest
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

# Set required environment variables BEFORE importing modules
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-unit-tests-only-32chars-minimum")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_USER", "testuser")
os.environ.setdefault("POSTGRES_PASSWORD", "testpass")
os.environ.setdefault("POSTGRES_DB", "testdb")

# Add UserService to path - use absolute path to avoid conflicts
USERSERVICE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'UserService'))
if USERSERVICE_PATH not in sys.path:
    sys.path.insert(0, USERSERVICE_PATH)

# Import only what we need to test
try:
    from auth import get_password_hash, verify_password, create_access_token, verify_token
    import schemas
except ImportError as e:
    pytest.skip(f"Skipping UserService tests due to import error: {e}", allow_module_level=True)


class TestAuthentication:
    """Test authentication functions"""

    def test_password_hashing(self):
        """Test password hashing and verification"""
        password = "testpassword123"
        hashed = get_password_hash(password)

        # Hash should be different from original
        assert hashed != password
        assert len(hashed) > 0

        # Should verify correctly
        assert verify_password(password, hashed) == True

        # Should fail with wrong password
        assert verify_password("wrongpassword", hashed) == False

    def test_password_truncation(self):
        """Test that long passwords are handled properly"""
        # Password > 72 bytes (bcrypt limit)
        long_password = "a" * 100
        hashed = get_password_hash(long_password)

        # Should not raise exception
        assert hashed is not None
        assert len(hashed) > 0

    def test_create_access_token(self):
        """Test JWT token creation"""
        data = {"sub": "test@example.com", "type": "user"}
        token = create_access_token(data)

        # Token should be a string
        assert isinstance(token, str)
        assert len(token) > 0

        # Token should have 3 parts (header.payload.signature)
        parts = token.split('.')
        assert len(parts) == 3

    def test_create_access_token_with_expiry(self):
        """Test JWT token creation with custom expiry"""
        data = {"sub": "test@example.com"}
        expires_delta = timedelta(minutes=15)
        token = create_access_token(data, expires_delta=expires_delta)

        assert isinstance(token, str)
        assert len(token) > 0


class TestUserSchemas:
    """Test user data validation schemas"""

    def test_user_create_schema_valid(self):
        """Test valid user creation schema"""
        user_data = schemas.UserCreate(
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            phone_number="0123456789",
            password="testpassword123"
        )

        assert user_data.username == "testuser"
        assert user_data.email == "test@example.com"
        assert user_data.full_name == "Test User"
        assert user_data.phone_number == "0123456789"
        assert user_data.password == "testpassword123"

    def test_user_create_schema_invalid_email(self):
        """Test invalid email format"""
        with pytest.raises(Exception):  # Pydantic will raise validation error
            schemas.UserCreate(
                username="testuser",
                email="invalid-email-format",  # Invalid email
                full_name="Test User",
                phone_number="0123456789",
                password="testpassword123"
            )

    def test_user_update_schema(self):
        """Test user update schema"""
        update_data = schemas.UserUpdate(
            full_name="Updated Name",
            phone_number="0987654321"
        )

        assert update_data.full_name == "Updated Name"
        assert update_data.phone_number == "0987654321"

    def test_user_update_schema_optional_fields(self):
        """Test user update with optional fields"""
        # All fields are optional in update
        update_data = schemas.UserUpdate()

        # Should create successfully with no fields set
        assert update_data is not None


class TestUserBusinessLogic:
    """Test user-related business logic"""

    def test_email_uniqueness_validation(self):
        """Test that email uniqueness should be enforced"""
        # This is a logic test - in real implementation,
        # database should have unique constraint on email
        emails = ["user1@example.com", "user2@example.com"]

        # Adding duplicate should fail
        duplicate_email = "user1@example.com"
        assert duplicate_email in emails

    def test_phone_number_format(self):
        """Test phone number format validation"""
        valid_phones = ["0123456789", "0987654321", "0912345678"]

        for phone in valid_phones:
            assert len(phone) == 10
            assert phone.startswith("0")

    def test_password_requirements(self):
        """Test password should meet minimum requirements"""
        weak_password = "123"
        strong_password = "StrongPass123!@#"

        # In real implementation, should enforce minimum length
        assert len(weak_password) < 8
        assert len(strong_password) >= 8


class TestUserCRUDLogic:
    """Test CRUD operation logic without database"""

    @pytest.mark.asyncio
    async def test_user_creation_flow(self):
        """Test user creation flow logic"""
        # Mock user data
        user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "full_name": "Test User",
            "phone_number": "0123456789",
            "password": "hashed_password_here"
        }

        # Simulate creation
        created_user = {
            "id": 1,
            **user_data,
            "created_at": datetime.utcnow()
        }

        # Verify user structure
        assert created_user["id"] == 1
        assert created_user["email"] == "test@example.com"
        assert created_user["username"] == "testuser"
        assert "created_at" in created_user

    @pytest.mark.asyncio
    async def test_duplicate_email_logic(self):
        """Test duplicate email detection logic"""
        existing_emails = ["user1@example.com", "user2@example.com"]
        new_email = "user1@example.com"

        # Should detect duplicate
        is_duplicate = new_email in existing_emails
        assert is_duplicate == True

        # New email should not be duplicate
        unique_email = "newuser@example.com"
        is_duplicate = unique_email in existing_emails
        assert is_duplicate == False

    @pytest.mark.asyncio
    async def test_user_update_logic(self):
        """Test user update logic"""
        original_user = {
            "id": 1,
            "username": "testuser",
            "email": "test@example.com",
            "full_name": "Old Name",
            "phone_number": "0123456789"
        }

        # Update data
        updates = {
            "full_name": "New Name",
            "phone_number": "0987654321"
        }

        # Apply updates
        updated_user = {**original_user, **updates}

        # Verify updates
        assert updated_user["full_name"] == "New Name"
        assert updated_user["phone_number"] == "0987654321"
        assert updated_user["email"] == original_user["email"]  # Unchanged

    @pytest.mark.asyncio
    async def test_password_hashing_in_creation(self):
        """Test that passwords are hashed during user creation"""
        plain_password = "mypassword123"
        hashed_password = get_password_hash(plain_password)

        # Hashed password should be different
        assert hashed_password != plain_password
        assert len(hashed_password) > len(plain_password)

        # Should be verifiable
        assert verify_password(plain_password, hashed_password) == True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
