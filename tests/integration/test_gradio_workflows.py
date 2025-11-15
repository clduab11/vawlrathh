"""Integration tests for Gradio UI workflows."""

from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def sample_deck_csv():
    """Provide sample CSV path or skip if unavailable."""
    sample_path = (
        Path(__file__).parent.parent.parent / "examples" / "sample_deck.csv"
    )
    if not sample_path.exists():
        pytest.skip("Sample CSV not found")
    return sample_path


class TestDeckUploadWorkflow:
    """Test complete deck upload workflows."""
    
    @pytest.mark.asyncio
    async def test_csv_upload_to_analysis_workflow(
        self,
        api_client,
        sample_deck_csv
    ):
        """Test uploading CSV deck and running analysis."""
        with sample_deck_csv.open('rb') as file_handle:
            response = await api_client.post(
                "/api/v1/upload/csv",
                files={"file": ("deck.csv", file_handle, "text/csv")}
            )

        assert response.status_code == 200
        data = response.json()
        assert "deck_id" in data
        deck_id = data["deck_id"]

        response = await api_client.post(f"/api/v1/analyze/{deck_id}")
        assert response.status_code == 200
        analysis = response.json()
        assert "analysis" in analysis
    
    @pytest.mark.asyncio
    async def test_text_upload_to_optimization_workflow(self, api_client):
        """Test uploading text deck and running optimization."""
        deck_text = """
        4 Lightning Bolt (M11) 146
        4 Counterspell (MH2) 267
        20 Island (BRO) 280
        """

        response = await api_client.post(
            "/api/v1/upload/text",
            json={"deck_string": deck_text, "format": "Modern"}
        )

        assert response.status_code == 200
        data = response.json()
        deck_id = data["deck_id"]

        response = await api_client.post(f"/api/v1/optimize/{deck_id}")
        assert response.status_code == 200
        optimization = response.json()
        assert "suggestions" in optimization


class TestChatWorkflow:
    """Test WebSocket chat workflows."""
    
    @pytest.mark.asyncio
    async def test_websocket_chat_connection(self):
        """Test establishing WebSocket connection and sending message."""
        # This will require websockets library
        pytest.skip("Requires websockets client implementation")
    
    @pytest.mark.asyncio
    async def test_chat_with_deck_context(self):
        """Test chat with deck ID context."""
        pytest.skip("Requires websockets client implementation")


class TestPurchaseWorkflow:
    """Test purchase info workflows."""
    
    @pytest.mark.asyncio
    async def test_get_purchase_info_for_deck(self, api_client):
        """Test retrieving purchase info after deck upload."""
        deck_text = """
        4 Lightning Bolt (M11) 146
        20 Island (BRO) 280
        """

        response = await api_client.post(
            "/api/v1/upload/text",
            json={"deck_string": deck_text}
        )
        assert response.status_code == 200
        deck_id = response.json()["deck_id"]

        response = await api_client.get(f"/api/v1/purchase/{deck_id}")
        assert response.status_code == 200
        purchase_info = response.json()

        assert purchase_info["deck_id"] == deck_id
        assert purchase_info["deck_name"]

        expected_keys = {
            "total_cards",
            "purchasable_cards",
            "arena_only_cards",
            "total_price_usd",
            "cards",
            "arena_only",
            "summary",
        }
        assert expected_keys.issubset(purchase_info.keys())
        assert isinstance(purchase_info["cards"], list)
        assert isinstance(purchase_info["summary"], dict)
        assert "cheapest_vendor_breakdown" in purchase_info["summary"]
        assert "avg_card_price_usd" in purchase_info["summary"]

        if purchase_info["cards"]:
            card = purchase_info["cards"][0]
            assert {
                "card_name",
                "quantity",
                "unit_price_usd",
                "total_price_usd",
                "best_vendor",
                "vendors",
            }.issubset(card.keys())
            assert isinstance(card["vendors"], list)
            if card["vendors"]:
                vendor = card["vendors"][0]
                assert {
                    "vendor_name",
                    "purchase_url",
                    "in_stock",
                }.issubset(vendor.keys())
