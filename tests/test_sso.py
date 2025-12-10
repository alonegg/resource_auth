from unittest.mock import AsyncMock, patch
from backend.models import User

def test_sso_login_success(client, session):
    # Mock validate_ticket in resources.py (where it is used)
    with patch("backend.routers.resources.cas_client.validate_ticket", new_callable=AsyncMock) as mock_validate:
        mock_validate.return_value = {"user": "20230099"}
        
        response = client.get("/resource?ticket=ST-123456", follow_redirects=False)
        assert response.status_code == 302
        assert "user_id" in response.headers["set-cookie"]
        
        # Check user created
        user = session.query(User).filter(User.swufe_uid == "20230099").first()
        assert user is not None
        assert user.role == "user"

def test_sso_login_fail(client, session):
    with patch("backend.routers.resources.cas_client.validate_ticket", new_callable=AsyncMock) as mock_validate:
        mock_validate.return_value = None
        
        response = client.get("/resource?ticket=ST-INVALID", follow_redirects=False)
        # Assuming it just renders the page without login if ticket invalid
        assert response.status_code == 200
        assert "user_id" not in response.headers.get("set-cookie", "")

def test_sso_router_login(client):
    # Test backend/routers/sso.py
    response = client.get("/login/sso", follow_redirects=False)
    assert response.status_code in [302, 303, 307]
    assert "authserver.swufe.edu.cn" in response.headers["location"]
