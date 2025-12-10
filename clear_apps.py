from sqlmodel import Session, create_engine, select, delete
from backend.models import Application

# Adjust path if necessary, assuming running from project root
sqlite_url = "sqlite:///data/database.db"
engine = create_engine(sqlite_url)

try:
    with Session(engine) as session:
        statement = delete(Application)
        result = session.exec(statement)
        session.commit()
        print(f"Successfully deleted {result.rowcount} application records.")
except Exception as e:
    print(f"Error deleting records: {e}")
