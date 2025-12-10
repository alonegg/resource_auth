def test_admin_root_redirect(client, session, admin_user, admin_headers):
    # Manually set cookie because admin_root calls get_current_user_optional directly
    client.cookies.set("user_id", str(admin_user.id))
    response = client.get("/admin", follow_redirects=False)
    # The code returns 302 Found
    assert response.status_code == 302
    assert response.headers["location"] == "/admin/dashboard"

def test_admin_root_redirect_login(client, session):
    response = client.get("/admin", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "/login"

def test_admin_resource_not_found(client, session, admin_user, admin_headers):
    response = client.post("/admin/resources/9999", data={
        "name": "N", "category": "C", "description": "D", "auth_type": "A", "valid_until": "2022-01-01"
    }, follow_redirects=False)
    assert response.status_code == 404
    
    response = client.post("/admin/resources/9999/delete", follow_redirects=False)
    assert response.status_code == 404
    
    response = client.get("/admin/resource/9999/edit", follow_redirects=False)
    assert response.status_code == 404

def test_preview_zip_invalid(client, session, admin_user, admin_headers):
    response = client.post(
        "/admin/tools/preview-zip", 
        files={"file": ("test.txt", b"text", "text/plain")}
    )
    assert response.status_code == 400
