from backend.core.cas_client import CASClient
from unittest.mock import MagicMock, patch
import pytest

def test_cas_client_urls():
    client = CASClient("https://cas.example.com")
    
    login_url = client.get_login_url("http://service.com")
    assert login_url == "https://cas.example.com/login?service=http%3A%2F%2Fservice.com"
    
    logout_url = client.get_logout_url("http://service.com")
    assert logout_url == "https://cas.example.com/logout?service=http%3A%2F%2Fservice.com"

@pytest.mark.asyncio
async def test_cas_validate_ticket_success():
    client = CASClient("https://cas.example.com")
    
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.return_value = MagicMock(
            status_code=200,
            content=b"""<cas:serviceResponse xmlns:cas='http://www.yale.edu/tp/cas'>
                <cas:authenticationSuccess>
                    <cas:user>testuser</cas:user>
                    <cas:attributes>
                        <cas:email>test@example.com</cas:email>
                    </cas:attributes>
                </cas:authenticationSuccess>
            </cas:serviceResponse>"""
        )
        
        user_data = await client.validate_ticket("ST-123", "http://service.com")
        assert user_data["user"] == "testuser"
        assert user_data["attributes"]["cas:email"] == "test@example.com"

@pytest.mark.asyncio
async def test_cas_validate_ticket_fail():
    client = CASClient("https://cas.example.com")
    
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.return_value = MagicMock(
            status_code=200,
            content=b"""<cas:serviceResponse xmlns:cas='http://www.yale.edu/tp/cas'>
                <cas:authenticationFailure code="INVALID_TICKET">
                    Ticket not recognized
                </cas:authenticationFailure>
            </cas:serviceResponse>"""
        )
        
        user_data = await client.validate_ticket("ST-123", "http://service.com")
        assert user_data is None
