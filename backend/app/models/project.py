from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="analyzing")

    # RFP source
    solicitation_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_s3_key: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Analysis results
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    requirements: Mapped[list] = mapped_column(JSONB, default=list)
    compliance_matrix: Mapped[list] = mapped_column(JSONB, default=list)
    gaps: Mapped[list] = mapped_column(JSONB, default=list)

    # Company context snapshot
    company_profile_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    past_performance_snapshot: Mapped[list] = mapped_column(JSONB, default=list)
    capability_statement_snapshot: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    organization: Mapped["Organization"] = relationship(back_populates="projects")  # noqa: F821
    draft_sections: Mapped[list["DraftSection"]] = relationship(  # noqa: F821
        back_populates="project"
    )
    conversations: Mapped[list["Conversation"]] = relationship(back_populates="project")  # noqa: F821
