"""
test_api.py
============
Tests for the Dashboard REST API (dashboard/app.py)
"""

import pytest
import json

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    from fastapi.testclient import TestClient
    from dashboard.app import app, state
    # Clear state
    state.simulations.clear()
    state.narrative_log.clear()
    return TestClient(app)


class TestRootEndpoints:
    def test_root(self, client):
        """GET / should return service info"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "FundGenesis API"
        assert "endpoints" in data

    def test_health(self, client):
        """GET /health should return ok"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"


class TestSimulationAPI:
    def test_run_simulation_minimal(self, client):
        """POST /api/v1/simulation/run with minimal config"""
        response = client.post("/api/v1/simulation/run", json={
            "n_steps": 10,
            "n_retail": 3,
            "n_trend": 1,
            "n_value": 1,
            "seed": 42,
        })
        assert response.status_code == 200
        data = response.json()
        assert "simulation_id" in data
        assert data["status"] == "completed"
        assert "summary" in data
        assert data["summary"]["final_price"] > 0

    def test_run_simulation_with_narratives(self, client):
        """POST /api/v1/simulation/run with narrative events"""
        response = client.post("/api/v1/simulation/run", json={
            "n_steps": 15,
            "n_retail": 3,
            "n_trend": 1,
            "n_value": 1,
            "seed": 42,
            "narrative_events": [
                {
                    "name": "Tech Boom",
                    "category": "fintech",
                    "polarity": "positive",
                    "intensity": 0.7,
                    "timing": 5,
                    "duration": 10,
                }
            ],
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"

    def test_get_simulation_not_found(self, client):
        """GET /api/v1/simulation/nonexistent should 404"""
        response = client.get("/api/v1/simulation/nonexistent")
        assert response.status_code == 404

    def test_get_simulation_after_run(self, client):
        """GET /api/v1/simulation/{id} should return results"""
        # Run a simulation first
        run_response = client.post("/api/v1/simulation/run", json={
            "n_steps": 10,
            "n_retail": 3,
            "n_trend": 1,
            "n_value": 1,
            "seed": 42,
        })
        sim_id = run_response.json()["simulation_id"]

        # Get results
        get_response = client.get(f"/api/v1/simulation/{sim_id}")
        assert get_response.status_code == 200
        data = get_response.json()
        assert data["id"] == sim_id
        assert data["status"] == "completed"

    def test_get_simulation_steps(self, client):
        """GET /api/v1/simulation/{id}/steps should return step data"""
        # Run simulation
        run_response = client.post("/api/v1/simulation/run", json={
            "n_steps": 10,
            "n_retail": 3,
            "n_trend": 1,
            "n_value": 1,
            "seed": 42,
        })
        sim_id = run_response.json()["simulation_id"]

        # Get steps
        steps_response = client.get(f"/api/v1/simulation/{sim_id}/steps")
        assert steps_response.status_code == 200
        data = steps_response.json()
        assert data["total_steps"] == 10
        assert len(data["steps"]) == 10

    def test_get_simulation_steps_pagination(self, client):
        """Steps endpoint should support pagination"""
        run_response = client.post("/api/v1/simulation/run", json={
            "n_steps": 10,
            "n_retail": 3,
            "n_trend": 1,
            "n_value": 1,
            "seed": 42,
        })
        sim_id = run_response.json()["simulation_id"]

        # Get paginated steps
        steps_response = client.get(f"/api/v1/simulation/{sim_id}/steps?offset=2&limit=3")
        assert steps_response.status_code == 200
        data = steps_response.json()
        assert len(data["steps"]) == 3

    def test_list_simulations(self, client):
        """GET /api/v1/simulations should list all simulations"""
        # Run a simulation
        client.post("/api/v1/simulation/run", json={
            "n_steps": 10,
            "n_retail": 3,
            "n_trend": 1,
            "n_value": 1,
            "seed": 42,
        })

        list_response = client.get("/api/v1/simulations")
        assert list_response.status_code == 200
        data = list_response.json()
        assert "simulations" in data
        assert len(data["simulations"]) >= 1


class TestNarrativeAPI:
    def test_inject_narrative(self, client):
        """POST /api/v1/narrative/inject should record narrative"""
        response = client.post("/api/v1/narrative/inject", json={
            "name": "Test Event",
            "category": "fintech",
            "polarity": "positive",
            "intensity": 0.7,
            "credibility": 0.8,
            "duration": 20,
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "injected"
        assert data["narrative"]["name"] == "Test Event"

    def test_inject_narrative_invalid_polarity(self, client):
        """Invalid polarity should return 400"""
        response = client.post("/api/v1/narrative/inject", json={
            "name": "Test Event",
            "category": "fintech",
            "polarity": "invalid",
            "intensity": 0.7,
        })
        assert response.status_code == 400


class TestMarketStateAPI:
    def test_get_market_state(self, client):
        """GET /api/v1/market/state should return market state"""
        response = client.get("/api/v1/market/state")
        assert response.status_code == 200
        data = response.json()
        assert "market" in data
        assert "price" in data["market"]


class TestAgentSummaryAPI:
    def test_get_agents_summary(self, client):
        """GET /api/v1/agents/summary should return agent info"""
        response = client.get("/api/v1/agents/summary")
        assert response.status_code == 200
        data = response.json()
        assert "agent_types" in data
        assert "network_structure" in data
        assert "reflexivity_model" in data

    def test_agent_types_count(self, client):
        """Should list 3 agent types"""
        response = client.get("/api/v1/agents/summary")
        data = response.json()
        assert len(data["agent_types"]) == 3
