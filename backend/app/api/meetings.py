import json
import logging
from typing import List
from fastapi import APIRouter, Depends, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session

from app.models.database import get_db, SessionLocal
from app.schemas.meeting import MeetingCreateResponse, MeetingResponse
from app.repositories import meeting_repository
from app.services import audio_service
from app.services.transcription_service import transcribe_audio
from app.services.summarization_service import summarize_transcript
from app.core.errors import AppException, MeetingNotFoundException

logger = logging.getLogger("meeting_summarizer")

router = APIRouter(prefix="/api/meetings", tags=["meetings"])


def process_meeting_task(meeting_id: int, temp_path: str):
    """Background task to transcribe, analyze, and save meeting intelligence."""
    db: Session = SessionLocal()
    try:
        logger.info(f"Background task: Started processing meeting {meeting_id}")
        
        # 1. Transcribe audio
        logger.info(f"Background task: Transcribing audio for meeting {meeting_id}")
        transcript_text = transcribe_audio(temp_path)
        meeting_repository.update_meeting(db, meeting_id, transcript=transcript_text)
        
        # 2. Extract meeting intelligence (Summarization)
        logger.info(f"Background task: Summarizing transcript for meeting {meeting_id}")
        structured_summary = summarize_transcript(transcript_text)
        
        # 3. Update database record with success status
        meeting_repository.update_meeting(
            db,
            meeting_id,
            status="completed",
            result=structured_summary
        )
        logger.info(f"Background task: Successfully processed meeting {meeting_id}")
        
    except AppException as e:
        logger.error(f"Background task: Application error processing meeting {meeting_id}: {e.message}")
        meeting_repository.update_meeting(db, meeting_id, status="failed", error_message=e.message)
    except Exception as e:
        logger.error(f"Background task: Unexpected error processing meeting {meeting_id}: {e}", exc_info=True)
        meeting_repository.update_meeting(db, meeting_id, status="failed", error_message="Internal processing failure.")
    finally:
        # 4. Clean up temporary audio file
        logger.info(f"Background task: Cleaning up temporary audio at {temp_path}")
        audio_service.delete_temp_audio(temp_path)
        db.close()


@router.post("", response_model=MeetingCreateResponse)
async def create_meeting(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload audio, initialize meeting, and queue background processing."""
    # 1. Validate and save audio file temporarily
    temp_path = audio_service.save_temp_audio(file)
    
    # 2. Initialize database record in 'processing' status
    db_meeting = meeting_repository.create_meeting(db, file.filename)
    
    # 3. Queue the background processing task
    background_tasks.add_task(process_meeting_task, db_meeting.id, temp_path)
    
    return db_meeting


@router.get("/{meeting_id}", response_model=MeetingResponse)
async def get_meeting(meeting_id: int, db: Session = Depends(get_db)):
    """Retrieve details for a specific meeting, parsing result JSON."""
    meeting = meeting_repository.get_meeting(db, meeting_id)
    if not meeting:
        raise MeetingNotFoundException()
        
    result_data = None
    if meeting.result_json:
        try:
            result_data = json.loads(meeting.result_json)
        except Exception as e:
            logger.error(f"Failed to deserialize result_json for meeting {meeting_id}: {e}")
            
    return MeetingResponse(
        id=meeting.id,
        filename=meeting.filename,
        status=meeting.status,
        transcript=meeting.transcript,
        result=result_data,
        error_message=meeting.error_message,
        created_at=meeting.created_at,
        updated_at=meeting.updated_at
    )


@router.get("", response_model=List[MeetingResponse])
async def list_meetings(db: Session = Depends(get_db)):
    """List all meetings. Transcripts are omitted for performance."""
    meetings = meeting_repository.list_meetings(db)
    response_list = []
    
    for meeting in meetings:
        result_data = None
        if meeting.result_json:
            try:
                result_data = json.loads(meeting.result_json)
            except Exception:
                pass
                
        response_list.append(
            MeetingResponse(
                id=meeting.id,
                filename=meeting.filename,
                status=meeting.status,
                transcript=None,  # Omit large transcripts for listing
                result=result_data,
                error_message=meeting.error_message,
                created_at=meeting.created_at,
                updated_at=meeting.updated_at
            )
        )
        
    return response_list
