from backend.models import Resource, Application, User
from fastapi.testclient import TestClient
from datetime import datetime

def test_list_resources(client, session):
    res = Resource(name="SAS Test", category="Software", auth_type="AUTO_ZIP", form_schema={}, config={})
    session.add(res)
    session.commit()
    
    response = client.get("/resource")
    assert response.status_code == 200
    assert "SAS Test" in response.text

def test_apply_resource(client, session, test_user, auth_headers):
    # 1. Setup Resource
    res = Resource(
        name="DSLAB GPU", 
        category="Compute", 
        auth_type="MANUAL", 
        form_schema={"fields": [{"name": "project_desc", "type": "text"}]}, 
        config={}
    )
    session.add(res)
    session.commit()
    session.refresh(res)
    
    # 2. Apply
    response = client.post(
        f"/resources/{res.id}/apply", 
        data={"project_desc": "My AI Project"},
        follow_redirects=False # Expect redirect
    )
    
    assert response.status_code == 303
    
    # 3. Verify DB
    app = session.query(Application).filter(Application.user_id == test_user.id).first()
    assert app is not None
    assert app.resource_id == res.id
    assert app.status == "PENDING"
    assert app.user_input["project_desc"] == "My AI Project"

def test_auto_approve_resource(client, session, test_user, auth_headers):
    # 1. Setup Resource
    res = Resource(name="Auto SAS", category="Software", auth_type="AUTO_ZIP", form_schema={}, config={})
    session.add(res)
    session.commit()
    session.refresh(res)
    
    # 2. Apply
    response = client.post(f"/resources/{res.id}/apply", data={}, follow_redirects=False)
    
    # 3. Verify Approved
    app = session.query(Application).filter(Application.resource_id == res.id).first()
    assert app.status == "APPROVED"
    assert app.approved_at is not None

def test_admin_approval(client, session, admin_user, admin_headers):
    # 1. Setup User and App
    student = User(swufe_uid="stu1", name="Stu", password_hash="x", email="s@s.cn", department="S", phone="123")
    session.add(student)
    session.commit()
    session.refresh(student)
    
    res = Resource(name="GHE", category="API", auth_type="MANUAL", form_schema={}, config={})
    session.add(res)
    session.commit()
    session.refresh(res)
    
    app_obj = Application(user_id=student.id, resource_id=res.id, status="PENDING")
    session.add(app_obj)
    session.commit()
    session.refresh(app_obj)
    
    # 2. Approve
    response = client.post(f"/admin/approve/{app_obj.id}", follow_redirects=False)
    assert response.status_code == 303
    
    # 3. Verify
    session.refresh(app_obj)
    assert app_obj.status == "APPROVED"

def test_admin_reject(client, session, admin_user, admin_headers):
    # 1. Setup
    res = Resource(name="GHE2", category="API", auth_type="MANUAL", form_schema={}, config={})
    session.add(res)
    session.commit()
    
    app_obj = Application(user_id=admin_user.id, resource_id=res.id, status="PENDING")
    session.add(app_obj)
    session.commit()
    session.refresh(app_obj)
    
    # 2. Reject
    response = client.post(f"/admin/reject/{app_obj.id}", data={"reason": "No quota"}, follow_redirects=False)
    assert response.status_code == 303
    
    # 3. Verify
    session.refresh(app_obj)
    assert app_obj.status == "REJECTED"
    assert app_obj.auth_output.get("rejection_reason") == "No quota"

def test_admin_create_resource(client, session, admin_user, admin_headers):
    response = client.post("/admin/resources", data={
        "name": "New Res",
        "category": "Data",
        "description": "Desc",
        "auth_type": "MANUAL",
        "valid_until": "2025-12-31"
    }, follow_redirects=False)
    
    assert response.status_code == 303
    
    res = session.query(Resource).filter(Resource.name == "New Res").first()
    assert res is not None
    assert res.category == "Data"

def test_admin_dashboard(client, session, admin_user, admin_headers):
    response = client.get("/admin/dashboard")
    assert response.status_code == 200
    assert "E-TRAP Admin" in response.text

def test_admin_update_resource(client, session, admin_user, admin_headers):
    # 1. Create
    from datetime import date
    res = Resource(name="Old Name", category="Software", auth_type="MANUAL", form_schema={}, config={}, valid_until=date(2024, 1, 1))
    session.add(res)
    session.commit()
    session.refresh(res)
    
    # 2. Update
    response = client.post(f"/admin/resources/{res.id}", data={
        "name": "New Name",
        "category": "Software",
        "description": "Updated",
        "auth_type": "MANUAL",
        "valid_until": "2025-01-01"
    }, follow_redirects=False)
    
    assert response.status_code == 303
    
    session.refresh(res)
    assert res.name == "New Name"
    assert res.description == "Updated"

def test_download_resource(client, session, test_user, auth_headers, tmp_path):
    # 1. Create content
    content_dir = tmp_path / "content"
    content_dir.mkdir()
    (content_dir / "test.txt").write_text("Secret")
    
    # 2. Setup Resource
    res = Resource(
        name="Downloadable", 
        category="Software", 
        auth_type="AUTO_ZIP", 
        form_schema={}, 
        config={"root_path": str(content_dir), "inject_file": "lic.dat"}
    )
    session.add(res)
    session.commit()
    session.refresh(res)
    
    # 3. Approve App
    app_obj = Application(user_id=test_user.id, resource_id=res.id, status="APPROVED", approved_at=datetime.now())
    session.add(app_obj)
    session.commit()
    
    # 4. Download
    response = client.get(f"/resources/{res.id}/download")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"

def test_download_unauthorized(client, session, test_user, auth_headers):
    res = Resource(name="NoApp", category="Software", auth_type="AUTO_ZIP", form_schema={}, config={})
    session.add(res)
    session.commit()
    
    response = client.get(f"/resources/{res.id}/download")
    assert response.status_code == 403

def test_admin_delete_resource(client, session, admin_user, admin_headers):
    res = Resource(name="To Delete", category="Software", auth_type="MANUAL", form_schema={}, config={})
    session.add(res)
    session.commit()
    session.refresh(res)
    
    response = client.post(f"/admin/resources/{res.id}/delete", follow_redirects=False)
    assert response.status_code == 303
    
    res_check = session.get(Resource, res.id)
    assert res_check is None

def test_admin_edit_page(client, session, admin_user, admin_headers):
    res = Resource(name="EditMe", category="Software", auth_type="MANUAL", form_schema={}, config={})
    session.add(res)
    session.commit()
    
    response = client.get(f"/admin/resource/{res.id}/edit")
    assert response.status_code == 200
    assert "EditMe" in response.text

def test_admin_update_with_file(client, session, admin_user, admin_headers, tmp_path):
    # 1. Create
    from datetime import date
    res = Resource(name="FileRes", category="Software", auth_type="AUTO_ZIP", form_schema={}, config={}, valid_until=date(2025,1,1))
    session.add(res)
    session.commit()
    
    # 2. Upload Zip
    import io
    import zipfile
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as zf:
        zf.writestr("test.txt", "content")
    zip_buf.seek(0)
    
    response = client.post(
        f"/admin/resources/{res.id}", 
        data={
            "name": "FileRes",
            "category": "Software",
            "description": "Desc",
            "auth_type": "AUTO_ZIP",
            "valid_until": "2025-01-01"
        },
        files={"file_zip": ("update.zip", zip_buf, "application/zip")},
        follow_redirects=False
    )
    assert response.status_code == 303
    
    session.refresh(res)
    # Check config has root_path
    assert "root_path" in res.config
    import os
    assert os.path.exists(res.config["root_path"])
    assert os.path.exists(os.path.join(res.config["root_path"], "test.txt"))
