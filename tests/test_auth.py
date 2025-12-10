from backend.models import User
from fastapi.testclient import TestClient
import io

def test_login_flow(client, session, test_user):
    # 1. Login Page
    response = client.get("/login")
    assert response.status_code == 200
    
    # 2. Login Action (Dev Mode)
    # Note: password is checked against hashed password. test_user has "hashed".
    # verify_password uses pwd_context.verify.
    # We need to set a real hash for the test user or mock verify_password.
    # Easiest is to update test_user with a known hash.
    from backend.auth import get_password_hash
    test_user.password_hash = get_password_hash("password123")
    session.add(test_user)
    session.commit()
    
    response = client.post("/login", data={"swufe_uid": test_user.swufe_uid, "password": "password123"}, follow_redirects=False)
    assert response.status_code == 303
    assert "user_id" in response.cookies

def test_logout(client, session, auth_headers):
    response = client.get("/logout", follow_redirects=False)
    assert response.status_code in [303, 307]
    # Starlette delete_cookie sets max-age=0
    assert 'user_id=""' in response.headers["set-cookie"] or 'Max-Age=0' in response.headers["set-cookie"]

def test_profile_complete(client, session, auth_headers, test_user):
    # 1. Set incomplete
    test_user.email = ""
    session.add(test_user)
    session.commit()
    
    # 2. Get Page
    response = client.get("/profile/complete")
    assert response.status_code == 200
    
    # 3. Submit
    response = client.post("/profile/complete", data={
        "email": "new@s.cn", 
        "phone": "999",
        "name": test_user.name,
        "department": test_user.department
    }, follow_redirects=False)
    assert response.status_code == 303
    
    session.refresh(test_user)
    assert test_user.email == "new@s.cn"

def test_admin_preview_zip(client, session, admin_user, admin_headers):
    # Upload a dummy zip
    zip_content = io.BytesIO()
    import zipfile
    with zipfile.ZipFile(zip_content, "w") as zf:
        zf.writestr("hello.txt", "world")
    zip_content.seek(0)
    
    response = client.post(
        "/admin/tools/preview-zip", 
        files={"file": ("test.zip", zip_content, "application/zip")}
    )
    assert response.status_code == 200
    assert "hello.txt" in response.json()["files"]

def test_admin_decrypt_tool(client, session, admin_user, admin_headers):
    # 1. Encrypt something
    from backend.core.watermark import cipher
    import json
    data = {"uid": 123}
    encrypted = cipher.encrypt(json.dumps(data).encode())
    
    # 2. Upload
    response = client.post(
        "/admin/tools/decrypt",
        files={"file": ("trace.dat", encrypted, "application/octet-stream")}
    )
    assert response.status_code == 200
    assert "uid" in response.text
