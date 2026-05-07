from sqlalchemy import JSON, Column, Integer, String

from src.models.db import Base


class TaskRecord(Base):
    """Database model for storing session recordings and audit trails."""
    __tablename__ = "tasks"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    site = Column(String)
    task_prompt = Column(String)
    template = Column(String, nullable=True)
    status = Column(String)
    result_summary = Column(String, nullable=True)
    outcome_details = Column(JSON, nullable=True)
    transcript = Column(JSON, nullable=True)
    transcript_path = Column(String, nullable=True)
    pending_question = Column(String, nullable=True)
    created_at = Column(String)
    updated_at = Column(String)
