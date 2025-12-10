import os
import io
import zipfile
import json
import pytest
from backend.core.watermark import stream_zip_from_directory, decrypt_trace_info, cipher

def test_encryption_roundtrip():
    """Test that data can be encrypted and decrypted correctly."""
    data = {"uid": 123, "name": "Test User"}
    json_bytes = json.dumps(data).encode('utf-8')
    encrypted = cipher.encrypt(json_bytes)
    
    decrypted = cipher.decrypt(encrypted)
    assert json.loads(decrypted) == data

def test_decrypt_trace_info():
    """Test the helper function."""
    data = {"uid": 456, "username": "testuser"}
    json_bytes = json.dumps(data).encode('utf-8')
    encrypted = cipher.encrypt(json_bytes)
    
    result = decrypt_trace_info(encrypted)
    assert result == data

def test_stream_zip_injection(tmp_path):
    """Test that the zip stream contains the injected file and original files."""
    # 1. Create a dummy directory with a file
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    (source_dir / "test.txt").write_text("hello world")
    
    user_info = {
        "id": 1,
        "name": "Alice",
        "username": "alice123",
        "dept": "CS",
        "apply_time": "2023-01-01",
        "apply_id": 99
    }
    
    # 2. Generate Zip
    stream = stream_zip_from_directory(str(source_dir), user_info, "license.key")
    
    # Consume generator
    zip_content = b"".join(stream)
    
    # 3. Verify Zip Content
    with zipfile.ZipFile(io.BytesIO(zip_content), 'r') as zf:
        # Check files exist
        assert "test.txt" in zf.namelist()
        assert "license.key" in zf.namelist()
        
        # Verify original content
        assert zf.read("test.txt").decode() == "hello world"
        
        # Verify injected content
        encrypted_data = zf.read("license.key")
        decrypted_info = decrypt_trace_info(encrypted_data)
        
        assert decrypted_info["uid"] == 1
        assert decrypted_info["username"] == "alice123"
