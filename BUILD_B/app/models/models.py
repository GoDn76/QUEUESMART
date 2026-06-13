from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    BigInteger,
    Identity,
    JSON,
    Index,
    Enum,
)
from sqlalchemy.orm import relationship

from app.db.session import Base


def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    # Relationships
    counters = relationship("Counter", back_populates="organization", cascade="all, delete-orphan")
    service_types = relationship("ServiceType", back_populates="organization", cascade="all, delete-orphan")
    operators = relationship("Operator", back_populates="organization", cascade="all, delete-orphan")
    display_boards = relationship("DisplayBoard", back_populates="organization", cascade="all, delete-orphan")


class Counter(Base):
    __tablename__ = "counters"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    queue_type = Column(String, nullable=False)  # FIFO, PRIORITY, HYBRID
    qr_slug = Column(String, unique=True, index=True, nullable=False)
    active = Column(Boolean, default=True, nullable=False)

    # Relationships
    organization = relationship("Organization", back_populates="counters")
    operators = relationship("Operator", back_populates="counter")
    tokens = relationship("Token", back_populates="counter", cascade="all, delete-orphan")
    display_boards = relationship("DisplayBoard", back_populates="counter")


class ServiceType(Base):
    __tablename__ = "service_types"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    estimated_duration_minutes = Column(Integer, default=15, nullable=False)
    priority_weight = Column(Integer, default=10, nullable=False)

    # Relationships
    organization = relationship("Organization", back_populates="service_types")
    tokens = relationship("Token", back_populates="service_type")


class Operator(Base):
    __tablename__ = "operators"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    counter_id = Column(Integer, ForeignKey("counters.id", ondelete="SET NULL"), nullable=True)
    active = Column(Boolean, default=True, nullable=False)
    last_login_at = Column(DateTime, nullable=True)
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    password_changed_at = Column(DateTime, nullable=True)
    session_version = Column(Integer, default=1, nullable=False)

    # Relationships
    organization = relationship("Organization", back_populates="operators")
    counter = relationship("Counter", back_populates="operators")
    events = relationship("QueueEvent", back_populates="operator")


class Token(Base):
    __tablename__ = "tokens"

    id = Column(Integer, primary_key=True, index=True)
    # Autoincrementing PostgreSQL identity sequence
    sequence_number = Column(BigInteger, Identity(start=1), nullable=False, unique=True)
    token_number = Column(String, nullable=False, index=True)
    counter_id = Column(Integer, ForeignKey("counters.id", ondelete="CASCADE"), nullable=False)
    service_type_id = Column(Integer, ForeignKey("service_types.id", ondelete="CASCADE"), nullable=False)
    customer_name = Column(String, nullable=False)
    customer_phone = Column(String, nullable=False)
    status = Column(String, nullable=False, index=True)  # WAITING, IN_PROGRESS, COMPLETED, SKIPPED, ABANDONED
    priority_score = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    called_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    counter = relationship("Counter", back_populates="tokens")
    service_type = relationship("ServiceType", back_populates="tokens")
    events = relationship("QueueEvent", back_populates="token", cascade="all, delete-orphan")

    # Composite indexes for faster queue operations & analytics
    __table_args__ = (
        Index("idx_token_counter_status", "counter_id", "status"),
        Index("idx_token_created_at", "created_at"),
    )


class QueueEvent(Base):
    __tablename__ = "queue_events"

    id = Column(Integer, primary_key=True, index=True)
    token_id = Column(Integer, ForeignKey("tokens.id", ondelete="CASCADE"), nullable=True)
    operator_id = Column(Integer, ForeignKey("operators.id", ondelete="SET NULL"), nullable=True)
    event_type = Column(String, nullable=False)  # JOINED, CALLED, COMPLETED, SKIPPED, ABANDONED, etc.
    event_data = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=utc_now, nullable=False)

    # Relationships
    token = relationship("Token", back_populates="events")
    operator = relationship("Operator", back_populates="events")


class DisplayBoard(Base):
    __tablename__ = "display_boards"

    id = Column(Integer, primary_key=True, index=True)
    uuid_id = Column(String, unique=True, index=True, nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    counter_id = Column(Integer, ForeignKey("counters.id", ondelete="SET NULL"), nullable=True)
    name = Column(String, nullable=False)
    board_type = Column(String, nullable=False)  # COUNTER, ORGANIZATION
    access_token = Column(String, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    # Relationships
    organization = relationship("Organization", back_populates="display_boards")
    counter = relationship("Counter", back_populates="display_boards")


class TokenMigrationRequest(Base):
    __tablename__ = "token_migrations"

    id = Column(Integer, primary_key=True, index=True)
    token_id = Column(Integer, ForeignKey("tokens.id", ondelete="CASCADE"), nullable=False)
    from_counter_id = Column(Integer, ForeignKey("counters.id", ondelete="CASCADE"), nullable=False)
    to_counter_id = Column(Integer, ForeignKey("counters.id", ondelete="CASCADE"), nullable=False)
    predicted_time_saved = Column(Integer, nullable=True)
    reason = Column(String, nullable=True)
    status = Column(String, nullable=False, default="PENDING")  # PENDING, SOURCE_APPROVED, DESTINATION_APPROVED, FULLY_APPROVED, REJECTED, EXECUTED
    created_by_id = Column(Integer, ForeignKey("operators.id", ondelete="SET NULL"), nullable=True)
    source_operator_approved = Column(Boolean, default=False)
    destination_operator_approved = Column(Boolean, default=False)
    approved_by_id = Column(Integer, ForeignKey("operators.id", ondelete="SET NULL"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    executed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    # Relationships
    token = relationship("Token")
    from_counter = relationship("Counter", foreign_keys=[from_counter_id])
    to_counter = relationship("Counter", foreign_keys=[to_counter_id])
    created_by = relationship("Operator", foreign_keys=[created_by_id])
    approved_by = relationship("Operator", foreign_keys=[approved_by_id])

