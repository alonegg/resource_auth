import sys
import os
import zipfile
from sqlmodel import Session, select, create_engine
from datetime import datetime, date
from passlib.context import CryptContext

# Add root to path
sys.path.append(os.getcwd())

from backend.models import Resource, User
from backend.database import engine, create_db_and_tables
from backend.auth import get_password_hash

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_dummy_zip():
    if not os.path.exists("files"):
        os.makedirs("files")
    
    zip_path = "files/sas_installer.zip"
    if not os.path.exists(zip_path):
        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.writestr('README.txt', 'This is the original installer content.')
        print(f"Created dummy zip at {zip_path}")
    return os.path.abspath(zip_path)

def seed_db():
    # Remove existing db to force re-seed with new schema
    if os.path.exists("data/database.db"):
        os.remove("data/database.db")
        
    create_db_and_tables()
    
    with Session(engine) as session:
        zip_abs_path = create_dummy_zip()
        
        # 1. Software Resources (软件资源)
        sas = Resource(
            name="SAS Studio 2024",
            category="Software",
            auth_type="AUTO_ZIP",
            description="Statistical Analysis System. Auto-approved.",
            valid_until=date(2025, 12, 31),
            public_installer_url="http://cdn.edu/sas_installer.iso",
            form_schema={
                "fields": [
                    {"name": "usage_purpose", "label": "Usage Purpose", "type": "select", "options": ["Teaching", "Research"], "required": True}
                ]
            },
            config={"zip_path": zip_abs_path, "inject_file": "license.dat"}
        )
        session.add(sas)

        stata = Resource(
            name="Stata 17",
            category="Software",
            auth_type="MANUAL",
            description="Data Science Tool",
            valid_until=date(2025, 6, 30),
            form_schema={
                "fields": [
                    {"name": "usage_purpose", "label": "Usage Purpose", "type": "select", "options": ["Teaching", "Research"], "required": True}
                ]
            },
            config={"static_code": "STATA-KEY-12345-ABCD"}
        )
        session.add(stata)

        matlab = Resource(
            name="Matlab 2024b",
            category="Software",
            auth_type="MANUAL",
            description="Numerical Computing Platform",
            valid_until=date(2025, 12, 31),
             form_schema={
                "fields": [
                    {"name": "usage_purpose", "label": "Usage Purpose", "type": "select", "options": ["Teaching", "Research"], "required": True}
                ]
            },
            config={"instruction_text": "1. Go to mathworks.com\n2. Sign in with school email (@swufe.edu.cn)\n3. Download installer."}
        )
        session.add(matlab)
        
        # 2. Compute Resources (计算资源)
        dslab = Resource(
            name="DSLAB GPU Cluster",
            category="Compute",
            auth_type="MANUAL",
            description="NVIDIA A100 Cluster. Requires booking approval.",
            valid_until=date(2025, 12, 31),
            form_schema={
                "fields": [
                    {"name": "booking_time", "label": "Booking Slot (YYYY-MM-DD HH:MM)", "type": "text", "required": True},
                    {"name": "project_desc", "label": "Project Description", "type": "textarea", "required": True}
                ]
            },
            config={}
        )
        session.add(dslab)
        
        # 3. Data Resources (数据资源)
        wind = Resource(
            name="Wind Financial Data",
            category="Data",
            auth_type="MANUAL",
            description="Financial Data Terminal Access.",
            valid_until=date(2025, 12, 31),
            form_schema={
                "fields": [
                    {"name": "data_type", "label": "Data Types Needed", "type": "text", "required": True},
                    {"name": "project_desc", "label": "Reason for Request", "type": "textarea", "required": True}
                ]
            },
            config={}
        )
        session.add(wind)

        # 4. Teaching Resources (教学资源)
        course_ai = Resource(
            name="AI Course Platform",
            category="Teaching", 
            description="AI Assisted Teaching Service",
            auth_type="MANUAL",
            valid_until=date(2025, 12, 31),
            form_schema={"fields": [{"name": "course_code", "label": "Course Code", "type": "text", "required": True}]},
            config={}
        )
        session.add(course_ai)
        
        # 6. Create Admin User
        admin_pwd = get_password_hash("admin123")
        admin = User(
            swufe_uid="admin",
            password_hash=admin_pwd,
            name="System Admin",
            department="IT Center",
            phone="000",
            email="admin@swufe.edu.cn",
            role="admin"
        )
        session.add(admin)
        
        session.commit()
        print("Seeded Database with Resources and Admin User.")

if __name__ == "__main__":
    seed_db()
