import os
import uuid
from fastapi import UploadFile
from app.core.config import settings
from app.core.errors import InvalidAudioException, FileTooLargeException

SUPPORTED_EXTENSIONS = {".mp3", ".wav", ".m4a", ".mp4", ".ogg", ".webm"}

def validate_audio_file(file: UploadFile):
    """Validate audio file format and size headers."""
    if not file.filename:
        raise InvalidAudioException("Upload filename is missing.")
        
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise InvalidAudioException(f"Unsupported audio format. Supported extensions: {', '.join(SUPPORTED_EXTENSIONS)}")

    # Check file size attribute if present in UploadFile (FastAPI/Starlette feature)
    file_size_bytes = getattr(file, "size", None)
    max_size_bytes = settings.MAX_AUDIO_SIZE_MB * 1024 * 1024
    if file_size_bytes is not None and file_size_bytes > max_size_bytes:
        raise FileTooLargeException(f"File size exceeds the maximum limit of {settings.MAX_AUDIO_SIZE_MB} MB.")

def save_temp_audio(file: UploadFile) -> str:
    """Save upload stream to a safe temporary location, validating size dynamically."""
    validate_audio_file(file)
    
    ext = os.path.splitext(file.filename)[1].lower()
    # Store temp files in the backend/scratch/ directory or project scratch
    temp_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../scratch/temp_audio"))
    os.makedirs(temp_dir, exist_ok=True)
    
    temp_path = os.path.join(temp_dir, f"{uuid.uuid4()}{ext}")
    max_size_bytes = settings.MAX_AUDIO_SIZE_MB * 1024 * 1024
    written_bytes = 0
    
    try:
        file.file.seek(0)
        with open(temp_path, "wb") as buffer:
            while True:
                # Read in 1MB chunks
                chunk = file.file.read(1024 * 1024)
                if not chunk:
                    break
                written_bytes += len(chunk)
                if written_bytes > max_size_bytes:
                    raise FileTooLargeException(f"File size exceeds the limit of {settings.MAX_AUDIO_SIZE_MB} MB.")
                buffer.write(chunk)
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise e
        
    return temp_path

def delete_temp_audio(temp_path: str):
    """Safely delete the temporary audio file."""
    if temp_path and os.path.exists(temp_path):
        try:
            os.remove(temp_path)
        except Exception:
            pass
