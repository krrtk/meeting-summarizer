from fastapi import Request
from fastapi.responses import JSONResponse

class AppException(Exception):
    """Base application exception for standardized error contract."""
    def __init__(self, status_code: int, code: str, message: str):
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(message)


class InvalidAudioException(AppException):
    def __init__(self, message: str = "Unsupported audio format."):
        super().__init__(status_code=400, code="INVALID_AUDIO", message=message)


class FileTooLargeException(AppException):
    def __init__(self, message: str = "File is too large."):
        super().__init__(status_code=400, code="FILE_TOO_LARGE", message=message)


class TranscriptionFailedException(AppException):
    def __init__(self, message: str = "Transcription failed."):
        super().__init__(status_code=500, code="TRANSCRIPTION_FAILED", message=message)


class LLMFailedException(AppException):
    def __init__(self, message: str = "LLM analysis failed."):
        super().__init__(status_code=500, code="LLM_FAILED", message=message)


class InvalidLLMOutputException(AppException):
    def __init__(self, message: str = "Invalid structured intelligence output from AI."):
        super().__init__(status_code=500, code="INVALID_LLM_OUTPUT", message=message)


class MeetingNotFoundException(AppException):
    def __init__(self, message: str = "Meeting not found."):
        super().__init__(status_code=404, code="MEETING_NOT_FOUND", message=message)


class ProcessingFailedException(AppException):
    def __init__(self, message: str = "Meeting processing failed."):
        super().__init__(status_code=500, code="PROCESSING_FAILED", message=message)


async def app_exception_handler(request: Request, exc: AppException):
    """FastAPI handler to format AppException into standard JSON error contract."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": {
                "code": exc.code,
                "message": exc.message
            }
        }
    )
