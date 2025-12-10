import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine, select
from backend.main import app
from backend.database import get_session
from backend.models import User, Resource
from backend.auth import get_current_user, get_current_user_optional, require_admin

from sqlalchemy.pool import StaticPool

# Use in-memory database for testing
sqlite_url = "sqlite://" # Use shared memory url
engine = create_engine(
    sqlite_url, 
    connect_args={"check_same_thread": False}, 
    poolclass=StaticPool
)

@pytest.fixture(name="session")
def session_fixture():
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)

@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    
    # We will override auth per test or here if we want a default user
    # For now, let's just override session
    
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()

@pytest.fixture(name="test_user")
def test_user_fixture(session: Session):
    user = User(
        swufe_uid="20230001",
        password_hash="hashed",
        name="Test Student",
        email="test@swufe.edu.cn",
        department="CS",
        role="user",
        phone="13800000000"
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user

@pytest.fixture(name="admin_user")
def admin_user_fixture(session: Session):
    user = User(
        swufe_uid="admin",
        password_hash="hashed",
        name="Admin User",
        email="admin@swufe.edu.cn",
        department="IT",
        role="admin",
        phone="13800000001"
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user

@pytest.fixture(name="auth_headers")
def auth_headers_fixture(client, test_user):
    # Since we use cookies in real app, but here we can mock dependency.
    # But to test the endpoints that depend on `get_current_user`, 
    # we should override the dependency.
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_current_user_optional] = lambda: test_user
    return {}

@pytest.fixture(name="admin_headers")
def admin_headers_fixture(client, admin_user):
    app.dependency_overrides[get_current_user] = lambda: admin_user
    app.dependency_overrides[get_current_user_optional] = lambda: admin_user
    app.dependency_overrides[require_admin] = lambda: admin_user
    return {}
