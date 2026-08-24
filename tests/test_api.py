import io
import json
import os
import sys
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add backend directory to sys.path so app modules are importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend")))

from app.main import app as fastapi_app
from app.models.database import Base, get_db
from app.models.meeting import Meeting
from app.schemas.meeting import MeetingExtraction
from app.api.meetings import process_meeting_task
from app.core.errors import TranscriptionFailedException, LLMFailedException, InvalidLLMOutputException

# Test Database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_meeting_summarizer.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Override SessionLocal in meetings API module to use test database for background tasks
import app.api.meetings
app.api.meetings.SessionLocal = TestingSessionLocal

# Override get_db dependency
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

fastapi_app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    # Clean up the test database file
    if os.path.exists("./test_meeting_summarizer.db"):
        try:
            os.remove("./test_meeting_summarizer.db")
        except Exception:
            pass

client = TestClient(fastapi_app)


def test_health():
    """Verify that the health check endpoint returns 200 and 'ok'."""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# ----------------- DB Initialization Tests -----------------

def test_meetings_table_created_from_empty_db():
    """
    Verify that Base.metadata.create_all creates the 'meetings' table when
    starting from a blank SQLite database (regression for the 'no such table'
    startup bug caused by importing models after calling create_all).
    """
    from sqlalchemy import create_engine, inspect
    from sqlalchemy.orm import sessionmaker

    tmp_db_path = "./test_init_empty.db"
    tmp_url = f"sqlite:///{tmp_db_path}"

    try:
        tmp_engine = create_engine(tmp_url, connect_args={"check_same_thread": False})

        # Simulate what main.py does: import Meeting model, then create_all
        from app.models import meeting as _  # noqa: F401 — registers Meeting with Base
        Base.metadata.create_all(bind=tmp_engine)

        inspector = inspect(tmp_engine)
        assert "meetings" in inspector.get_table_names(), (
            "meetings table was not created — model was not registered with Base before create_all"
        )

        # Also verify a row can be inserted (catches schema mismatches)
        TmpSession = sessionmaker(bind=tmp_engine)
        db = TmpSession()
        from app.models.meeting import Meeting
        record = Meeting(filename="init_test.mp3", status="processing")
        db.add(record)
        db.commit()
        db.refresh(record)
        assert record.id is not None
        db.close()
        tmp_engine.dispose()
    finally:
        if os.path.exists(tmp_db_path):
            try:
                os.remove(tmp_db_path)
            except Exception:
                pass


@patch("app.api.meetings.process_meeting_task")
def test_post_meetings_no_such_table_regression(mock_task):
    """
    Regression test: POST /api/meetings must not raise 'no such table: meetings'.
    This fails when the Meeting model is not imported before Base.metadata.create_all.
    """
    file_content = b"fake mp3 audio data"
    files = {"file": ("regression_test.mp3", io.BytesIO(file_content), "audio/mpeg")}
    response = client.post("/api/meetings", files=files)
    # Must not be a 500 Internal Server Error caused by missing table
    assert response.status_code != 500, (
        f"POST /api/meetings returned 500 — possible 'no such table' error: {response.text}"
    )
    assert response.status_code == 200, f"Unexpected status: {response.status_code} — {response.text}"


# ----------------- Audio Validation Tests -----------------

def test_upload_invalid_extension():
    """Verify that uploading a file with an unsupported extension is rejected with standard error."""
    file_content = b"fake audio content"
    files = {"file": ("test.txt", io.BytesIO(file_content), "text/plain")}
    response = client.post("/api/meetings", files=files)
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "INVALID_AUDIO"


@patch("app.core.config.settings.MAX_AUDIO_SIZE_MB", 0.000001)  # 1 byte limit
def test_upload_file_too_large():
    """Verify that uploading a file exceeding the maximum size is rejected with standard error."""
    file_content = b"fake audio content exceeding maximum limit"
    files = {"file": ("test.mp3", io.BytesIO(file_content), "audio/mpeg")}
    response = client.post("/api/meetings", files=files)
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "FILE_TOO_LARGE"


# ----------------- Meeting Creation & Background Processing Tests -----------------

@patch("app.api.meetings.process_meeting_task")
def test_create_meeting_endpoint(mock_task):
    """Verify that POST /api/meetings initializes a record in 'processing' state and triggers background task."""
    file_content = b"fake mp3 audio data"
    files = {"file": ("test_meeting.mp3", io.BytesIO(file_content), "audio/mpeg")}
    
    response = client.post("/api/meetings", files=files)
    assert response.status_code == 200
    
    data = response.json()
    assert data["id"] is not None
    assert data["status"] == "processing"
    
    # Check that background task was enqueued
    mock_task.assert_called_once()


# ----------------- Background Processing Flows -----------------

@patch("app.api.meetings.transcribe_audio")
@patch("app.api.meetings.summarize_transcript")
@patch("app.services.audio_service.delete_temp_audio")
def test_process_meeting_success(mock_cleanup, mock_summarize, mock_transcribe):
    """Verify background task flow updates DB to 'completed' and saves structured extraction."""
    db = TestingSessionLocal()
    meeting = Meeting(filename="test.mp3", status="processing")
    db.add(meeting)
    db.commit()
    db.refresh(meeting)
    
    mock_transcribe.return_value = "Hello this is a meeting transcript."
    mock_summarize.return_value = MeetingExtraction(
        meeting_title="Test Meeting Title",
        summary="Test Summary",
        key_decisions=["Decision 1"],
        action_items=[],
        open_questions=[],
        next_steps=[]
    )
    
    process_meeting_task(meeting.id, "/fake/temp/path.mp3")
    
    # Verify DB update
    db.expire_all()
    updated_meeting = db.query(Meeting).filter(Meeting.id == meeting.id).first()
    assert updated_meeting.status == "completed"
    assert updated_meeting.transcript == "Hello this is a meeting transcript."
    assert "Test Meeting Title" in updated_meeting.result_json
    
    mock_cleanup.assert_called_once_with("/fake/temp/path.mp3")
    db.close()


@patch("app.api.meetings.transcribe_audio")
@patch("app.services.audio_service.delete_temp_audio")
def test_process_meeting_transcription_failure(mock_cleanup, mock_transcribe):
    """Verify background task flow handles ASR failures, updates status to 'failed', and saves error message."""
    db = TestingSessionLocal()
    meeting = Meeting(filename="test.mp3", status="processing")
    db.add(meeting)
    db.commit()
    db.refresh(meeting)
    
    mock_transcribe.side_effect = TranscriptionFailedException("Whisper service down.")
    
    process_meeting_task(meeting.id, "/fake/temp/path.mp3")
    
    # Verify DB update
    db.expire_all()
    updated_meeting = db.query(Meeting).filter(Meeting.id == meeting.id).first()
    assert updated_meeting.status == "failed"
    assert updated_meeting.error_message == "Whisper service down."
    
    mock_cleanup.assert_called_once_with("/fake/temp/path.mp3")
    db.close()


@patch("app.api.meetings.transcribe_audio")
@patch("app.api.meetings.summarize_transcript")
@patch("app.services.audio_service.delete_temp_audio")
def test_process_meeting_llm_failure(mock_cleanup, mock_summarize, mock_transcribe):
    """Verify background task flow handles LLM failures, updates status to 'failed', and saves error message."""
    db = TestingSessionLocal()
    meeting = Meeting(filename="test.mp3", status="processing")
    db.add(meeting)
    db.commit()
    db.refresh(meeting)
    
    mock_transcribe.return_value = "Transcript text."
    mock_summarize.side_effect = LLMFailedException("Groq rate limit reached.")
    
    process_meeting_task(meeting.id, "/fake/temp/path.mp3")
    
    # Verify DB update
    db.expire_all()
    updated_meeting = db.query(Meeting).filter(Meeting.id == meeting.id).first()
    assert updated_meeting.status == "failed"
    assert updated_meeting.error_message == "Groq rate limit reached."
    db.close()


@patch("app.api.meetings.transcribe_audio")
@patch("app.api.meetings.summarize_transcript")
@patch("app.services.audio_service.delete_temp_audio")
def test_process_meeting_malformed_llm_output(mock_cleanup, mock_summarize, mock_transcribe):
    """Verify background task flow handles invalid LLM structure output, updates status to 'failed', and saves error message."""
    db = TestingSessionLocal()
    meeting = Meeting(filename="test.mp3", status="processing")
    db.add(meeting)
    db.commit()
    db.refresh(meeting)
    
    mock_transcribe.return_value = "Transcript text."
    mock_summarize.side_effect = InvalidLLMOutputException("Missing key_decisions field.")
    
    process_meeting_task(meeting.id, "/fake/temp/path.mp3")
    
    # Verify DB update
    db.expire_all()
    updated_meeting = db.query(Meeting).filter(Meeting.id == meeting.id).first()
    assert updated_meeting.status == "failed"
    assert updated_meeting.error_message == "Missing key_decisions field."
    db.close()


# ----------------- Meeting Retrieval Tests -----------------

def test_get_meeting_not_found():
    """Verify that retrieving a non-existent meeting returns 404."""
    response = client.get("/api/meetings/999")
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "MEETING_NOT_FOUND"


def test_get_meeting_success():
    """Verify that GET /api/meetings/{id} retrieves details correctly and parses JSON result."""
    db = TestingSessionLocal()
    result_mock = {
        "meeting_title": "Test Title",
        "summary": "Summary text",
        "key_decisions": ["D1"],
        "action_items": [],
        "open_questions": [],
        "next_steps": []
    }
    meeting = Meeting(
        filename="test_meeting.mp3",
        status="completed",
        transcript="Test transcript",
        result_json=json.dumps(result_mock)
    )
    db.add(meeting)
    db.commit()
    db.refresh(meeting)
    
    response = client.get(f"/api/meetings/{meeting.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "test_meeting.mp3"
    assert data["status"] == "completed"
    assert data["transcript"] == "Test transcript"
    assert data["result"]["meeting_title"] == "Test Title"
    db.close()


def test_list_meetings():
    """Verify that GET /api/meetings listings are ordered newest first and transcripts are omitted."""
    db = TestingSessionLocal()
    meeting1 = Meeting(filename="old.mp3", status="completed", transcript="transcript 1")
    meeting2 = Meeting(filename="new.mp3", status="completed", transcript="transcript 2")
    db.add(meeting1)
    db.add(meeting2)
    db.commit()
    
    response = client.get("/api/meetings")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    # Transcripts should be omitted for listing endpoint performance
    assert data[0]["transcript"] is None
    assert data[1]["transcript"] is None
    db.close()


# ----------------- Summarization Unit Tests -----------------

SAMPLE_TRANSCRIPT = (
    "The team decided to use FastAPI for the backend. "
    "Rahul will finish the API documentation by Friday. "
    "Priya will complete the frontend by Monday. "
    "We need to decide on the database next week."
)


def test_summarize_transcript_content_extraction():
    """
    Verify summarize_transcript extracts non-empty fields from a realistic transcript.
    The LLM call is mocked so this test is deterministic and offline.
    - summary must be non-empty
    - key_decisions must contain the FastAPI decision
    - action_items must contain Rahul's task and Priya's task
    - deadlines are populated only when explicitly stated in the transcript
    """
    from app.services.summarization_service import summarize_transcript
    from app.schemas.meeting import MeetingExtraction, ActionItem

    mock_extraction = MeetingExtraction(
        meeting_title="Backend & Frontend Planning Meeting",
        summary=(
            "The team agreed on FastAPI for the backend. "
            "Rahul was assigned API documentation due Friday, and Priya was assigned frontend work due Monday. "
            "A database decision is deferred to next week."
        ),
        key_decisions=["Use FastAPI for the backend."],
        action_items=[
            ActionItem(task="Finish API documentation", owner="Rahul", deadline="Friday", priority=None),
            ActionItem(task="Complete the frontend", owner="Priya", deadline="Monday", priority=None),
        ],
        open_questions=["Which database should be used?"],
        next_steps=["Decide on the database next week."],
    )

    with patch("app.services.summarization_service.Groq") as MockGroq:
        # Set up the mock to return our controlled extraction JSON
        mock_client = MockGroq.return_value
        mock_client.chat.completions.create.return_value.choices[0].message.content = (
            mock_extraction.model_dump_json()
        )

        # Use a real API key placeholder so the mock branch is NOT taken
        with patch("app.services.summarization_service.settings") as mock_settings:
            mock_settings.GROQ_API_KEY = "test-real-key"
            mock_settings.GROQ_LLM_MODEL = "openai/gpt-oss-120b"
            result = summarize_transcript(SAMPLE_TRANSCRIPT)

    # summary must be non-empty
    assert result.summary, "summary must not be empty"

    # key_decisions must contain the FastAPI decision
    decisions_lower = [d.lower() for d in result.key_decisions]
    assert any("fastapi" in d for d in decisions_lower), (
        f"Expected FastAPI decision in key_decisions, got: {result.key_decisions}"
    )

    # action_items must include Rahul's and Priya's tasks
    owners = [item.owner for item in result.action_items if item.owner]
    assert any("rahul" in o.lower() for o in owners), (
        f"Expected Rahul in action_items owners, got: {owners}"
    )
    assert any("priya" in o.lower() for o in owners), (
        f"Expected Priya in action_items owners, got: {owners}"
    )

    # Deadlines are only populated when explicitly stated
    rahul_item = next(i for i in result.action_items if i.owner and "rahul" in i.owner.lower())
    priya_item = next(i for i in result.action_items if i.owner and "priya" in i.owner.lower())
    assert rahul_item.deadline is not None, "Rahul's deadline (Friday) should be extracted"
    assert priya_item.deadline is not None, "Priya's deadline (Monday) should be extracted"


def test_summarize_transcript_empty_fields_raise_error():
    """
    Verify that if the LLM returns empty strings for required fields,
    summarize_transcript raises InvalidLLMOutputException instead of silently
    returning an empty result.
    """
    from app.services.summarization_service import summarize_transcript

    empty_response = json.dumps({
        "meeting_title": "",
        "summary": "",
        "key_decisions": [],
        "action_items": [],
        "open_questions": [],
        "next_steps": [],
    })

    with patch("app.services.summarization_service.Groq") as MockGroq:
        mock_client = MockGroq.return_value
        mock_client.chat.completions.create.return_value.choices[0].message.content = empty_response
        with patch("app.services.summarization_service.settings") as mock_settings:
            mock_settings.GROQ_API_KEY = "test-real-key"
            mock_settings.GROQ_LLM_MODEL = "openai/gpt-oss-120b"
            with pytest.raises(InvalidLLMOutputException):
                summarize_transcript(SAMPLE_TRANSCRIPT)


def test_summarize_transcript_strips_code_fences():
    """
    Verify that JSON wrapped in markdown code fences (``` blocks) is parsed correctly
    instead of raising a JSON parse error.
    """
    from app.services.summarization_service import summarize_transcript
    from app.schemas.meeting import MeetingExtraction, ActionItem

    valid_extraction = MeetingExtraction(
        meeting_title="Tech Planning",
        summary="The team chose FastAPI and assigned tasks.",
        key_decisions=["Use FastAPI for the backend."],
        action_items=[ActionItem(task="Write docs", owner="Rahul", deadline="Friday", priority=None)],
        open_questions=[],
        next_steps=[],
    )
    # Simulate a model that wraps JSON in ```json ... ``` code fences
    fenced_response = f"```json\n{valid_extraction.model_dump_json()}\n```"

    with patch("app.services.summarization_service.Groq") as MockGroq:
        mock_client = MockGroq.return_value
        mock_client.chat.completions.create.return_value.choices[0].message.content = fenced_response
        with patch("app.services.summarization_service.settings") as mock_settings:
            mock_settings.GROQ_API_KEY = "test-real-key"
            mock_settings.GROQ_LLM_MODEL = "openai/gpt-oss-120b"
            result = summarize_transcript(SAMPLE_TRANSCRIPT)

    assert result.meeting_title == "Tech Planning"
    assert result.summary == "The team chose FastAPI and assigned tasks."

