from typing import Optional, Any
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship, sessionmaker
from datetime import datetime
import uuid

from schemakernel.storage.sql import Base, PydanticType
from schemakernel.policy import PolicyConfig

class SQLPolicyVersion(Base):
    __tablename__ = "schemakernel_policy_versions"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    policy_name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    config: Mapped[PolicyConfig] = mapped_column(PydanticType(PolicyConfig), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

class SQLPolicyAlias(Base):
    __tablename__ = "schemakernel_policy_aliases"
    
    alias_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    policy_name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    version_id: Mapped[str] = mapped_column(String(36), ForeignKey("schemakernel_policy_versions.id"), nullable=False)
    
    version: Mapped[SQLPolicyVersion] = relationship("SQLPolicyVersion")

class VersionedPolicyStore:
    def __init__(self, engine: Any):
        self.engine = engine
        self.SessionLocal = sessionmaker(bind=self.engine)
        Base.metadata.create_all(self.engine)

    def save_version(self, policy_name: str, config: PolicyConfig, description: Optional[str] = None) -> str:
        with self.SessionLocal() as session:
            version = SQLPolicyVersion(
                policy_name=policy_name,
                config=config,
                description=description
            )
            session.add(version)
            session.commit()
            # Refresh to get the generated ID if not provided, though default handles it
            version_id = version.id
            return version_id

    def get_version(self, version_id: str) -> Optional[PolicyConfig]:
        with self.SessionLocal() as session:
            version = session.get(SQLPolicyVersion, version_id)
            return version.config if version else None

    def set_alias(self, alias_name: str, policy_name: str, version_id: str) -> None:
        with self.SessionLocal() as session:
            alias = session.get(SQLPolicyAlias, alias_name)
            if alias:
                alias.policy_name = policy_name
                alias.version_id = version_id
            else:
                alias = SQLPolicyAlias(
                    alias_name=alias_name,
                    policy_name=policy_name,
                    version_id=version_id
                )
                session.add(alias)
            session.commit()

    def resolve_alias(self, alias_name: str) -> Optional[PolicyConfig]:
        with self.SessionLocal() as session:
            alias = session.get(SQLPolicyAlias, alias_name)
            if alias and alias.version:
                return alias.version.config
            return None

    def list_versions(self, policy_name: str) -> list[dict[str, Any]]:
        with self.SessionLocal() as session:
            versions = (
                session.query(SQLPolicyVersion)
                .filter_by(policy_name=policy_name)
                .order_by(SQLPolicyVersion.created_at.desc())
                .all()
            )
            return [
                {
                    "id": v.id,
                    "created_at": v.created_at,
                    "description": v.description,
                    "policy_name": v.policy_name
                }
                for v in versions
            ]
