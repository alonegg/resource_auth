from datetime import datetime, date
from typing import Optional, Dict, List, Any
from sqlmodel import SQLModel, Field, JSON, Relationship

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    swufe_uid: str = Field(index=True, unique=True) # 学工号
    password_hash: str # New: Store hashed password
    name: str
    email: str
    phone: Optional[str] = None
    department: str # 学院
    role: str = "user" # user, admin: bool = Field(default=False)
    is_active: bool = Field(default=True)
    
    applications: List["Application"] = Relationship(back_populates="user")

class Resource(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    category: str # "Software", "Compute", "API", "Data"
    auth_type: str # 'AUTO_ZIP', 'MANUAL', 'API_GATEWAY'
    
    # Dynamic Form Configuration
    # e.g. {"fields": [{"name": "usage", "label": "Usage", "type": "text", "required": true}]}
    form_schema: Dict[str, Any] = Field(default={}, sa_type=JSON)
    
    # Level 1: Public Installer
    public_installer_url: Optional[str] = None 
    description: str = Field(default="")
    
    # Lifecycle
    valid_until: Optional[date] = None # Replaces default_duration_days

    # Configuration Payload (Type-specific)
    # Type A: {"zip_path": "...", "inject_file": "setup.dat"}
    config: Dict[str, Any] = Field(default={}, sa_type=JSON)
    
    is_active: bool = Field(default=True)

    applications: List["Application"] = Relationship(back_populates="resource")

class Application(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    resource_id: int = Field(foreign_key="resource.id")
    
    status: str = Field(default="PENDING") # PENDING, APPROVED, REJECTED, REVOKED, EXPIRED
    
    # Lifecycle
    approved_at: Optional[datetime] = None
    expired_at: Optional[datetime] = None
    
    # User submission (e.g. usage description)
    user_input: Dict[str, Any] = Field(default={}, sa_type=JSON)
    
    # Result (Trace UUID, API Key, etc.)
    auth_output: Dict[str, Any] = Field(default={}, sa_type=JSON)
    
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now) # Handled in logic

    user: Optional[User] = Relationship(back_populates="applications")
    resource: Optional[Resource] = Relationship(back_populates="applications")

class AuditLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int
    action: str # 'APPLY', 'APPROVE', 'DOWNLOAD', 'REVOKE'
    resource_id: Optional[int] = None
    ip_address: str
    details: str
    timestamp: datetime = Field(default_factory=datetime.now)
