import json
from sqlalchemy.orm import Session
from app.models.meeting import Meeting

def create_meeting(db: Session, filename: str) -> Meeting:
    """Create a new meeting record in processing state."""
    db_meeting = Meeting(
        filename=filename,
        status="processing"
    )
    db.add(db_meeting)
    db.commit()
    db.refresh(db_meeting)
    return db_meeting

def get_meeting(db: Session, meeting_id: int) -> Meeting | None:
    """Retrieve a meeting record by its ID."""
    return db.query(Meeting).filter(Meeting.id == meeting_id).first()

def list_meetings(db: Session) -> list[Meeting]:
    """List all meeting records ordered by creation date descending."""
    return db.query(Meeting).order_by(Meeting.created_at.desc()).all()

def update_meeting(db: Session, meeting_id: int, **updates) -> Meeting | None:
    """Update properties of a meeting record."""
    db_meeting = get_meeting(db, meeting_id)
    if not db_meeting:
        return None
    
    for key, value in updates.items():
        if key == "result" and value is not None:
            # If standard dictionary or Pydantic model is passed for result, serialize it
            if hasattr(value, "model_dump_json"):
                db_meeting.result_json = value.model_dump_json()
            elif isinstance(value, dict):
                db_meeting.result_json = json.dumps(value)
            else:
                db_meeting.result_json = str(value)
        elif hasattr(db_meeting, key):
            setattr(db_meeting, key, value)
            
    db.commit()
    db.refresh(db_meeting)
    return db_meeting
