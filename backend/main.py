from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os

from .database import create_db_and_tables

# Lifespan event to create tables on startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure data dir exists
    if not os.path.exists("data"):
        os.makedirs("data")
    create_db_and_tables()
    yield

app = FastAPI(title="Experimental Teaching Resource Authorization Platform", version="2.0", lifespan=lifespan)

# Templates
templates = Jinja2Templates(directory="backend/templates")

from fastapi import Response
from fastapi.responses import RedirectResponse

@app.get("/set-language/{lang}")
def set_language(lang: str, response: Response, next_url: str = "/"):
    if lang not in ["zh", "en"]:
        lang = "zh"
    
    redirect_url = next_url if next_url else "/"
    resp = RedirectResponse(url=redirect_url, status_code=302)
    resp.set_cookie(key="lang", value=lang, max_age=31536000) # 1 year
    return resp

# Register Routers
from backend.routers import auth, resources, admin, sso

app.include_router(auth.router)
app.include_router(sso.router)
app.include_router(resources.router)
app.include_router(admin.router)

@app.get("/")
async def root():
    return {"message": "Welcome to Experimental Teaching Resource Authorization Platform v2.0"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
