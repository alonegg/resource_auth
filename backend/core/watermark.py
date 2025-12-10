import zipfile
import io
import json
import os
from datetime import datetime
from cryptography.fernet import Fernet
from typing import Dict, Any

# Fixed Key for MVP Persistence
SECRET_KEY = b'aXEs6JY2iuIhZ3JNRkK-Wk5H91ctRTjwRPh7lFhX07E=' 
cipher = Fernet(SECRET_KEY)

class UnseekableStream:
    def __init__(self, stream):
        self.stream = stream
    
    def write(self, data):
        return self.stream.write(data)
        
    def flush(self):
        self.stream.flush()
        
    def tell(self):
        raise io.UnsupportedOperation("not seekable")
        
    def seek(self, offset, whence=0):
        raise io.UnsupportedOperation("not seekable")

    def close(self):
        pass

def stream_zip_from_directory(dir_path: str, user_info: Dict[str, Any], fake_filename: str = "licence.dat"):
    """
    Generator that creates a zip stream from a directory, injecting the license file.
    """
    if not os.path.exists(dir_path):
        raise FileNotFoundError(f"Source directory not found: {dir_path}")

    # 1. Prepare payload (License Data)
    trace_data = {
        "uid": user_info.get('id'),
        "name": user_info.get('name'),
        "username": user_info.get('username'), # swufe_uid
        "dept": user_info.get('dept'),
        "timestamp": datetime.now().isoformat(),
        "apply_time": user_info.get('apply_time'),
        "apply_id": user_info.get('apply_id', 'N/A')
    }
    
    # 2. Encrypt
    json_bytes = json.dumps(trace_data).encode('utf-8')
    encrypted_bytes = cipher.encrypt(json_bytes)
    
    # 3. Stream Zip Generation
    zip_buffer = io.BytesIO()
    wrapped_buffer = UnseekableStream(zip_buffer)
    compression = zipfile.ZIP_DEFLATED if 'zlib' in zipfile.__all__ else zipfile.ZIP_STORED
    
    with zipfile.ZipFile(wrapped_buffer, "w", compression) as zf:
        # A. Add Injected File
        info = zipfile.ZipInfo(fake_filename)
        info.date_time = datetime.now().timetuple()[:6]
        zf.writestr(info, encrypted_bytes)
        
        # Flush buffer
        zip_buffer.seek(0)
        yield zip_buffer.read()
        zip_buffer.seek(0)
        zip_buffer.truncate(0)
        
        # B. Walk Directory and Add Files
        for root, dirs, files in os.walk(dir_path):
            for file in files:
                file_path = os.path.join(root, file)
                # Calculate archive name (relative to dir_path)
                arcname = os.path.relpath(file_path, dir_path)
                
                # Write file to zip
                zf.write(file_path, arcname)
                
                # Flush buffer (Simulate streaming)
                zip_buffer.seek(0)
                yield zip_buffer.read()
                zip_buffer.seek(0)
                zip_buffer.truncate(0)
                
    # C. Central Directory (Written on exit)
    zip_buffer.seek(0)
    yield zip_buffer.read()

def stream_zip_from_zip_file(source_zip_path: str, user_info: Dict[str, Any], fake_filename: str = "licence.dat"):
    """
    Legacy Support: Generator that reads from an existing zip file and injects the license file.
    Efficiently streams content without fully unzipping to disk.
    """
    if not os.path.exists(source_zip_path):
        raise FileNotFoundError(f"Source zip not found: {source_zip_path}")

    # 1. Prepare payload
    trace_data = {
        "uid": user_info.get('id'),
        "name": user_info.get('name'),
        "username": user_info.get('username'),
        "dept": user_info.get('dept'),
        "timestamp": datetime.now().isoformat(),
        "apply_time": user_info.get('apply_time'),
        "apply_id": user_info.get('apply_id', 'N/A')
    }
    
    json_bytes = json.dumps(trace_data).encode('utf-8')
    encrypted_bytes = cipher.encrypt(json_bytes)
    
    # 2. Stream Zip Generation
    zip_buffer = io.BytesIO()
    wrapped_buffer = UnseekableStream(zip_buffer)
    # Use ZIP_STORED for speed if re-compressing is too slow, but DEFLATED is better for size.
    # Since we are reading compressed data, re-compressing might be slow. 
    # But standard ZipFile.read() returns bytes. 
    # To avoid re-compression, we would need low-level copy, which python zipfile doesn't easily support for streaming.
    # So we re-compress.
    compression = zipfile.ZIP_DEFLATED if 'zlib' in zipfile.__all__ else zipfile.ZIP_STORED
    
    with zipfile.ZipFile(source_zip_path, 'r') as source_zf:
        with zipfile.ZipFile(wrapped_buffer, "w", compression) as dest_zf:
            # A. Add Injected File
            info = zipfile.ZipInfo(fake_filename)
            info.date_time = datetime.now().timetuple()[:6]
            dest_zf.writestr(info, encrypted_bytes)
            
            zip_buffer.seek(0)
            yield zip_buffer.read()
            zip_buffer.seek(0)
            zip_buffer.truncate(0)
            
            # B. Copy Files
            for item in source_zf.infolist():
                # Read from source (decompressed)
                content = source_zf.read(item.filename)
                # Write to dest (re-compressed)
                dest_zf.writestr(item, content)
                
                zip_buffer.seek(0)
                yield zip_buffer.read()
                zip_buffer.seek(0)
                zip_buffer.truncate(0)
                
    # C. Finalize
    zip_buffer.seek(0)
    yield zip_buffer.read()

def decrypt_trace_info(encrypted_data: bytes) -> Dict[str, Any]:
    """Helper to verify content"""
    try:
        decrypted = cipher.decrypt(encrypted_data)
        return json.loads(decrypted)
    except Exception as e:
        return {"error": str(e)}
