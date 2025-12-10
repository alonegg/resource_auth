import os
import sys
# Add backend to path to allow imports
sys.path.append(os.getcwd())

from backend.core.watermark import stream_zip_from_directory

# Mock Data
dir_path = "data/resources/1/content"
user_info = {
    "id": 1,
    "name": "Test User",
    "username": "testuser",
    "dept": "IT",
    "apply_time": "2024-01-01T12:00:00",
    "apply_id": 1
}

print(f"Testing stream from: {dir_path}")
if not os.path.exists(dir_path):
    print("Directory does not exist!")
    sys.exit(1)

try:
    generator = stream_zip_from_directory(dir_path, user_info, "licence.dat")
    count = 0
    total_bytes = 0
    for chunk in generator:
        count += 1
        total_bytes += len(chunk)
        print(f"Chunk {count}: {len(chunk)} bytes")
    print("Success!")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
