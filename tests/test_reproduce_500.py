
from backend.models import Resource
from fastapi.testclient import TestClient
import pytest

def test_edit_resource_page_500(client, session, admin_user, admin_headers):
    """
    Reproduce 500 error on edit resource page.
    """
    # 1. Create a resource that might cause issues. 
    # The user said ID 2. Let's just create one.
    # Case A: config is None
    res = Resource(
        name="Buggy Resource", 
        category="Software", 
        description="Desc", 
        auth_type="MANUAL", 
        form_schema={},
        config=None # Potentially dangerous if code assumes dict
    )
    session.add(res)
    session.commit()
    session.refresh(res)
    
    # 2. Access Edit Page (GET)
    response = client.get(f"/admin/resource/{res.id}/edit", headers=admin_headers)
    assert response.status_code == 200
    
    # 3. Update Resource (POST) - Should not crash
    data = {
        "name": "Fixed Resource",
        "category": "Software",
        "description": "Desc Updated",
        "auth_type": "MANUAL",
        "valid_until": "2025-12-31"
    }
    response = client.post(f"/admin/resources/{res.id}", data=data, headers=admin_headers, follow_redirects=False)
    assert response.status_code == 303
    
    # Verify config is initialized
    session.refresh(res)
    assert res.name == "Fixed Resource"
    assert res.config == {} # Should be initialized to dict
