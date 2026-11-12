"""SpirandeliEmpire OS 3.2 — Multi-User, BYOK & AI Model Manager Database Models"""

import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy import (
    String, Text, Boolean, Integer, Float, DateTime, JSON, ForeignKey, UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.session import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    full_name: Mapped[str] = mapped_column(String(128), default="Usuário", nullable=False)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(256), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    role: Mapped[str] = mapped_column(String(32), default="USER", nullable=False)  # ADMIN, USER, VIEWER (legacy: owner)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    terms_accepted: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)

    sessions = relationship("UserSessionModel", back_populates="user", cascade="all, delete-orphan")
    credentials = relationship("AIProviderCredentialModel", back_populates="user", cascade="all, delete-orphan")


class UserSessionModel(Base):
    __tablename__ = "user_sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    refresh_token_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    user_agent: Mapped[str] = mapped_column(String(256), default="")
    ip_address: Mapped[str] = mapped_column(String(64), default="")
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    last_used_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    user = relationship("UserModel", back_populates="sessions")


class PasswordResetTokenModel(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class InviteCodeModel(Base):
    __tablename__ = "invite_codes"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    created_by_user_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    used_by_user_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    is_used: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class SecurityAuditLogModel(Base):
    __tablename__ = "security_audit_logs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    user_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    ip_address: Mapped[str] = mapped_column(String(64), default="")
    details_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, index=True)


class AIProviderCredentialModel(Base):
    __tablename__ = "ai_provider_credentials"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False, index=True)  # gemini, openai, anthropic
    label: Mapped[str] = mapped_column(String(128), nullable=False)
    workspace_org: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    encrypted_api_key: Mapped[str] = mapped_column(Text, nullable=False)
    encryption_key_version: Mapped[str] = mapped_column(String(16), default="v1", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_validated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    last_error_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    last_error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)

    user = relationship("UserModel", back_populates="credentials")
    models = relationship("AIModelCatalogModel", back_populates="credential", cascade="all, delete-orphan")


class AIModelCatalogModel(Base):
    __tablename__ = "ai_models"
    __table_args__ = (
        UniqueConstraint("credential_id", "model_id", name="uq_ai_model_cred_model"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    credential_id: Mapped[str] = mapped_column(String(64), ForeignKey("ai_provider_credentials.id", ondelete="CASCADE"), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    model_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    version: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    context_window: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    max_output_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    supported_methods: Mapped[List[str]] = mapped_column(JSON, default=list)
    capabilities: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)
    lifecycle_status: Mapped[str] = mapped_column(String(32), default="active", index=True)  # active, deprecated, retired, unconfirmed
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    raw_metadata: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    last_synced_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    credential = relationship("AIProviderCredentialModel", back_populates="models")


class AIProviderSyncLogModel(Base):
    __tablename__ = "ai_provider_sync_logs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    credential_id: Mapped[str] = mapped_column(String(64), ForeignKey("ai_provider_credentials.id", ondelete="CASCADE"), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)  # success, error
    models_count: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, index=True)


class UserAIPreferenceModel(Base):
    __tablename__ = "user_ai_preferences"

    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    default_provider: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    default_credential_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    default_model_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    fallback_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    fallback_chain: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)
    usage_limits: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)


class AgentModelConfigModel(Base):
    __tablename__ = "agent_model_configs"
    __table_args__ = (
        UniqueConstraint("user_id", "agent_id", name="uq_user_agent_model_cfg"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    provider: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    credential_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    model_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    generation_params: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    fallback_enabled: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    fallback_chain: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)


class TaskModelConfigModel(Base):
    __tablename__ = "task_model_configs"
    __table_args__ = (
        UniqueConstraint("user_id", "profile_key", name="uq_user_task_profile_cfg"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    profile_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    provider: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    credential_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    model_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    generation_params: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)


class AIUsageRecordModel(Base):
    __tablename__ = "ai_usage_records"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    project_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    workflow_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    task_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    model_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    credential_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cached_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32), default="success", index=True)  # success, error, fallback_success
    fallback_from: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, index=True)


class AgentModel(Base):
    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    department: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(128), nullable=False)
    specialty: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    provider: Mapped[str] = mapped_column(String(64), default="")
    model: Mapped[str] = mapped_column(String(64), default="")
    generation_config: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    allowed_tools: Mapped[List[str]] = mapped_column(JSON, default=list)
    permissions: Mapped[List[str]] = mapped_column(JSON, default=list)
    memory: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    operational_state: Mapped[str] = mapped_column(String(32), default="idle", index=True)
    avatar_url: Mapped[str] = mapped_column(String(256), default="")
    office_room: Mapped[str] = mapped_column(String(64), default="development")
    metrics: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    history: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)
    assigned_tasks: Mapped[List[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)

    memories = relationship("MemoryModel", back_populates="agent", cascade="all, delete-orphan")


class ProjectModel(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    user_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    objectives: Mapped[List[str]] = mapped_column(JSON, default=list)
    project_type: Mapped[str] = mapped_column(String(64), default="software", index=True)
    status: Mapped[str] = mapped_column(String(32), default="active", index=True)
    priority: Mapped[str] = mapped_column(String(32), default="medium")
    department: Mapped[str] = mapped_column(String(64), default="development")
    lead_agent_id: Mapped[str] = mapped_column(String(64), default="jeffrey")
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)

    tasks = relationship("TaskModel", back_populates="project", cascade="all, delete-orphan")
    workflows = relationship("WorkflowModel", back_populates="project", cascade="all, delete-orphan")
    artifacts = relationship("ArtifactModel", back_populates="project", cascade="all, delete-orphan")


class WorkflowModel(Base):
    __tablename__ = "workflows"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    user_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    project_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("projects.id", ondelete="CASCADE"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    workflow_type: Mapped[str] = mapped_column(String(64), default="supervisor", index=True)
    status: Mapped[str] = mapped_column(String(32), default="running", index=True)
    current_node: Mapped[str] = mapped_column(String(64), default="start")
    graph_state: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    checkpoints: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)
    errors: Mapped[List[str]] = mapped_column(JSON, default=list)
    quality_results: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)
    initiated_by: Mapped[str] = mapped_column(String(64), default="user")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)

    project = relationship("ProjectModel", back_populates="workflows")
    executions = relationship("WorkflowExecutionModel", back_populates="workflow", cascade="all, delete-orphan")


class WorkflowExecutionModel(Base):
    __tablename__ = "workflow_executions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    workflow_id: Mapped[str] = mapped_column(String(64), ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False, index=True)
    celery_task_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="queued", index=True)
    attempt: Mapped[int] = mapped_column(Integer, default=1)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metrics_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    workflow = relationship("WorkflowModel", back_populates="executions")


class TaskModel(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    user_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    project_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("projects.id", ondelete="CASCADE"), nullable=True, index=True)
    workflow_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("workflows.id", ondelete="SET NULL"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    assigned_agent_id: Mapped[str] = mapped_column(String(64), default="jeffrey", index=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    priority: Mapped[str] = mapped_column(String(32), default="medium")
    dependencies: Mapped[List[str]] = mapped_column(JSON, default=list)
    deadline: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    approvals_required: Mapped[bool] = mapped_column(Boolean, default=False)
    artifacts: Mapped[List[str]] = mapped_column(JSON, default=list)
    quality_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    result_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)

    project = relationship("ProjectModel", back_populates="tasks")


class ArtifactModel(Base):
    __tablename__ = "artifacts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    user_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    artifact_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    file_hash: Mapped[str] = mapped_column(String(64), default="")
    version: Mapped[int] = mapped_column(Integer, default=1)
    project_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True)
    workflow_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("workflows.id", ondelete="SET NULL"), nullable=True, index=True)
    creator_agent_id: Mapped[str] = mapped_column(String(64), default="jeffrey")
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, index=True)

    project = relationship("ProjectModel", back_populates="artifacts")


class ApprovalModel(Base):
    __tablename__ = "approvals"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    user_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    workflow_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("workflows.id", ondelete="CASCADE"), nullable=True, index=True)
    project_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    task_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    requested_by_agent_id: Mapped[str] = mapped_column(String(64), default="jeffrey")
    action_name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    resources_used: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    risks: Mapped[List[str]] = mapped_column(JSON, default=list)
    consequences: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    reviewer_feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, index=True)


class IntegrationModel(Base):
    __tablename__ = "integrations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    credentials_encrypted: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    permissions: Mapped[List[str]] = mapped_column(JSON, default=list)
    last_tested_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    config_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class EventModel(Base):
    __tablename__ = "events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    user_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    agent_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    workflow_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    project_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    payload: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, index=True)


class ChatMessageModel(Base):
    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    user_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    project_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    workflow_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    sender_type: Mapped[str] = mapped_column(String(32), default="user")
    sender_name: Mapped[str] = mapped_column(String(64), default="User")
    agent_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, index=True)


class MemoryModel(Base):
    __tablename__ = "agent_memories"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    user_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    agent_id: Mapped[str] = mapped_column(String(64), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True)
    memory_type: Mapped[str] = mapped_column(String(32), default="long_term", index=True)
    key: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)

    agent = relationship("AgentModel", back_populates="memories")


class SystemLogModel(Base):
    __tablename__ = "system_logs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    level: Mapped[str] = mapped_column(String(16), default="INFO", index=True)
    source: Mapped[str] = mapped_column(String(64), default="backend", index=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    details_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    workflow_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    agent_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, index=True)


class SettingModel(Base):
    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    description: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)
