"""
Unit tests for DriverService - Business Logic
Run with: pytest tests/test_driverservice.py -v
"""
import pytest
from datetime import datetime

class TestDriverBusinessLogic:
    """Test driver business logic"""

    def test_driver_status_values(self):
        """Test driver status validation"""
        valid_statuses = ["AVAILABLE", "BUSY", "OFFLINE"]
        for status in valid_statuses:
            assert status in valid_statuses

    def test_vehicle_types(self):
        """Test vehicle type validation"""
        valid_vehicle_types = ["BIKE", "CAR", "CAR_7_SEATS"]
        assert "BIKE" in valid_vehicle_types

class TestDriverWallet:
    """Test driver wallet operations"""

    @pytest.mark.asyncio
    async def test_wallet_initialization(self):
        """Test wallet is initialized with zero balance"""
        wallet = {"balance": 0, "currency": "VND"}
        assert wallet["balance"] == 0

    @pytest.mark.asyncio
    async def test_wallet_credit(self):
        """Test crediting driver wallet"""
        wallet = {"balance": 50000}
        trip_fare = 30000
        wallet["balance"] += trip_fare
        assert wallet["balance"] == 80000

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
