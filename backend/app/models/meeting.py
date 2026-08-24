from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime
from app.models.database import Base

class Meeting(Base):
    __tablename__ = "meetings"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    # status can be: "processing", "completed", "failed"
    status = Column(String, default="processing", nullable=False)
    transcript = Column(Text, nullable=True)
    # Stored as raw serialized JSON string containing the MeetingExtraction output
    result_json = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
