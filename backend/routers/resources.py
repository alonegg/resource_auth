from fastapi import APIRouter, Depends, HTTPException, status, Request, Response, Form
from fastapi.responses import HTMLResponse, StreamingResponse, RedirectResponse
from sqlmodel import Session, select, desc
from datetime import datetime, timedelta
import json
import os

from ..database import get_session
from ..models import User, Resource, Application, AuditLog
from ..auth import get_current_user, require_profile_completion, get_current_user_optional, create_access_token, COOKIE_NAME
from ..core.watermark import stream_zip_from_directory
from ..main import templates
from ..core.cas_client import CASClient

# Strict Service URL for Validation
SERVICE_URL = "http://192.168.77.87/resource"
CAS_SERVER_URL = "https://authserver.swufe.edu.cn/authserver"
cas_client = CASClient(CAS_SERVER_URL)

router = APIRouter()

from ..core.i18n import get_translator

@router.get("/resource", response_class=HTMLResponse)
async def list_resources(
    request: Request, 
    user: User | None = Depends(get_current_user_optional), # Use Optional Auth
    session: Session = Depends(get_session),
    trans: tuple = Depends(get_translator),
    ticket: str = None
):
    # 0. Handle SSO Ticket (If present)
    if ticket:
        # Validate Ticket
        user_data = await cas_client.validate_ticket(ticket, SERVICE_URL)
        if not user_data:
            # Invalid ticket, show list but maybe error? Or just ignore
            pass 
        else:
            cas_uid = user_data.get('user')
            # Provision User
            user_db = session.exec(select(User).where(User.swufe_uid == cas_uid)).first()
            if not user_db:
                user_db = User(
                    swufe_uid=cas_uid,
                    name=cas_uid, 
                    role="user", 
                    department="SSO User",
                    password_hash="SSO_USER",
                    email="",
                    phone=""
                )
                session.add(user_db)
                session.commit()
                session.refresh(user_db)
                
            # Create Session
            access_token = create_access_token(data={"sub": user_db.id})
            
            # Check Profile Completion
            if not user_db.email or not user_db.phone:
                redirect_url = "/profile/complete"
            else:
                redirect_url = "/resource"
            
            resp = RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)
            resp.set_cookie(key=COOKIE_NAME, value=access_token, httponly=True, max_age=1800)
            return resp

    _, lang = trans # Unpack translation helper and language code

    # 1. Get all public resources
    resources = session.exec(select(Resource).where(Resource.is_active == True)).all()
    
    # 2. Get user's applications (Only if logged in)
    app_map = {}
    if user:
        # Fetch all applications sorted by ID ascending, so the dictionary comprehension
        # keeps the latest application for each resource_id.
        apps = session.exec(select(Application).where(Application.user_id == user.id).order_by(Application.id)).all()
        app_map = {app.resource_id: app for app in apps}
    
    return templates.TemplateResponse("resources.html", {
        "request": request, 
        "user": user, 
        "resources": resources, 
        "app_map": app_map,
        "_": _,
        "lang": lang
    })

@router.post("/resources/{resource_id}/apply")
async def apply_resource(
    request: Request,
    resource_id: int, 
    user: User = Depends(require_profile_completion),
    session: Session = Depends(get_session)
):
    resource = session.get(Resource, resource_id)
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
        
    # Check existing
    existing = session.exec(select(Application).where(
        Application.user_id == user.id, 
        Application.resource_id == resource_id
    ).order_by(desc(Application.id))).first()
    
    # If existing and ACTIVE (PENDING or APPROVED), block
    if existing and existing.status in ["PENDING", "APPROVED"]:
        return Response(status_code=400, content="Already applied and active")
    
    # Dynamic Form Data Handling
    form_data = await request.form()
    user_input = {k: v for k, v in form_data.items()}
    
    app = Application(
        user_id=user.id,
        resource_id=resource_id,
        user_input=user_input,
        status="PENDING"
    )
    
    # Auto-Approve Type A
    if resource.auth_type == 'AUTO_ZIP':
        app.status = 'APPROVED'
        app.approved_at = datetime.now()
        if resource.valid_until:
            app.expired_at = datetime.combine(resource.valid_until, datetime.max.time())
        else:
             app.expired_at = datetime.now() + timedelta(days=180)
    
    # Auto-Approve Type: AUTO_CODE
    elif resource.auth_type == 'AUTO_CODE':
        app.status = 'APPROVED'
        app.approved_at = datetime.now()
        # Generate Code
        import uuid
        import random
        # Format: ETRAP-{Year}{Month}-{HEX}
        now = datetime.now()
        suffix = "".join(random.choices("ABCDEF0123456789", k=6))
        code = f"ETRAP-{now.year}{now.month:02d}-{suffix}"
        
        app.auth_output = {"code": code}
        
        if resource.valid_until:
            app.expired_at = datetime.combine(resource.valid_until, datetime.max.time())
        else:
             app.expired_at = datetime.now() + timedelta(days=365)

    session.add(app)
    
    # Audit
    audit = AuditLog(user_id=user.id, action="APPLY", resource_id=resource_id, ip_address=request.client.host, details=f"Status: {app.status}")
    session.add(audit)
    
    session.commit()
    return RedirectResponse(url="/resource", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/resources/{resource_id}/download")
async def download_resource(
    resource_id: int,
    user: User = Depends(require_profile_completion),
    session: Session = Depends(get_session)
):
    # 1. Verify Application
    app = session.exec(select(Application).where(
        Application.user_id == user.id, 
        Application.resource_id == resource_id,
        Application.status == 'APPROVED'
    )).first()
    
    if not app:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    resource = session.get(Resource, resource_id)
    if resource.auth_type != 'AUTO_ZIP':
        raise HTTPException(status_code=400, detail="Not a downloadable resource")
        
    # 2. Get Config
    root_path = resource.config.get("root_path")
    zip_path = resource.config.get("zip_path") # Legacy
    inject_file = resource.config.get("inject_file", "licence.dat")
    
    if not root_path and not zip_path:
        raise HTTPException(status_code=500, detail="Misconfigured resource: No content found")
        
    # 3. Watermark & Stream
    try:
        from ..core.watermark import stream_zip_from_directory
        
        user_info = {
            "id": user.id,
            "name": user.name,
            "username": user.swufe_uid,
            "dept": user.department,
            "apply_time": app.approved_at.isoformat() if app.approved_at else None,
            "apply_id": app.id
        }
        
        if root_path and os.path.exists(root_path):
            # NEW: Stream from directory
            stream = stream_zip_from_directory(root_path, user_info, inject_file)
        elif zip_path and os.path.exists(zip_path):
            # LEGACY: Stream from zip file (Fix for "Legacy ZIP mode deprecated" error)
            from ..core.watermark import stream_zip_from_zip_file
            stream = stream_zip_from_zip_file(zip_path, user_info, inject_file)
            print(f"WARNING: Serving legacy resource {resource.id} from zip file. Please re-upload.")
        else:
             raise HTTPException(status_code=500, detail="Content file missing on server")
        
        # Audit
        audit = AuditLog(user_id=user.id, action="DOWNLOAD", resource_id=resource_id, ip_address="127.0.0.1", details=f"Downloaded {resource.name}")
        session.add(audit)
        session.commit()
        
        # Download Filename Logic
        download_name = "SAS LIC.zip" if "SAS" in resource.name else f"{resource.name}.zip"
        
        return StreamingResponse(
            stream, 
            media_type="application/zip", 
            headers={"Content-Disposition": f'attachment; filename="{download_name}"'}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
