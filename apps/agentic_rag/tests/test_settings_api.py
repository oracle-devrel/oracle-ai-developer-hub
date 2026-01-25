"""
Tests for Settings API.

This test suite verifies that:
1. Settings endpoints work correctly
2. Model switching updates the system
3. Available models are listed

Run with: pytest tests/test_settings_api.py -v
"""

import pytest
import requests
import json

BACKEND_URL = "http://localhost:8000"
TIMEOUT = 30


class TestSettingsAPI:
    """Test settings API endpoints."""

    def test_get_settings(self):
        """Test getting current settings."""
        response = requests.get(f"{BACKEND_URL}/v1/settings", timeout=TIMEOUT)
        assert response.status_code == 200

        data = response.json()
        assert "model" in data
        assert "available_models" in data
        assert "model_name" in data["model"]

    def test_get_current_model(self):
        """Test getting current model."""
        response = requests.get(f"{BACKEND_URL}/v1/settings/model", timeout=TIMEOUT)
        assert response.status_code == 200

        data = response.json()
        assert "model_name" in data
        assert data["model_name"]  # Should not be empty

    def test_list_available_models(self):
        """Test listing available Ollama models."""
        response = requests.get(f"{BACKEND_URL}/v1/settings/models", timeout=TIMEOUT)
        assert response.status_code == 200

        data = response.json()
        assert "models" in data
        assert "count" in data
        assert "current" in data
        assert data["count"] > 0
        assert len(data["models"]) > 0

    def test_update_model(self):
        """Test updating the active model."""
        # Get current model first
        current_response = requests.get(
            f"{BACKEND_URL}/v1/settings/model",
            timeout=TIMEOUT
        )
        current_model = current_response.json()["model_name"]

        # Update to a different model
        new_model = "gemma3:270m"
        response = requests.post(
            f"{BACKEND_URL}/v1/settings/model",
            json={"model_name": new_model},
            timeout=TIMEOUT
        )
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["current_model"] == new_model

        # Verify it changed
        verify_response = requests.get(
            f"{BACKEND_URL}/v1/settings/model",
            timeout=TIMEOUT
        )
        assert verify_response.json()["model_name"] == new_model

        # Restore original model
        requests.post(
            f"{BACKEND_URL}/v1/settings/model",
            json={"model_name": current_model},
            timeout=TIMEOUT
        )

    def test_test_model_endpoint(self):
        """Test the model testing endpoint."""
        response = requests.post(
            f"{BACKEND_URL}/v1/settings/model/test",
            json={"model_name": "gemma3:270m"},
            timeout=60
        )
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["model"] == "gemma3:270m"
        assert "response" in data

    def test_invalid_model_test(self):
        """Test model testing with invalid model."""
        response = requests.post(
            f"{BACKEND_URL}/v1/settings/model/test",
            json={"model_name": "nonexistent-model-xyz"},
            timeout=30
        )
        assert response.status_code == 400


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
