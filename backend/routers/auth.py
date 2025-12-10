from fastapi import APIRouter, Depends, HTTPException, status, Request, Response, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlmodel import Session, select
from backend.database import get_session
from backend.models import User
from backend.auth import get_current_user, get_password_hash, verify_password
from backend.core.i18n import get_translator
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="backend/templates")

@router.get("/login", response_class=HTMLResponse)
async def login_page(
    request: Request,
    trans: tuple = Depends(get_translator)
):
    _, lang = trans
    return templates.TemplateResponse("login.html", {"request": request, "_": _, "lang": lang})

@router.post("/login")
async def login(
    response: Response,
    swufe_uid: str = Form(...),
    password: str = Form(...),
    session: Session = Depends(get_session)
):
    user = session.exec(select(User).where(User.swufe_uid == swufe_uid)).first()
    if not user or not verify_password(password, user.password_hash):
        # In a real app return error message to template
        return Response(content="Invalid credentials", status_code=400)
    
    # Simple Cookie Auth
    response = RedirectResponse(url="/resource", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(key="user_id", value=str(user.id))
    return response

@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/login")
    response.delete_cookie("user_id")
    return response

@router.get("/register", response_class=HTMLResponse)
async def register_page(
    request: Request,
    trans: tuple = Depends(get_translator)
):
    _, lang = trans
    return templates.TemplateResponse("register.html", {"request": request, "_": _, "lang": lang})

@router.post("/register")
async def register(
    swufe_uid: str = Form(...),
    password: str = Form(...),
    name: str = Form(...),
    department: str = Form(...),
    phone: str = Form(...),
    email: str = Form(...),
    session: Session = Depends(get_session)
):
    existing = session.exec(select(User).where(User.swufe_uid == swufe_uid)).first()
    if existing:
        return Response(content="User already exists", status_code=400)
    
    hashed_pwd = get_password_hash(password)
    user = User(
        swufe_uid=swufe_uid,
        password_hash=hashed_pwd,
        name=name,
        department=department,
        phone=phone,
        email=email,
        role="user"
    )
    session.add(user)
    session.commit()
    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/profile/complete", response_class=HTMLResponse)
async def profile_page(
    request: Request, 
    user: User = Depends(get_current_user),
    trans: tuple = Depends(get_translator)
):
    if not user:
        return RedirectResponse(url="/login")
    _, lang = trans
    return templates.TemplateResponse("profile.html", {"request": request, "user": user, "_": _, "lang": lang})

@router.post("/profile/complete")
async def complete_profile(
    email: str = Form(...),
    phone: str = Form(...),
    name: str = Form(...),
    department: str = Form(...),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user.email = email
    user.phone = phone
    user.name = name
    user.department = department
    session.add(user)
    session.commit()
    
    return RedirectResponse(url="/resource", status_code=status.HTTP_303_SEE_OTHER)
