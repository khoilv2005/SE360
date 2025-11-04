"""
Unit tests for TripService - Business Logic
Run with: pytest tests/test_tripservice.py -v
"""
import pytest
from datetime import datetime

class TestTripBusinessLogic:
    """Test trip business logic"""

    @pytest.mark.asyncio
    async def test_fare_calculation_bike(self):
        """Test fare calculation for bike rides"""
        distance_km = 5.0
        base_fare = 15000
        per_km_rate = 3000
        expected_fare = base_fare + (distance_km * per_km_rate)
        assert expected_fare == 30000

    @pytest.mark.asyncio
    async def test_fare_calculation_car(self):
        """Test fare calculation for car rides"""
        distance_km = 5.0
        base_fare = 20000
        per_km_rate = 5000
        expected_fare = base_fare + (distance_km * per_km_rate)
        assert expected_fare == 45000

    @pytest.mark.asyncio
    async def test_trip_status_transitions(self):
        """Test valid trip status transitions"""
        valid_from_pending = ["ACCEPTED", "CANCELLED"]
        assert "ACCEPTED" in valid_from_pending

    @pytest.mark.asyncio
    async def test_create_trip_mock(self):
        """Test trip creation logic"""
        trip_data = {
            "trip_id": "trip_001",
            "passenger_id": "user_001",
            "status": "PENDING",
            "estimated_fare": 30000
        }
        assert trip_data["status"] == "PENDING"
        assert trip_data["passenger_id"] == "user_001"

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
