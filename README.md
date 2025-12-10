# E-TRAP (Experimental Teaching Resource Authorization Platform)

## Overview
E-TRAP is a centralized portal for managing authorizations to experimental teaching resources, including Commercial Software, Computing Power, Data Services, and APIs.

## Key Features
- **Unified Catalog**: Browse and search resources by category.
- **Dynamic Applications**: Forms adapt based on resource type (e.g. Software vs Compute).
- **Automated workflows**: Auto-injection of watermarks for software downloads.
- **Admin Dashboard**: Manage approvals, resource configurations, and view analytics.
- **i18n Support**: Full English and Chinese (Simplified) interface support.

## Getting Started

### Prerequisites
- Python 3.11+
- SQLite (Built-in)

### Installation
1.  Clone the repository.
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
3.  Seed the database (Initial Admin: `admin`/`admin123`):
    ```bash
    python scripts/seed_data.py
    ```

### Running the Server
Use the helper script:
```bash
./run.sh
```
Or manually:
```bash
uvicorn backend.main:app --reload
```

### Access Points
- **Student Portal**: [http://127.0.0.1:8000/resource](http://127.0.0.1:8000/resource)
- **Admin Dashboard**: [http://127.0.0.1:8000/admin](http://127.0.0.1:8000/admin) (Login required)

## Internationalization (i18n)
- The platform automatically detects language preference.
- Use the Switcher in the top navigation bar to toggle between **English** and **Chinese**.
- Keys are managed in `backend/core/i18n.py`.

## Security Note
- **Dev Mode**: The current setup uses a static SECRET_KEY and dev-mode login.
- **Production**: Please update `backend/auth.py` and environment variables for production deployment.
