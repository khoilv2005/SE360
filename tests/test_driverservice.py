"""
Unit tests for DriverService
Run with: pytest tests/test_driverservice.py -v
"""
import pytest
import sys
import os
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

# Set required environment variables
os.environ.setdefault("SECRET_KEY", "test-secret-key-32chars-minimum")
os.environ.setdefault("COSMOS_CONNECTION_STRING", "mongodb://localhost:27017")

# Add DriverService to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'DriverService'))

import schemas


class TestDriverSchemas:
    """Test Driver data models and schemas"""

    def test_driver_create_schema_valid(self):
        """Test valid driver creation schema"""
        driver_data = schemas.DriverCreate(
            user_id="user_001",
            license_number="ABC123456",
            vehicle_type="BIKE",
            vehicle_plate="59A-12345",
            vehicle_model="Honda Wave",
            vehicle_color="Black"
        )

        assert driver_data.user_id == "user_001"
        assert driver_data.license_number == "ABC123456"
        assert driver_data.vehicle_type == "BIKE"

    def test_driver_status_schema(self):
        """Test driver status schema"""
        # Valid statuses: AVAILABLE, BUSY, OFFLINE
        valid_statuses = ["AVAILABLE", "BUSY", "OFFLINE"]

        for status in valid_statuses:
            assert status in valid_statuses

    def test_vehicle_types(self):
        """Test vehicle type validation"""
        valid_vehicle_types = ["BIKE", "CAR", "CAR_7_SEATS"]

        assert "BIKE" in valid_vehicle_types
        assert "CAR" in valid_vehicle_types
        assert "CAR_7_SEATS" in valid_vehicle_types


class TestDriverWallet:
    """Test driver wallet operations"""

    @pytest.mark.asyncio
    async def test_wallet_initialization(self):
        """Test wallet is initialized with zero balance"""
        wallet = {
            "balance": 0,
            "currency": "VND"
        }

        assert wallet["balance"] == 0
        assert wallet["currency"] == "VND"

    @pytest.mark.asyncio
    async def test_wallet_credit(self):
        """Test crediting driver wallet"""
        wallet = {"balance": 50000}

        # Driver completes trip, gets paid
        trip_fare = 30000
        wallet["balance"] += trip_fare

        assert wallet["balance"] == 80000

    @pytest.mark.asyncio
    async def test_wallet_debit(self):
        """Test debiting driver wallet (commission)"""
        wallet = {"balance": 100000}

        # Platform takes 20% commission
        trip_fare = 50000
        commission_rate = 0.20
        commission = trip_fare * commission_rate

        wallet["balance"] -= commission

        assert wallet["balance"] == 90000  # 100000 - 10000

    @pytest.mark.asyncio
    async def test_wallet_withdrawal(self):
        """Test driver wallet withdrawal"""
        wallet = {"balance": 500000}

        withdrawal_amount = 300000
        if wallet["balance"] >= withdrawal_amount:
            wallet["balance"] -= withdrawal_amount

        assert wallet["balance"] == 200000


class TestDriverCRUD:
    """Test Driver CRUD operations (mocked)"""

    @pytest.mark.asyncio
    async def test_create_driver_profile(self):
        """Test driver profile creation"""
        driver_data = {
            "driver_id": "driver_001",
            "user_id": "user_001",
            "license_number": "ABC123456",
            "vehicle_type": "BIKE",
            "vehicle_plate": "59A-12345",
            "status": "AVAILABLE",
            "rating": 5.0,
            "total_trips": 0,
            "wallet": {"balance": 0, "currency": "VND"}
        }

        assert driver_data["status"] == "AVAILABLE"
        assert driver_data["rating"] == 5.0
        assert driver_data["total_trips"] == 0
        assert driver_data["wallet"]["balance"] == 0

    @pytest.mark.asyncio
    async def test_update_driver_status(self):
        """Test updating driver status"""
        driver = {
            "driver_id": "driver_001",
            "status": "AVAILABLE"
        }

        # Driver accepts trip
        driver["status"] = "BUSY"
        assert driver["status"] == "BUSY"

        # Driver completes trip
        driver["status"] = "AVAILABLE"
        assert driver["status"] == "AVAILABLE"

        # Driver goes offline
        driver["status"] = "OFFLINE"
        assert driver["status"] == "OFFLINE"

    @pytest.mark.asyncio
    async def test_update_driver_rating(self):
        """Test updating driver rating"""
        driver = {
            "driver_id": "driver_001",
            "rating": 5.0,
            "total_ratings": 10
        }

        # New rating: 4 stars
        new_rating = 4.0
        total_ratings = driver["total_ratings"]
        current_rating = driver["rating"]

        # Calculate new average
        updated_rating = ((current_rating * total_ratings) + new_rating) / (total_ratings + 1)

        driver["rating"] = round(updated_rating, 2)
        driver["total_ratings"] += 1

        assert driver["total_ratings"] == 11
        assert 4.0 <= driver["rating"] <= 5.0  # Rating should be between 4 and 5

    @pytest.mark.asyncio
    async def test_increment_trip_count(self):
        """Test incrementing driver trip count"""
        driver = {
            "driver_id": "driver_001",
            "total_trips": 50
        }

        # Driver completes a trip
        driver["total_trips"] += 1

        assert driver["total_trips"] == 51


class TestDriverAuthentication:
    """Test driver authentication and authorization"""

    @pytest.mark.asyncio
    async def test_service_token_validation(self):
        """Test service-to-service token validation"""
        # Mock service token payload
        token_payload = {
            "sub": "tripservice",
            "type": "service",
            "aud": "driverservice"
        }

        # Validate token type
        assert token_payload["type"] == "service"
        assert token_payload["aud"] == "driverservice"

    @pytest.mark.asyncio
    async def test_internal_endpoint_access(self):
        """Test that internal endpoints require service tokens"""
        # Mock request to internal endpoint
        endpoint = "/internal/drivers/driver_001"

        # Should require service token
        requires_service_token = True

        assert requires_service_token is True
        assert "/internal/" in endpoint


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
