from typing import Any, Type, TypeVar

from sqlalchemy import Column, JSON, String, Integer, TypeDecorator
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Mapped, mapped_column
from pydantic import BaseModel

from schemakernel.models import CompletionOutcome, PlannerTrace, SchemaState
from schemakernel.store import StorageBackend
from schemakernel.exceptions import SessionNotFound

T = TypeVar("T", bound=BaseModel)

class PydanticType(TypeDecorator):
    """
    Pydantic type for SQLAlchemy columns.
    Uses JSON for storage, but handles Pydantic model validation.
    """
    impl = JSON
    cache_ok = True

    def __init__(self, model_class: Type[T], *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.model_class = model_class

    def process_bind_param(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, self.model_class):
            return value.model_dump(mode="json")
        return value

    def process_result_value(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return None
        return self.model_class.model_validate(value)

class Base(DeclarativeBase):
    pass

class SQLState(Base):
    __tablename__ = "schemakernel_states"
    session_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    state: Mapped[SchemaState] = mapped_column(PydanticType(SchemaState), nullable=False)

class SQLTrace(Base):
    __tablename__ = "schemakernel_traces"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    trace: Mapped[PlannerTrace] = mapped_column(PydanticType(PlannerTrace), nullable=False)

class SQLOutcome(Base):
    __tablename__ = "schemakernel_outcomes"
    session_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    outcome: Mapped[CompletionOutcome] = mapped_column(PydanticType(CompletionOutcome), nullable=False)

class SQLStorageBackend(StorageBackend):
    def __init__(self, engine):
        self.engine = engine
        self.SessionLocal = sessionmaker(bind=self.engine)
        Base.metadata.create_all(self.engine)

    def save_state(self, state: SchemaState) -> None:
        with self.SessionLocal() as session:
            sql_state = session.get(SQLState, state.session_id)
            if sql_state:
                sql_state.state = state
            else:
                sql_state = SQLState(session_id=state.session_id, state=state)
                session.add(sql_state)
            session.commit()

    def load_state(self, session_id: str) -> SchemaState:
        with self.SessionLocal() as session:
            sql_state = session.get(SQLState, session_id)
            if not sql_state:
                raise SessionNotFound(f"Session '{session_id}' not found")
            return sql_state.state

    def delete_state(self, session_id: str) -> None:
        with self.SessionLocal() as session:
            session.query(SQLState).filter_by(session_id=session_id).delete()
            session.query(SQLTrace).filter_by(session_id=session_id).delete()
            session.query(SQLOutcome).filter_by(session_id=session_id).delete()
            session.commit()

    def save_trace(self, trace: PlannerTrace) -> None:
        with self.SessionLocal() as session:
            sql_trace = SQLTrace(session_id=trace.session_id, trace=trace)
            session.add(sql_trace)
            session.commit()

    def list_traces(self, session_id: str) -> list[PlannerTrace]:
        with self.SessionLocal() as session:
            traces = (
                session.query(SQLTrace)
                .filter_by(session_id=session_id)
                .order_by(SQLTrace.id)
                .all()
            )
            return [t.trace for t in traces]

    def save_outcome(self, outcome: CompletionOutcome) -> None:
        with self.SessionLocal() as session:
            sql_outcome = session.get(SQLOutcome, outcome.session_id)
            if sql_outcome:
                sql_outcome.outcome = outcome
            else:
                sql_outcome = SQLOutcome(session_id=outcome.session_id, outcome=outcome)
                session.add(sql_outcome)
            session.commit()

    def load_outcome(self, session_id: str) -> CompletionOutcome:
        with self.SessionLocal() as session:
            sql_outcome = session.get(SQLOutcome, session_id)
            if not sql_outcome:
                raise SessionNotFound(f"No outcome for session '{session_id}'")
            return sql_outcome.outcome
