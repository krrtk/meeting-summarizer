from datetime import datetime
from pydantic import BaseModel, Field

class ActionItem(BaseModel):
    task: str = Field(..., description="The task description")
    owner: str | None = Field(default=None, description="The person responsible for the task, if explicitly identifiable")
    deadline: str | None = Field(default=None, description="The deadline for the task, if explicitly mentioned")
    priority: str | None = Field(default=None, description="The priority/urgency of the task, if explicitly indicated")


class MeetingExtraction(BaseModel):
    meeting_title: str = Field(..., description="A concise title of the meeting")
    summary: str = Field(..., description="A concise, high-level summary of the meeting")
    key_decisions: list[str] = Field(default_factory=list, description="List of key decisions made")
    action_items: list[ActionItem] = Field(default_factory=list, description="List of action items extracted from the meeting")
    open_questions: list[str] = Field(default_factory=list, description="List of unresolved or open questions")
    next_steps: list[str] = Field(default_factory=list, description="List of next steps")


class MeetingCreateResponse(BaseModel):
    id: int
    status: str

    model_config = {
        "from_attributes": True
    }


class MeetingResponse(BaseModel):
    id: int
    filename: str
    status: str
    transcript: str | None = None
    result: MeetingExtraction | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }
