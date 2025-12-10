from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.responses import RedirectResponse
from sqlmodel import Session, select
from datetime import datetime

from ..database import get_session
from ..models import User
from ..core.cas_client import CASClient
from ..auth import create_access_token, COOKIE_NAME

router = APIRouter()

# CAS Configuration - Hardcoded for MVP based on doc
CAS_SERVER_URL = "https://authserver.swufe.edu.cn/authserver"
cas_client = CASClient(CAS_SERVER_URL)

@router.get("/login/sso")
async def sso_login(
    request: Request,
    next_url: str = "/",
):
    """
    Handle CAS Login Redirect:
    Redirects to CAS with the strict service URL: http://192.168.77.87/resource
    The CAS server will redirect back to that URL with a ticket.
    """
    # STRICT Service URL for School CAS
    service_url = "http://192.168.77.87/resource"
    
    # Store next_url in session or cookie if needed to redirect after /resource?ticket=... 
    # But for MVP, we just land on /resource.
    
    return RedirectResponse(cas_client.get_login_url(service_url))

@router.get("/logout/sso")
async def sso_logout(request: Request):
    """
    Logout locally and from CAS.
    """
    # STRICT Service URL for School CAS Logout Callback
    service_url = "http://192.168.77.87/resource"
    
    redirect_url = cas_client.get_logout_url(service_url)
    response = RedirectResponse(redirect_url)
    response.delete_cookie(COOKIE_NAME)
    return response
