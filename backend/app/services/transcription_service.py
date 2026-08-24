import logging
from groq import Groq
from app.core.config import settings
from app.core.errors import TranscriptionFailedException

logger = logging.getLogger("meeting_summarizer")

def transcribe_audio(audio_path: str) -> str:
    """Send local audio file to Groq Whisper API for transcription."""
    if not settings.GROQ_API_KEY or settings.GROQ_API_KEY == "mock-key-for-local-testing":
        # Check if we are running in tests or local mock environment
        logger.warning("No valid Groq API key configured. Returning mock transcription.")
        return "Alice: We will launch on September 10. Bob: I'll prepare the deployment guide by Friday. Charlie: We still need to decide which payment provider to use."

    try:
        client = Groq(api_key=settings.GROQ_API_KEY)
        with open(audio_path, "rb") as audio_file:
            response = client.audio.transcriptions.create(
                model=settings.GROQ_TRANSCRIPTION_MODEL,
                file=audio_file
            )
        return response.text
    except Exception as e:
        logger.error(f"Groq ASR transcription call failed: {e}", exc_info=True)
        raise TranscriptionFailedException(f"Transcription failed: {str(e)}")
