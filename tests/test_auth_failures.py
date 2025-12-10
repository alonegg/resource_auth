from backend.models import Resource

def test_require_admin_fail(client, session, test_user, auth_headers):
    # Try to access admin dashboard as normal user
    # Note: admin_dashboard checks role using require_admin dependency
    response = client.get("/admin/dashboard", follow_redirects=False)
    assert response.status_code == 403

def test_require_profile_fail(client, session, auth_headers, test_user):
    # Incomplete profile
    test_user.email = ""
    session.add(test_user)
    session.commit()
    
    # Create resource
    res = Resource(name="R", category="Software", auth_type="AUTO_ZIP", form_schema={}, config={})
    session.add(res)
    session.commit()
    
    # Try to download (requires profile completion)
    # Need an approved application first?
    # download_resource checks require_profile_completion FIRST.
    
    # But wait, download_resource also checks Application.
    # If I don't have application, I get 403 or 404?
    # It checks require_profile_completion dependency.
    
    response = client.get(f"/resources/{res.id}/download", follow_redirects=False)
    
    # Should be 403 because of profile, OR 403 because of no app.
    # require_profile_completion raises 403 with specific detail.
    
    assert response.status_code == 403
    assert "Profile incomplete" in response.text
