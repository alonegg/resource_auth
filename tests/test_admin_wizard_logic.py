from backend.models import Resource
from fastapi.testclient import TestClient

def test_admin_wizard_validation_logic(client, session, admin_user, admin_headers):
    """
    Simulate wizard validation flow by checking if backend rejects incomplete data.
    Frontend validation is JS based, but backend MUST also validate.
    """
    # 1. Try to submit incomplete data (Missing auth_type, valid_until)
    data_incomplete = {
        "name": "Incomplete Resource",
        "category": "Software",
        "description": "Desc"
    }
    response = client.post("/admin/resources", data=data_incomplete, headers=admin_headers, follow_redirects=False)
    # Backend Pydantic/FastAPI Form validation should catch missing fields (422 Unprocessable Entity)
    assert response.status_code == 422
    
    # 2. Try to submit with missing Category
    data_no_cat = {
        "name": "No Cat Resource",
        "auth_type": "AUTO_ZIP",
        "valid_until": "2025-01-01"
    }
    response = client.post("/admin/resources", data=data_no_cat, headers=admin_headers, follow_redirects=False)
    assert response.status_code == 422

def test_admin_wizard_full_flow(client, session, admin_user, admin_headers):
    """
    Test a complete valid submission mimicking the wizard steps.
    """
    data = {
        "name": "Wizard Complete Resource",
        "category": "Data",
        "description": "<p>Rich Text Description</p>",
        "valid_until": "2025-12-31",
        "auth_type": "MANUAL",
        "quota": 500
    }
    response = client.post("/admin/resources", data=data, headers=admin_headers, follow_redirects=False)
    assert response.status_code == 303
    
    # Verify DB
    res = session.query(Resource).filter(Resource.name == "Wizard Complete Resource").first()
    assert res is not None
    assert res.category == "Data"
    assert res.auth_type == "MANUAL"
