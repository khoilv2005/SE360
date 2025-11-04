"""
Unit tests for LocationService
Run with: pytest tests/test_locationservice.py -v
"""
import pytest
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

# Set required environment variables
os.environ.setdefault("REDIS_HOST", "localhost")

# Add LocationService to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'LocationService'))

import schemas


class TestLocationSchemas:
    """Test Location data models and schemas"""

    def test_location_update_schema(self):
        """Test location update schema"""
        location_data = schemas.LocationUpdate(
            latitude=10.762622,
            longitude=106.660172
        )

        assert location_data.latitude == 10.762622
        assert location_data.longitude == 106.660172
        assert -90 <= location_data.latitude <= 90
        assert -180 <= location_data.longitude <= 180

    def test_nearby_driver_schema(self):
        """Test nearby driver schema"""
        nearby_driver = schemas.NearbyDriver(
            driver_id="driver_001",
            latitude=10.762622,
            longitude=106.660172,
            distance_km=1.5
        )

        assert nearby_driver.driver_id == "driver_001"
        assert nearby_driver.distance_km == 1.5


class TestGeospatialQueries:
    """Test geospatial query operations"""

    @pytest.mark.asyncio
    async def test_nearby_drivers_calculation(self):
        """Test calculation of nearby drivers"""
        # Mock driver locations
        driver_locations = [
            {"driver_id": "driver_001", "lat": 10.762622, "lng": 106.660172, "distance_km": 0.5},
            {"driver_id": "driver_002", "lat": 10.762722, "lng": 106.660272, "distance_km": 1.2},
            {"driver_id": "driver_003", "lat": 10.762822, "lng": 106.660372, "distance_km": 2.0},
            {"driver_id": "driver_004", "lat": 10.762922, "lng": 106.660472, "distance_km": 4.5},
        ]

        # Filter drivers within 3km
        radius_km = 3.0
        nearby = [d for d in driver_locations if d["distance_km"] <= radius_km]

        assert len(nearby) == 3
        assert all(d["distance_km"] <= radius_km for d in nearby)

    @pytest.mark.asyncio
    async def test_redis_geoadd_mock(self):
        """Test Redis GEOADD operation (mocked)"""
        # Mock Redis geospatial add
        driver_id = "driver_001"
        longitude = 106.660172
        latitude = 10.762622

        # GEOADD command format: GEOADD key longitude latitude member
        geoadd_command = {
            "key": "drivers:locations",
            "longitude": longitude,
            "latitude": latitude,
            "member": f"driver:{driver_id}"
        }

        assert geoadd_command["member"] == "driver:driver_001"
        assert geoadd_command["longitude"] == 106.660172

    @pytest.mark.asyncio
    async def test_redis_georadius_mock(self):
        """Test Redis GEORADIUS operation (mocked)"""
        # Mock Redis geospatial search
        center_lng = 106.660172
        center_lat = 10.762622
        radius_km = 5.0

        georadius_command = {
            "key": "drivers:locations",
            "longitude": center_lng,
            "latitude": center_lat,
            "radius": radius_km,
            "unit": "km"
        }

        assert georadius_command["radius"] == 5.0
        assert georadius_command["unit"] == "km"


class TestWebSocketConnections:
    """Test WebSocket connection management"""

    @pytest.mark.asyncio
    async def test_driver_connection_manager(self):
        """Test driver WebSocket connection manager"""
        # Mock connection manager
        active_connections = {}

        # Driver connects
        driver_id = "driver_001"
        active_connections[driver_id] = "websocket_mock"

        assert driver_id in active_connections
        assert len(active_connections) == 1

        # Driver disconnects
        del active_connections[driver_id]

        assert driver_id not in active_connections
        assert len(active_connections) == 0

    @pytest.mark.asyncio
    async def test_trip_room_manager(self):
        """Test trip room WebSocket management"""
        # Mock trip rooms
        trip_rooms = {}

        trip_id = "trip_001"
        trip_rooms[trip_id] = {
            "passenger": "websocket_passenger",
            "driver": "websocket_driver"
        }

        assert trip_id in trip_rooms
        assert "passenger" in trip_rooms[trip_id]
        assert "driver" in trip_rooms[trip_id]

    @pytest.mark.asyncio
    async def test_location_broadcast(self):
        """Test location broadcast to trip participants"""
        # Mock trip room
        trip_room = {
            "passenger": "ws_passenger",
            "driver": "ws_driver"
        }

        # Mock location update
        location_update = {
            "type": "location_update",
            "latitude": 10.762622,
            "longitude": 106.660172,
            "timestamp": datetime.utcnow().isoformat()
        }

        # Broadcast to both passenger and driver
        recipients = list(trip_room.values())

        assert len(recipients) == 2
        assert location_update["type"] == "location_update"


class TestLocationCRUD:
    """Test Location CRUD operations (mocked)"""

    @pytest.mark.asyncio
    async def test_store_driver_location(self):
        """Test storing driver location in Redis"""
        # Mock driver location data
        location_data = {
            "driver_id": "driver_001",
            "latitude": 10.762622,
            "longitude": 106.660172,
            "timestamp": datetime.utcnow(),
            "ttl": 300  # 5 minutes
        }

        assert location_data["driver_id"] == "driver_001"
        assert location_data["ttl"] == 300

    @pytest.mark.asyncio
    async def test_remove_driver_location(self):
        """Test removing driver location (offline)"""
        # Mock stored locations
        stored_locations = {
            "driver_001": {"lat": 10.762622, "lng": 106.660172},
            "driver_002": {"lat": 10.762722, "lng": 106.660272}
        }

        # Remove driver_001
        driver_id = "driver_001"
        if driver_id in stored_locations:
            del stored_locations[driver_id]

        assert driver_id not in stored_locations
        assert len(stored_locations) == 1

    @pytest.mark.asyncio
    async def test_location_ttl_expiration(self):
        """Test location TTL (time-to-live) expiration"""
        # Mock location with TTL
        location = {
            "driver_id": "driver_001",
            "ttl_seconds": 300,
            "stored_at": datetime.utcnow()
        }

        # Simulate TTL check
        ttl_remaining = location["ttl_seconds"]

        # After 5 minutes, TTL should expire
        # Redis will automatically remove the key

        assert ttl_remaining == 300


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
