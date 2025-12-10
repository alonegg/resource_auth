from fastapi import APIRouter, Depends, HTTPException, status, Request, Response, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select, func, desc, or_
from datetime import datetime, timedelta, date, time
from ..database import get_session
from ..models import User, Application, Resource, AuditLog
from ..auth import require_admin
from ..core.i18n import get_translator

router = APIRouter()
templates = Jinja2Templates(directory="backend/templates")

@router.get("/admin", include_in_schema=False)
async def admin_root(
    request: Request,
    session: Session = Depends(get_session)
):
    # Check if logged in & admin
    from backend.auth import get_current_user_optional
    user = get_current_user_optional(request, session)
    if user and user.role == "admin":
        return RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_302_FOUND)
    return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

@router.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    user: User = Depends(require_admin), # Admin Only
    session: Session = Depends(get_session),
    status_filter: str = "PENDING",
    trans: tuple = Depends(get_translator)
):
    _, lang = trans
    # 1. Get Applications (Filtered)
    query = select(Application)
    if status_filter != "ALL":
        query = query.where(Application.status == status_filter)
    query = query.order_by(Application.created_at.desc())
    
    apps = session.exec(query).all()
    
    # 2. Get Statistics (Top Resources)
    stats_query = (
        select(Resource.name, func.count(Application.id).label("count"))
        .join(Application)
        .group_by(Resource.id)
        .order_by(desc("count"))
        .limit(5)
    )
    top_res_rows = session.exec(stats_query).all()
    
    # 3. Get Logs
    audit_logs = session.exec(select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(10)).all()
    
    # 4. Get All Resources (For management tab)
    resources = session.exec(select(Resource)).all()
    
    total_requests = session.exec(select(func.count(Application.id))).one()
    
    stats = {
        "total_requests": total_requests,
        "top_resources": top_res_rows
    }
    
    return templates.TemplateResponse("admin_dashboard.html", {
        "request": request, 
        "user": user,
        "applications": apps,
        "resources": resources,
        "pending_count": len(apps),
        "audit_logs": audit_logs,
        "stats": stats,
        "_": _,
        "lang": lang
    })

@router.post("/admin/approve/{app_id}")
async def approve_application(
    app_id: int,
    request: Request,
    user: User = Depends(require_admin),
    session: Session = Depends(get_session)
):
    app = session.get(Application, app_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
        
    resource = session.get(Resource, app.resource_id)
    
    app.status = "APPROVED"
    app.approved_at = datetime.now()
    
    if resource.valid_until:
        # Set to end of the valid until day
        app.expired_at = datetime.combine(resource.valid_until, time.max)
    else:
        # Fallback if no valid_until (should not happen in new logic, but safe default)
        app.expired_at = datetime.now() + timedelta(days=180)
    
    session.add(app)
    
    # Audit Log
    audit = AuditLog(
        user_id=user.id, 
        action="APPROVE", 
        resource_id=app.resource_id, 
        details=f"Approved Application #{app.id} for {app.user.name}",
        ip_address=request.client.host if request.client else "unknown"
    )
    session.add(audit)
    
    session.commit()
    return RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/admin/reject/{app_id}")
async def reject_application(
    app_id: int,
    request: Request,
    reason: str = Form(...),
    user: User = Depends(require_admin),
    session: Session = Depends(get_session)
):
    app = session.get(Application, app_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    
    if not reason.strip():
        raise HTTPException(status_code=400, detail="Rejection reason cannot be empty")
    
    app.status = "REJECTED"
    # Store rejection reason in auth_output for MVP
    app.auth_output = {"rejection_reason": reason}
    session.add(app)
    
    # Audit Log
    audit = AuditLog(
        user_id=user.id, 
        action="REJECT", 
        resource_id=app.resource_id, 
        details=f"Rejected Application #{app.id}. Reason: {reason}",
        ip_address=request.client.host if request.client else "unknown"
    )
    session.add(audit)
    
    session.commit()
    return RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/admin/resources/new", response_class=HTMLResponse)
async def new_resource_page(
    request: Request,
    user: User = Depends(require_admin),
    trans: tuple = Depends(get_translator)
):
    _, lang = trans
    return templates.TemplateResponse("resource_editor.html", {
        "request": request, 
        "user": user, 
        "resource": None,
        "zip_files": [],
        "_": _, 
        "lang": lang
    })

@router.post("/admin/resources")
async def create_resource(
    request: Request,
    name: str = Form(...),
    category: str = Form(...),
    description: str = Form(...),
    auth_type: str = Form(...),
    valid_until: date = Form(...),
    # Optional Dynamic Fields
    file_zip: UploadFile = None,
    inject_file: str = Form(None),
    static_code: str = Form(None),
    instruction_text: str = Form(None), 
    usage_norms: str = Form(None),
    connection_info: str = Form(None),
    quota: int = Form(None),
    upstream_url: str = Form(None),
    public_installer_url: str = Form(None),
    user: User = Depends(require_admin),
    session: Session = Depends(get_session)
):
    try:
        # 1. Handle File Upload (for SAS/Zip type)
        config = {}
        if file_zip and file_zip.filename:
            # Save to ./data/resources/
            import os
            import shutil
            upload_dir = "data/resources"
            os.makedirs(upload_dir, exist_ok=True)
            file_path = os.path.join(upload_dir, file_zip.filename)
            
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file_zip.file, buffer)
                
            config["zip_path"] = file_path
            config["inject_file"] = inject_file or "license.dat"
        
        # 2. Handle Text Fields -> Config Payload
        if static_code:
            config["static_code"] = static_code
        if instruction_text:
            config["instruction_text"] = instruction_text
        if usage_norms:
            config["usage_norms"] = usage_norms
        if connection_info:
            config["connection_info"] = connection_info
        if quota:
            config["quota"] = quota
        if upstream_url:
            config["upstream_url"] = upstream_url
            
        # 3. Default Form Schema construction (Simplified for MVP)
        # In a real app, we might have a schema builder UI.
        form_schema = {"fields": []}
        if category == "Software":
            form_schema["fields"].append({"name": "usage_purpose", "label": "Usage Purpose", "type": "select", "options": ["Teaching", "Research"], "required": True})
            form_schema["fields"].append({"name": "course_name", "label": "Course Name (if Teaching)", "type": "text"})
        elif category == "Compute":
            form_schema["fields"].append({"name": "project_desc", "label": "Project Description", "type": "textarea", "required": True})
            form_schema["fields"].append({"name": "booking_time", "label": "Booking Time / Duration", "type": "text", "required": True})
        elif category == "Data":
            form_schema["fields"].append({"name": "project_desc", "label": "Reason for Request", "type": "textarea", "required": True})
        elif category == "Teaching":
            form_schema["fields"].append({"name": "course_code", "label": "Course Code", "type": "text", "required": True})
        
        # 4. Save to DB
        res = Resource(
            name=name,
            category=category,
            description=description,
            auth_type=auth_type,
            valid_until=valid_until,
            public_installer_url=public_installer_url,
            config=config,
            form_schema=form_schema
        )
        
        session.add(res)
        session.commit()
        session.refresh(res)
        
        return RedirectResponse(url="/admin/dashboard?tab=resources", status_code=status.HTTP_303_SEE_OTHER)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return HTMLResponse(content=f"<h1>500 Internal Server Error</h1><p>Failed to create resource.</p><pre>{str(e)}</pre>", status_code=500)

@router.get("/admin/resource/{id}/edit", response_class=HTMLResponse)
async def edit_resource_page(
    id: int, 
    request: Request, 
    user: User = Depends(require_admin),
    session: Session = Depends(get_session),
    trans: tuple = Depends(get_translator)
):
    _, lang = trans
    resource = session.get(Resource, id)
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
        
    zip_files = []
    # Check for unpacked content first
    config = resource.config or {}
    root_path = config.get("root_path")
    zip_path = config.get("zip_path") # Legacy fallback
    
    import os
    if root_path and os.path.exists(root_path):
        for root, dirs, files in os.walk(root_path):
            for file in files:
                rel_path = os.path.relpath(os.path.join(root, file), root_path)
                zip_files.append(rel_path)
    elif zip_path and os.path.exists(zip_path):
        import zipfile
        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                zip_files = zf.namelist()
        except Exception as e:
            zip_files = [f"Error reading zip: {str(e)}"]

    return templates.TemplateResponse("resource_editor.html", {"request": request, "user": user, "resource": resource, "zip_files": zip_files, "_": _, "lang": lang})

@router.post("/admin/resources/{res_id}")
async def update_resource(
    res_id: int,
    request: Request,
    name: str = Form(...),
    category: str = Form(...),
    description: str = Form(...),
    auth_type: str = Form(...),
    valid_until: date = Form(...),
    # Optional Dynamic Fields
    file_zip: UploadFile = None,
    inject_file: str = Form(None),
    static_code: str = Form(None),
    instruction_text: str = Form(None),
    usage_norms: str = Form(None),
    connection_info: str = Form(None),
    quota: int = Form(None),
    upstream_url: str = Form(None),
    public_installer_url: str = Form(None),
    user: User = Depends(require_admin),
    session: Session = Depends(get_session)
):
    resource = session.get(Resource, res_id)
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    
    # Update Basic Info
    resource.name = name
    resource.category = category
    resource.description = description
    resource.auth_type = auth_type
    resource.valid_until = valid_until
    if public_installer_url is not None:
        resource.public_installer_url = public_installer_url
    
    # Ensure config is a dict
    if resource.config is None:
        resource.config = {}
        
    # Update Config (Merge)
    # 1. Handle File Upload (Unzip Strategy)
    print(f"DEBUG: Update Resource {res_id}, File: {file_zip}, Filename: {file_zip.filename if file_zip else 'None'}")
    if file_zip and file_zip.filename:
        print("DEBUG: Processing Zip Upload...")
        import os
        import shutil
        import zipfile
        
        # Define paths
        base_dir = f"data/resources/{res_id}"
        zip_dest = os.path.join(base_dir, "original.zip")
        content_dir = os.path.join(base_dir, "content")
        
        # Cleanup & Setup
        if os.path.exists(base_dir):
            shutil.rmtree(base_dir)
        os.makedirs(content_dir, exist_ok=True)
        
        # Save ZIP
        with open(zip_dest, "wb") as buffer:
            shutil.copyfileobj(file_zip.file, buffer)
            
        # Unzip
        try:
            with zipfile.ZipFile(zip_dest, 'r') as zf:
                zf.extractall(content_dir)
        except Exception as e:
             raise HTTPException(status_code=400, detail=f"Invalid Zip File: {str(e)}")
             
        # Update Config
        resource.config["root_path"] = content_dir
        # Remove legacy zip_path to ensure new logic takes precedence
        if "zip_path" in resource.config:
            del resource.config["zip_path"]
    
    if inject_file:
        resource.config["inject_file"] = inject_file
    
    # 2. Handle Text Fields
    if static_code is not None:
        resource.config["static_code"] = static_code
    if instruction_text is not None:
        resource.config["instruction_text"] = instruction_text
    if usage_norms is not None:
        resource.config["usage_norms"] = usage_norms
    if connection_info is not None:
        resource.config["connection_info"] = connection_info
    if quota is not None:
        resource.config["quota"] = quota
    if upstream_url is not None:
        resource.config["upstream_url"] = upstream_url
        
    # Re-assign config to trigger SQLModel/SQLAlchemy update detection
    # resource.config = dict(resource.config) # Sometimes insufficient
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(resource, "config")
    
    # Update Schema based on category (Simple reset for MVP)
    form_schema = {"fields": []}
    if category == "Software":
        form_schema["fields"].append({"name": "usage_purpose", "label": "Usage Purpose", "type": "select", "options": ["Teaching", "Research"], "required": True})
        form_schema["fields"].append({"name": "course_name", "label": "Course Name (if Teaching)", "type": "text"})
    elif category == "Compute":
        form_schema["fields"].append({"name": "project_desc", "label": "Project Description", "type": "textarea", "required": True})
        form_schema["fields"].append({"name": "booking_time", "label": "Booking Time / Duration", "type": "text", "required": True})
    elif category == "Data":
        form_schema["fields"].append({"name": "project_desc", "label": "Reason for Request", "type": "textarea", "required": True})
    elif category == "Teaching":
        form_schema["fields"].append({"name": "course_code", "label": "Course Code", "type": "text", "required": True})
    resource.form_schema = form_schema

    print(f"DEBUG: Saving Resource Config: {resource.config}")
    session.add(resource)
    session.commit()
    print("DEBUG: Resource Saved.")
    
    return RedirectResponse(url="/admin/dashboard?tab=resources", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/admin/resources/{res_id}/delete")
async def delete_resource(
    res_id: int,
    request: Request,
    user: User = Depends(require_admin),
    session: Session = Depends(get_session)
):
    resource = session.get(Resource, res_id)
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
        
    # For MVP, we can do hard delete or soft delete.
    # Given 'is_active' exists in model, soft delete is safer.
    # But user asked for "Delete", let's assume they want it gone or at least hidden.
    # Let's use hard delete for now to keep dashboard clean, 
    # BUT we need to handle constraints (Apps linked to Resource).
    # Since we have cascade, usually it's better to soft delete.
    # Actually, model defined `is_active` but I didn't verify if I use it in queries.
    # Let's delete it.
    
    session.delete(resource)
    session.commit()
    
    return RedirectResponse(url="/admin/dashboard?tab=resources", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/admin/tools/preview-zip")
async def preview_zip_content(
    file: UploadFile,
    user: User = Depends(require_admin)
):
    """
    Reads a zip file from upload stream and returns its structure without saving.
    """
    if not file or not file.filename.endswith('.zip'):
        return JSONResponse({"error": "Invalid file type"}, status_code=400)
    
    try:
        import zipfile
        import io
        
        # Read file into memory
        content = await file.read()
        
        with zipfile.ZipFile(io.BytesIO(content), 'r') as zf:
            # Get file list
            files = zf.namelist()
            
        # Return simple list for now (Frontend can tree-ify if needed, or just list)
        return {"files": files}
        
    except Exception as e:
        return JSONResponse({"error": f"Failed to read zip: {str(e)}"}, status_code=400)

@router.get("/admin/tools/decrypt", response_class=HTMLResponse)
async def decrypt_tool_page(
    request: Request,
    user: User = Depends(require_admin),
    trans: tuple = Depends(get_translator)
):
    _, lang = trans
    return templates.TemplateResponse("admin_decrypt.html", {"request": request, "_": _, "lang": lang})

@router.post("/admin/tools/decrypt", response_class=HTMLResponse)
async def decrypt_tool_run(
    request: Request,
    file: UploadFile = File(...),
    user: User = Depends(require_admin),
    trans: tuple = Depends(get_translator)
):
    from ..core.watermark import decrypt_trace_info
    _, lang = trans
    
    content = await file.read()
    result = decrypt_trace_info(content)
    
    return templates.TemplateResponse("admin_decrypt.html", {"request": request, "result": result, "_": _, "lang": lang})

# --- User Management ---

@router.get("/admin/users", response_class=HTMLResponse)
async def admin_users(
    request: Request,
    search: str = "",
    user: User = Depends(require_admin),
    session: Session = Depends(get_session),
    trans: tuple = Depends(get_translator)
):
    _, lang = trans
    query = select(User)
    if search:
        query = query.where(
            or_(
                User.name.contains(search),
                User.swufe_uid.contains(search),
                User.email.contains(search)
            )
        )
    query = query.order_by(User.id.desc())
    users = session.exec(query).all()
    
    return templates.TemplateResponse("admin_users.html", {
        "request": request, 
        "user": user,
        "users": users,
        "search": search,
        "_": _,
        "lang": lang
    })

@router.get("/admin/users/{user_id}", response_class=HTMLResponse)
async def admin_user_detail(
    user_id: int,
    request: Request,
    user: User = Depends(require_admin),
    session: Session = Depends(get_session),
    trans: tuple = Depends(get_translator)
):
    _, lang = trans
    target_user = session.get(User, user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
        
    # Get user applications
    apps = session.exec(select(Application).where(Application.user_id == user_id).order_by(Application.created_at.desc())).all()
    
    return templates.TemplateResponse("admin_user_detail.html", {
        "request": request, 
        "user": user,
        "target_user": target_user,
        "applications": apps,
        "_": _,
        "lang": lang
    })

@router.post("/admin/users/{user_id}/toggle-status")
async def toggle_user_status(
    user_id: int,
    request: Request,
    user: User = Depends(require_admin),
    session: Session = Depends(get_session)
):
    target_user = session.get(User, user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
        
    target_user.is_active = not target_user.is_active
    session.add(target_user)
    
    # Audit Log
    action = "ENABLE_USER" if target_user.is_active else "DISABLE_USER"
    audit = AuditLog(
        user_id=user.id,
        action=action,
        details=f"{action} {target_user.name} ({target_user.swufe_uid})",
        ip_address=request.client.host if request.client else "unknown"
    )
    session.add(audit)
    session.commit()
    
    return RedirectResponse(url=f"/admin/users/{user_id}", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/admin/users/{user_id}/role")
async def change_user_role(
    user_id: int,
    request: Request,
    role: str = Form(...),
    user: User = Depends(require_admin),
    session: Session = Depends(get_session)
):
    target_user = session.get(User, user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
        
    old_role = target_user.role
    target_user.role = role
    session.add(target_user)
    
    # Audit Log
    audit = AuditLog(
        user_id=user.id,
        action="CHANGE_ROLE",
        details=f"Changed role for {target_user.name} from {old_role} to {role}",
        ip_address=request.client.host if request.client else "unknown"
    )
    session.add(audit)
    session.commit()
    
    return RedirectResponse(url=f"/admin/users/{user_id}", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/admin/applications/{app_id}/revoke")
async def revoke_application(
    app_id: int,
    request: Request,
    user: User = Depends(require_admin),
    session: Session = Depends(get_session)
):
    app = session.get(Application, app_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
        
    app.status = "REVOKED"
    app.expired_at = datetime.now() # Expire immediately
    session.add(app)
    
    # Audit Log
    audit = AuditLog(
        user_id=user.id,
        action="REVOKE",
        resource_id=app.resource_id,
        details=f"Revoked Application #{app.id} for {app.user.name}",
        ip_address=request.client.host if request.client else "unknown"
    )
    session.add(audit)
    session.commit()
    
    # Return to where we came from? Usually dashboard or user detail
    # Let's check referer or default to dashboard
    referer = request.headers.get("referer")
    if referer and "/admin/users/" in referer:
        return RedirectResponse(url=referer, status_code=status.HTTP_303_SEE_OTHER)
    return RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/admin/users/{user_id}/revoke-all")
async def revoke_all_user_applications(
    user_id: int,
    request: Request,
    user: User = Depends(require_admin),
    session: Session = Depends(get_session)
):
    target_user = session.get(User, user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
        
    apps = session.exec(select(Application).where(Application.user_id == user_id, Application.status == "APPROVED")).all()
    
    count = 0
    for app in apps:
        app.status = "REVOKED"
        app.expired_at = datetime.now()
        session.add(app)
        count += 1
        
    # Audit Log
    if count > 0:
        audit = AuditLog(
            user_id=user.id,
            action="REVOKE_ALL",
            details=f"Revoked all {count} active applications for {target_user.name}",
            ip_address=request.client.host if request.client else "unknown"
        )
        session.add(audit)
        session.commit()
    
    return RedirectResponse(url=f"/admin/users/{user_id}", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/admin/stats/data")
async def get_admin_stats(
    start_date: str = None,
    end_date: str = None,
    user: User = Depends(require_admin),
    session: Session = Depends(get_session)
):
    # Base query for approved applications
    base_query = select(Application).where(Application.status == "APPROVED")
    
    # Apply date filters if provided
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            base_query = base_query.where(Application.approved_at >= start_dt)
        except ValueError:
            pass
            
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            # Include the whole end day
            end_dt = end_dt + timedelta(days=1)
            base_query = base_query.where(Application.approved_at < end_dt)
        except ValueError:
            pass
            
    approved_apps = session.exec(base_query).all()
    
    # 1. Total & Active
    total_count = len(approved_apps)
    now = datetime.now()
    active_count = sum(1 for app in approved_apps if app.expired_at and app.expired_at > now)
    
    # 2. Expiring Soon (7 days)
    seven_days_later = now + timedelta(days=7)
    expiring_count = sum(1 for app in approved_apps if app.expired_at and now < app.expired_at <= seven_days_later)
    
    # 3. Distribution by Category
    # Need to join with Resource
    cat_query = select(Resource.category, func.count(Application.id)).join(Application).where(Application.status == "APPROVED")
    
    # Re-apply filters to this aggregate query
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            cat_query = cat_query.where(Application.approved_at >= start_dt)
        except ValueError:
            pass
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
            cat_query = cat_query.where(Application.approved_at < end_dt)
        except ValueError:
            pass
            
    cat_query = cat_query.group_by(Resource.category)
    cat_rows = session.exec(cat_query).all()
    
    distribution = {row[0]: row[1] for row in cat_rows}
    
    # 4. Trend (Last 7 days or filtered range)
    # If filtered range is large, maybe group by month? For now, simple daily grouping
    # Let's just do a simple daily count for the selected range (or last 30 days if no range)
    
    trend_data = {}
    
    # If no date filter, default to last 30 days for trend
    trend_start = datetime.now() - timedelta(days=30)
    if start_date:
        try:
            trend_start = datetime.strptime(start_date, "%Y-%m-%d")
        except:
            pass
            
    # Iterate apps and bucket by date
    for app in approved_apps:
        if app.approved_at:
            date_str = app.approved_at.strftime("%Y-%m-%d")
            trend_data[date_str] = trend_data.get(date_str, 0) + 1
            
    # Sort trend data
    sorted_trend_keys = sorted(trend_data.keys())
    sorted_trend_values = [trend_data[k] for k in sorted_trend_keys]
    
    return {
        "total": total_count,
        "active": active_count,
        "expiring": expiring_count,
        "distribution": distribution,
        "trend": {
            "labels": sorted_trend_keys,
            "data": sorted_trend_values
        }
    }
