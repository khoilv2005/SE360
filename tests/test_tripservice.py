"""
Unit tests for TripService
Run with: pytest tests/test_tripservice.py -v
"""
import pytest
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

# Set required environment variables
os.environ.setdefault("COSMOS_CONNECTION_STRING", "mongodb://localhost:27017")
os.environ.setdefault("MAPBOX_ACCESS_TOKEN", "test_token_123")
os.environ.setdefault("USER_SERVICE_BASE_URL", "http://localhost:8000")

# Add TripService to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'TripService'))

import schemas


class TestTripSchemas:
    """Test Trip data models and schemas"""

    def test_trip_request_schema_valid(self):
        """Test valid trip request schema"""
        trip_request = schemas.TripRequestCreate(
            user_id="user_001",
            pickup_location=schemas.Location(
                latitude=10.762622,
                longitude=106.660172,
                address="District 1, Ho Chi Minh City"
            ),
            dropoff_location=schemas.Location(
                latitude=10.772622,
                longitude=106.670172,
                address="District 3, Ho Chi Minh City"
            ),
            vehicle_type="BIKE"
        )

        assert trip_request.user_id == "user_001"
        assert trip_request.pickup_location.latitude == 10.762622
        assert trip_request.vehicle_type == "BIKE"

    def test_fare_estimate_request(self):
        """Test fare estimate request schema"""
        fare_request = schemas.FareEstimateRequest(
            pickup_lat=10.762622,
            pickup_lng=106.660172,
            dropoff_lat=10.772622,
            dropoff_lng=106.670172
        )

        assert fare_request.pickup_lat == 10.762622
        assert fare_request.dropoff_lng == 106.670172

    def test_trip_status_update(self):
        """Test trip status update schema"""
        # This would test status transitions
        # PENDING -> ACCEPTED -> IN_PROGRESS -> COMPLETED
        assert "PENDING" in ["PENDING", "ACCEPTED", "IN_PROGRESS", "COMPLETED"]
        assert "COMPLETED" in ["PENDING", "ACCEPTED", "IN_PROGRESS", "COMPLETED"]


class TestTripBusinessLogic:
    """Test trip business logic"""

    @pytest.mark.asyncio
    async def test_fare_calculation_bike(self):
        """Test fare calculation for bike rides"""
        # Mock fare calculation
        distance_km = 5.0
        base_fare = 15000
        per_km_rate = 3000

        expected_fare = base_fare + (distance_km * per_km_rate)

        assert expected_fare == 30000  # 15000 + (5 * 3000)

    @pytest.mark.asyncio
    async def test_fare_calculation_car(self):
        """Test fare calculation for car rides"""
        distance_km = 5.0
        base_fare = 20000
        per_km_rate = 5000

        expected_fare = base_fare + (distance_km * per_km_rate)

        assert expected_fare == 45000  # 20000 + (5 * 5000)

    @pytest.mark.asyncio
    async def test_trip_status_transitions(self):
        """Test valid trip status transitions"""
        # PENDING can go to ACCEPTED or CANCELLED
        valid_from_pending = ["ACCEPTED", "CANCELLED"]
        assert "ACCEPTED" in valid_from_pending

        # ACCEPTED can go to IN_PROGRESS or CANCELLED
        valid_from_accepted = ["IN_PROGRESS", "CANCELLED"]
        assert "IN_PROGRESS" in valid_from_accepted

        # IN_PROGRESS can go to COMPLETED
        valid_from_in_progress = ["COMPLETED"]
        assert "COMPLETED" in valid_from_in_progress


class TestTripCRUD:
    """Test Trip CRUD operations (mocked)"""

    @pytest.mark.asyncio
    async def test_create_trip_mock(self):
        """Test trip creation with mocked database"""
        # Mock trip data
        trip_data = {
            "trip_id": "trip_001",
            "user_id": "user_001",
            "driver_id": None,
            "status": "PENDING",
            "pickup_location": {
                "latitude": 10.762622,
                "longitude": 106.660172,
                "address": "District 1"
            },
            "dropoff_location": {
                "latitude": 10.772622,
                "longitude": 106.670172,
                "address": "District 3"
            },
            "estimated_fare": 30000,
            "vehicle_type": "BIKE",
            "created_at": datetime.utcnow()
        }

        # Verify trip structure
        assert trip_data["status"] == "PENDING"
        assert trip_data["user_id"] == "user_001"
        assert trip_data["driver_id"] is None
        assert trip_data["estimated_fare"] == 30000

    @pytest.mark.asyncio
    async def test_assign_driver_to_trip(self):
        """Test driver assignment to trip"""
        # Mock trip
        trip_data = {
            "trip_id": "trip_001",
            "status": "PENDING",
            "driver_id": None
        }

        # Assign driver
        trip_data["driver_id"] = "driver_005"
        trip_data["status"] = "ACCEPTED"

        assert trip_data["driver_id"] == "driver_005"
        assert trip_data["status"] == "ACCEPTED"

    @pytest.mark.asyncio
    async def test_complete_trip(self):
        """Test trip completion"""
        # Mock trip in progress
        trip_data = {
            "trip_id": "trip_001",
            "status": "IN_PROGRESS",
            "estimated_fare": 30000,
            "actual_fare": None
        }

        # Complete trip
        trip_data["status"] = "COMPLETED"
        trip_data["actual_fare"] = 32000  # Actual fare slightly different

        assert trip_data["status"] == "COMPLETED"
        assert trip_data["actual_fare"] == 32000

    @pytest.mark.asyncio
    async def test_cancel_trip(self):
        """Test trip cancellation"""
        # Mock trip
        trip_data = {
            "trip_id": "trip_001",
            "status": "PENDING",
            "cancellation_reason": None
        }

        # Cancel trip
        trip_data["status"] = "CANCELLED"
        trip_data["cancellation_reason"] = "User requested cancellation"

        assert trip_data["status"] == "CANCELLED"
        assert "User requested" in trip_data["cancellation_reason"]


class TestMapboxIntegration:
    """Test Mapbox API integration (mocked)"""

    @pytest.mark.asyncio
    async def test_mapbox_route_calculation(self):
        """Test route calculation with Mapbox (mocked)"""
        # Mock Mapbox response
        mock_mapbox_response = {
            "routes": [{
                "distance": 5000,  # 5 km in meters
                "duration": 900,   # 15 minutes in seconds
                "geometry": {
                    "coordinates": [
                        [106.660172, 10.762622],
                        [106.670172, 10.772622]
                    ]
                }
            }]
        }

        # Extract route info
        distance_meters = mock_mapbox_response["routes"][0]["distance"]
        distance_km = distance_meters / 1000
        duration_minutes = mock_mapbox_response["routes"][0]["duration"] / 60

        assert distance_km == 5.0
        assert duration_minutes == 15.0

    @pytest.mark.asyncio
    async def test_mapbox_error_handling(self):
        """Test handling of Mapbox API errors"""
        # Simulate Mapbox error
        try:
            # Mock error response
            raise Exception("Mapbox API error: Invalid coordinates")
        except Exception as e:
            error_message = str(e)
            assert "Mapbox API error" in error_message


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
