from datetime import datetime

import pytest


# ==========================================
# VALID FLOW TESTS
# ==========================================


# Test: Valid start and end sequence for a component
@pytest.mark.asyncio
async def test_valid_start_end_sequence(async_client):
    """Test that a valid start followed by end event is accepted."""
    # First, create a contract
    contract_payload = {
        "contract_number": "TEST001",
        "components": ["energy_supply", "battery_optimization"],
        "created_at": "2024-01-01T00:00:00",
    }
    await async_client.post("/contract/", json=contract_payload)

    # Start event
    start_event = {
        "type": "supply_energy_start",
        "contract_number": "TEST001",
        "date": "2024-02-01",
        "created_at": "2024-02-01T10:00:00",
    }
    response = await async_client.post("/event", json=start_event)
    assert response.status_code == 200
    assert response.json()["status"] == "accepted"

    # End event
    end_event = {
        "type": "supply_energy_end",
        "contract_number": "TEST001",
        "date": "2024-03-01",
        "created_at": "2024-03-01T10:00:00",
    }
    response = await async_client.post("/event", json=end_event)
    assert response.status_code == 200
    assert response.json()["status"] == "accepted"


# Test: Overwriting start date before component termination
@pytest.mark.asyncio
async def test_overwrite_start_date_before_termination(async_client):
    """Test that a start date can be overwritten if component is not terminated."""
    # Create contract
    contract_payload = {
        "contract_number": "TEST002",
        "components": ["battery_optimization"],
        "created_at": "2024-01-01T00:00:00",
    }
    await async_client.post("/contract/", json=contract_payload)

    # First start event
    start_event_1 = {
        "type": "battery_optimization_start",
        "contract_number": "TEST002",
        "date": "2024-02-01",
        "created_at": "2024-02-01T10:00:00",
    }
    response = await async_client.post("/event", json=start_event_1)
    assert response.status_code == 200
    assert response.json()["status"] == "accepted"

    # Second start event (should overwrite)
    start_event_2 = {
        "type": "battery_optimization_start",
        "contract_number": "TEST002",
        "date": "2024-02-15",
        "created_at": "2024-02-15T10:00:00",
    }
    response = await async_client.post("/event", json=start_event_2)
    assert response.status_code == 200
    assert response.json()["status"] == "accepted"

    # Verify timeline shows the overwritten start date
    timeline_response = await async_client.get("/TEST002/contract_timeline")
    assert timeline_response.status_code == 200
    data = timeline_response.json()
    assert data["components"]["battery_optimization"]["start"] == "2024-02-15"
    assert data["components"]["battery_optimization"]["end"] is None


# Test: Overwriting end date with a valid new end date
@pytest.mark.asyncio
async def test_overwrite_end_date(async_client):
    """Test that an end date can be overwritten with a valid new end date."""
    # Create contract
    contract_payload = {
        "contract_number": "TEST003",
        "components": ["heatpump_optimization"],
        "created_at": "2024-01-01T00:00:00",
    }
    await async_client.post("/contract/", json=contract_payload)

    # Start event
    start_event = {
        "type": "heatpump_optimization_start",
        "contract_number": "TEST003",
        "date": "2024-02-01",
        "created_at": "2024-02-01T10:00:00",
    }
    await async_client.post("/event", json=start_event)

    # First end event
    end_event_1 = {
        "type": "heatpump_optimization_end",
        "contract_number": "TEST003",
        "date": "2024-03-01",
        "created_at": "2024-03-01T10:00:00",
    }
    response = await async_client.post("/event", json=end_event_1)
    assert response.status_code == 200
    assert response.json()["status"] == "accepted"

    # Second end event (should overwrite)
    end_event_2 = {
        "type": "heatpump_optimization_end",
        "contract_number": "TEST003",
        "date": "2024-03-15",
        "created_at": "2024-03-15T10:00:00",
    }
    response = await async_client.post("/event", json=end_event_2)
    assert response.status_code == 200
    assert response.json()["status"] == "accepted"

    # Verify timeline shows the overwritten end date
    timeline_response = await async_client.get("/TEST003/contract_timeline")
    assert timeline_response.status_code == 200
    data = timeline_response.json()
    assert data["components"]["heatpump_optimization"]["start"] == "2024-02-01"
    assert data["components"]["heatpump_optimization"]["end"] == "2024-03-15"


# Test: Multiple components with independent timelines
@pytest.mark.asyncio
async def test_multiple_components_independent_timelines(async_client):
    """Test that multiple components can have independent timelines."""
    # Create contract with all components
    contract_payload = {
        "contract_number": "TEST004",
        "components": ["energy_supply", "battery_optimization", "heatpump_optimization"],
        "created_at": "2024-01-01T00:00:00",
    }
    await async_client.post("/contract/", json=contract_payload)

    # Events for energy_supply
    await async_client.post("/event", json={
        "type": "supply_energy_start",
        "contract_number": "TEST004",
        "date": "2024-02-01",
        "created_at": "2024-02-01T10:00:00",
    })
    await async_client.post("/event", json={
        "type": "supply_energy_end",
        "contract_number": "TEST004",
        "date": "2024-03-01",
        "created_at": "2024-03-01T10:00:00",
    })

    # Events for battery_optimization (only start)
    await async_client.post("/event", json={
        "type": "battery_optimization_start",
        "contract_number": "TEST004",
        "date": "2024-04-01",
        "created_at": "2024-04-01T10:00:00",
    })

    # Verify timeline
    timeline_response = await async_client.get("/TEST004/contract_timeline")
    assert timeline_response.status_code == 200
    data = timeline_response.json()

    assert data["components"]["energy_supply"]["start"] == "2024-02-01"
    assert data["components"]["energy_supply"]["end"] == "2024-03-01"
    assert data["components"]["battery_optimization"]["start"] == "2024-04-01"
    assert data["components"]["battery_optimization"]["end"] is None
    assert data["components"]["heatpump_optimization"]["start"] is None
    assert data["components"]["heatpump_optimization"]["end"] is None


# ==========================================
# INVALID FLOW TESTS
# ==========================================


# Test: End event before start event (by date)
@pytest.mark.asyncio
async def test_end_before_start_rejected(async_client):
    """Test that an end event with a date before the start date is rejected."""
    # Create contract
    contract_payload = {
        "contract_number": "TEST005",
        "components": ["energy_supply"],
        "created_at": "2024-01-01T00:00:00",
    }
    await async_client.post("/contract/", json=contract_payload)

    # Start event
    start_event = {
        "type": "supply_energy_start",
        "contract_number": "TEST005",
        "date": "2024-03-01",
        "created_at": "2024-03-01T10:00:00",
    }
    await async_client.post("/event", json=start_event)

    # End event with date before start (should be rejected)
    end_event = {
        "type": "supply_energy_end",
        "contract_number": "TEST005",
        "date": "2024-02-01",
        "created_at": "2024-03-02T10:00:00",
    }
    response = await async_client.post("/event", json=end_event)
    assert response.status_code == 200
    assert response.json()["status"] == "rejected"
    assert "before start" in response.json()["message"].lower()


# Test: Start event after existing end event
@pytest.mark.asyncio
async def test_start_after_end_rejected(async_client):
    """Test that a start event after an existing end date is rejected."""
    # Create contract
    contract_payload = {
        "contract_number": "TEST006",
        "components": ["battery_optimization"],
        "created_at": "2024-01-01T00:00:00",
    }
    await async_client.post("/contract/", json=contract_payload)

    # Start event
    start_event = {
        "type": "battery_optimization_start",
        "contract_number": "TEST006",
        "date": "2024-02-01",
        "created_at": "2024-02-01T10:00:00",
    }
    await async_client.post("/event", json=start_event)

    # End event
    end_event = {
        "type": "battery_optimization_end",
        "contract_number": "TEST006",
        "date": "2024-03-01",
        "created_at": "2024-03-01T10:00:00",
    }
    await async_client.post("/event", json=end_event)

    # New start event after end (should be rejected)
    # Note: This is caught by the "cannot restart after termination" rule
    new_start_event = {
        "type": "battery_optimization_start",
        "contract_number": "TEST006",
        "date": "2024-04-01",
        "created_at": "2024-04-01T10:00:00",
    }
    response = await async_client.post("/event", json=new_start_event)
    assert response.status_code == 200
    assert response.json()["status"] == "rejected"
    # This is caught by the termination rule, which is more specific
    assert ("after end" in response.json()["message"].lower() or
            "restarted" in response.json()["message"].lower())


# Test: End event without start event
@pytest.mark.asyncio
async def test_end_without_start_rejected(async_client):
    """Test that an end event without a prior start event is rejected."""
    # Create contract
    contract_payload = {
        "contract_number": "TEST007",
        "components": ["heatpump_optimization"],
        "created_at": "2024-01-01T00:00:00",
    }
    await async_client.post("/contract/", json=contract_payload)

    # End event without start (should be rejected)
    end_event = {
        "type": "heatpump_optimization_end",
        "contract_number": "TEST007",
        "date": "2024-03-01",
        "created_at": "2024-03-01T10:00:00",
    }
    response = await async_client.post("/event", json=end_event)
    assert response.status_code == 200
    assert response.json()["status"] == "rejected"
    assert "requires a start" in response.json()["message"].lower()


# Test: Restarting component after termination
@pytest.mark.asyncio
async def test_restart_after_termination_rejected(async_client):
    """Test that a component cannot be restarted once it has been terminated."""
    # Create contract
    contract_payload = {
        "contract_number": "TEST008",
        "components": ["energy_supply"],
        "created_at": "2024-01-01T00:00:00",
    }
    await async_client.post("/contract/", json=contract_payload)

    # Start event
    start_event = {
        "type": "supply_energy_start",
        "contract_number": "TEST008",
        "date": "2024-02-01",
        "created_at": "2024-02-01T10:00:00",
    }
    await async_client.post("/event", json=start_event)

    # End event (component is now terminated)
    end_event = {
        "type": "supply_energy_end",
        "contract_number": "TEST008",
        "date": "2024-03-01",
        "created_at": "2024-03-01T10:00:00",
    }
    await async_client.post("/event", json=end_event)

    # Try to restart (should be rejected)
    restart_event = {
        "type": "supply_energy_start",
        "contract_number": "TEST008",
        "date": "2024-02-15",
        "created_at": "2024-04-01T10:00:00",
    }
    response = await async_client.post("/event", json=restart_event)
    assert response.status_code == 200
    assert response.json()["status"] == "rejected"
    assert "cannot be restarted" in response.json()["message"].lower()


# Test: Event for non-existing contract
@pytest.mark.asyncio
async def test_event_for_nonexistent_contract_rejected(async_client):
    """Test that an event for a non-existing contract is rejected."""
    event = {
        "type": "supply_energy_start",
        "contract_number": "NONEXISTENT999",
        "date": "2024-02-01",
        "created_at": "2024-02-01T10:00:00",
    }
    response = await async_client.post("/event", json=event)
    assert response.status_code == 200
    assert response.json()["status"] == "rejected"
    assert "not found" in response.json()["message"].lower()


# Test: Invalid event type
@pytest.mark.asyncio
async def test_invalid_event_type_rejected(async_client):
    """Test that an event with an invalid type is rejected."""
    # Create contract
    contract_payload = {
        "contract_number": "TEST010",
        "components": ["energy_supply"],
        "created_at": "2024-01-01T00:00:00",
    }
    await async_client.post("/contract/", json=contract_payload)

    # Invalid event type
    event = {
        "type": "invalid_event_type",
        "contract_number": "TEST010",
        "date": "2024-02-01",
        "created_at": "2024-02-01T10:00:00",
    }
    response = await async_client.post("/event", json=event)
    assert response.status_code == 200
    assert response.json()["status"] == "rejected"
    assert "invalid event type" in response.json()["message"].lower()


# Test: Event for component not in contract
@pytest.mark.asyncio
async def test_event_for_component_not_in_contract_rejected(async_client):
    """Test that an event for a component not in the contract is rejected."""
    # Create contract with only energy_supply and battery_optimization
    contract_payload = {
        "contract_number": "TEST011",
        "components": ["energy_supply", "battery_optimization"],
        "created_at": "2024-01-01T00:00:00",
    }
    await async_client.post("/contract/", json=contract_payload)

    # Try to create event for heatpump_optimization (not in contract)
    event = {
        "type": "heatpump_optimization_start",
        "contract_number": "TEST011",
        "date": "2024-02-01",
        "created_at": "2024-02-01T10:00:00",
    }
    response = await async_client.post("/event", json=event)
    assert response.status_code == 200
    assert response.json()["status"] == "rejected"
    assert "not available in contract" in response.json()["message"].lower()

    # Verify timeline doesn't include the rejected component
    timeline_response = await async_client.get("/TEST011/contract_timeline")
    assert timeline_response.status_code == 200
    data = timeline_response.json()
    # Should only have the two components from contract
    assert "energy_supply" in data["components"]
    assert "battery_optimization" in data["components"]
    assert "heatpump_optimization" not in data["components"]


# ==========================================
# EVENT ORDERING TESTS
# ==========================================


# Test: Multiple events processed in created_at order
@pytest.mark.asyncio
async def test_events_processed_in_created_at_order(async_client):
    """Test that events are processed in order based on created_at timestamp."""
    # Create contract
    contract_payload = {
        "contract_number": "TEST012",
        "components": ["battery_optimization"],
        "created_at": "2024-01-01T00:00:00",
    }
    await async_client.post("/contract/", json=contract_payload)

    # Submit events out of order by date, but in order by created_at
    # Event 1: Start with date 2024-02-15, created first
    await async_client.post("/event", json={
        "type": "battery_optimization_start",
        "contract_number": "TEST012",
        "date": "2024-02-15",
        "created_at": "2024-01-10T10:00:00",
    })

    # Event 2: Start with date 2024-02-01, created second (should overwrite)
    await async_client.post("/event", json={
        "type": "battery_optimization_start",
        "contract_number": "TEST012",
        "date": "2024-02-01",
        "created_at": "2024-01-20T10:00:00",
    })

    # Event 3: End
    await async_client.post("/event", json={
        "type": "battery_optimization_end",
        "contract_number": "TEST012",
        "date": "2024-03-01",
        "created_at": "2024-01-30T10:00:00",
    })

    # Verify timeline reflects the event created last (2024-02-01 start)
    timeline_response = await async_client.get("/TEST012/contract_timeline")
    assert timeline_response.status_code == 200
    data = timeline_response.json()
    assert data["components"]["battery_optimization"]["start"] == "2024-02-01"
    assert data["components"]["battery_optimization"]["end"] == "2024-03-01"


# Test: Late-arriving event overwrites earlier event
@pytest.mark.asyncio
async def test_late_arriving_event_overwrites(async_client):
    """Test that a late-arriving event (later created_at) overwrites an earlier one."""
    # Create contract
    contract_payload = {
        "contract_number": "TEST013",
        "components": ["energy_supply"],
        "created_at": "2024-01-01T00:00:00",
    }
    await async_client.post("/contract/", json=contract_payload)

    # First start event
    await async_client.post("/event", json={
        "type": "supply_energy_start",
        "contract_number": "TEST013",
        "date": "2024-02-01",
        "created_at": "2024-02-01T08:00:00",
    })

    # Late-arriving start event with different date but later created_at
    await async_client.post("/event", json={
        "type": "supply_energy_start",
        "contract_number": "TEST013",
        "date": "2024-02-10",
        "created_at": "2024-02-01T12:00:00",
    })

    # Verify the late-arriving event overwrote the earlier one
    timeline_response = await async_client.get("/TEST013/contract_timeline")
    assert timeline_response.status_code == 200
    data = timeline_response.json()
    assert data["components"]["energy_supply"]["start"] == "2024-02-10"


# ==========================================
# CONTRACT TIMELINE ENDPOINT TESTS
# ==========================================


# Test: Get timeline for contract with no events
@pytest.mark.asyncio
async def test_timeline_no_events(async_client):
    """Test that timeline returns null values for components with no events."""
    # Create contract
    contract_payload = {
        "contract_number": "TEST014",
        "components": ["energy_supply", "battery_optimization"],
        "created_at": "2024-01-01T00:00:00",
    }
    await async_client.post("/contract/", json=contract_payload)

    # Get timeline
    timeline_response = await async_client.get("/TEST014/contract_timeline")
    assert timeline_response.status_code == 200
    data = timeline_response.json()

    assert data["contract_number"] == "TEST014"
    assert data["components"]["energy_supply"]["start"] is None
    assert data["components"]["energy_supply"]["end"] is None
    assert data["components"]["battery_optimization"]["start"] is None
    assert data["components"]["battery_optimization"]["end"] is None


# Test: Get timeline for non-existing contract
@pytest.mark.asyncio
async def test_timeline_nonexistent_contract(async_client):
    """Test that getting timeline for a non-existing contract returns 404."""
    response = await async_client.get("/NONEXISTENT999/contract_timeline")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


# Test: Timeline shows only start when no end event
@pytest.mark.asyncio
async def test_timeline_only_start_no_end(async_client):
    """Test that timeline correctly shows start date with null end when no end event exists."""
    # Create contract
    contract_payload = {
        "contract_number": "TEST016",
        "components": ["heatpump_optimization"],
        "created_at": "2024-01-01T00:00:00",
    }
    await async_client.post("/contract/", json=contract_payload)

    # Only start event
    await async_client.post("/event", json={
        "type": "heatpump_optimization_start",
        "contract_number": "TEST016",
        "date": "2024-02-01",
        "created_at": "2024-02-01T10:00:00",
    })

    # Get timeline
    timeline_response = await async_client.get("/TEST016/contract_timeline")
    assert timeline_response.status_code == 200
    data = timeline_response.json()

    assert data["components"]["heatpump_optimization"]["start"] == "2024-02-01"
    assert data["components"]["heatpump_optimization"]["end"] is None
