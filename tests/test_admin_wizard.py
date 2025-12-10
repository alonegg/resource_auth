from backend.models import User
from backend.auth import create_access_token
from fastapi.testclient import TestClient

def test_admin_new_resource_page_crash(client, session, admin_user, admin_headers):
    """
    Test if GET /admin/resources/new crashes (500).
    """
    response = client.get("/admin/resources/new", headers=admin_headers, follow_redirects=False)
    if response.status_code != 200:
        print(f"FAILED: Status {response.status_code}")
        print(f"Content: {response.text}")
    assert response.status_code == 200
    assert "New Resource Wizard" in response.text

def test_admin_create_resource_post(client, session, admin_user, admin_headers):
    """
    Test creating a resource via POST.
    """
    data = {
        "name": "Test Wizard Resource",
        "category": "Software",
        "description": "Created via Wizard",
        "auth_type": "AUTO_ZIP",
        "valid_until": "2025-12-31",
        "software_delivery": "FILE" # Frontend helper field, backend might ignore or use?
        # Backend expects specific fields mapping.
    }
    # Note: Backend create_resource expects form fields.
    response = client.post("/admin/resources", data=data, headers=admin_headers, follow_redirects=False)
    assert response.status_code == 303
