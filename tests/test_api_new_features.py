
from backend.models import Resource, Application
from fastapi.testclient import TestClient
from datetime import datetime
import io

def test_auto_code_resource(client, session, test_user, auth_headers):
    # 1. Setup Resource
    res = Resource(name="LicenseKeyApp", category="Software", auth_type="AUTO_CODE", form_schema={}, config={})
    session.add(res)
    session.commit()
    session.refresh(res)
    
    # 2. Apply
    response = client.post(f"/resources/{res.id}/apply", data={}, follow_redirects=False)
    
    # 3. Verify Approved and Code Generated
    app = session.query(Application).filter(Application.resource_id == res.id).first()
    assert app.status == "APPROVED"
    assert app.auth_output is not None
    assert "code" in app.auth_output
    assert app.auth_output["code"].startswith("ETRAP-")

def test_legacy_zip_download(client, session, test_user, auth_headers, tmp_path):
    # 1. Create a dummy zip
    import zipfile
    zip_path = tmp_path / "legacy.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("legacy.txt", "Old Content")
        
    # 2. Setup Resource (Legacy: has zip_path, no root_path)
    res = Resource(
        name="LegacyRes", 
        category="Software", 
        auth_type="AUTO_ZIP", 
        form_schema={}, 
        config={"zip_path": str(zip_path), "inject_file": "lic.dat"}
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
    
    # 5. Verify Content
    content = io.BytesIO(response.content)
    with zipfile.ZipFile(content) as zf:
        assert "legacy.txt" in zf.namelist()
        assert "lic.dat" in zf.namelist()
