"""Reusable CRUD operations for SQLModel tables."""

from __future__ import annotations

from tomllib import TOMLDecodeError, load
from typing import TYPE_CHECKING, Generic, TypeVar

from sqlmodel import Session, SQLModel, create_engine, select

if TYPE_CHECKING:
    from logging import Logger
    from pathlib import Path

    from sqlalchemy.engine import Engine
    from sqlalchemy.orm.attributes import InstrumentedAttribute

ModelT = TypeVar("ModelT", bound=SQLModel)


class DatabaseConfigurationError(ValueError):
    """Raised when a database TOML file is missing required configuration."""


class Crud(Generic[ModelT]):
    """Provide common create, read, update, and delete operations.

    The configuration file must contain a ``[database]`` table with a SQLAlchemy
    ``url``. The optional ``echo`` flag enables SQL statement logging.
    """

    def __init__(
        self,
        logger: Logger,
        toml_path: Path,
        model: type[ModelT],
        *,
        create_tables: bool = True,
    ) -> None:
        """Configure a CRUD repository for *model*.

        Args:
            logger: Logger used for operation diagnostics.
            toml_path: Path to the database TOML configuration.
            model: SQLModel table handled by this repository.
            create_tables: Create missing SQL tables during initialization.
        """
        self.logger = logger
        self.toml_path = toml_path
        self.model = model
        self._engine = self._create_engine()
        if create_tables:
            SQLModel.metadata.create_all(self._engine)

    @property
    def engine(self) -> Engine:
        """Return the repository's shared database engine."""
        return self._engine

    def _create_engine(self) -> Engine:
        """Create an engine from the database TOML configuration."""
        try:
            with self.toml_path.open("rb") as configuration_file:
                configuration = load(configuration_file)
            database = configuration["database"]
            url = database["url"]
        except (OSError, TOMLDecodeError, KeyError, TypeError) as error:
            message = f"Invalid database configuration: {self.toml_path}"
            raise DatabaseConfigurationError(message) from error

        if not isinstance(url, str) or not url.strip():
            message = "database.url must be a non-empty string"
            raise DatabaseConfigurationError(message)

        echo = database.get("echo", False)
        if not isinstance(echo, bool):
            message = "database.echo must be a boolean"
            raise DatabaseConfigurationError(message)
        return create_engine(url, echo=echo)

    def _column(self, field: str) -> InstrumentedAttribute[object]:
        """Return a model column after validating its public field name."""
        if field not in self.model.model_fields:
            raise ValueError(f"Unknown {self.model.__name__} field: {field}")
        column: InstrumentedAttribute[object] = getattr(self.model, field)
        return column

    def fetchall(self) -> list[ModelT]:
        """Return all rows for the configured model."""
        self.logger.debug("%s", self.fetchall.__name__)
        with Session(self.engine) as session:
            return list(session.exec(select(self.model)).all())

    def fetch(self, field: str, value: object) -> ModelT | None:
        """Return the first row where *field* equals *value*, if one exists."""
        self.logger.debug("%s", self.fetch.__name__)
        statement = select(self.model).where(self._column(field) == value)
        with Session(self.engine) as session:
            return session.exec(statement).first()

    def add(self, data: ModelT) -> ModelT:
        """Persist and return *data*."""
        self.logger.debug("%s", self.add.__name__)
        with Session(self.engine) as session:
            session.add(data)
            session.commit()
            session.refresh(data)
            return data

    def remove(self, field: str, value: object) -> bool:
        """Delete the first matching row and report whether one was found."""
        self.logger.debug("%s", self.remove.__name__)
        statement = select(self.model).where(self._column(field) == value)
        with Session(self.engine) as session:
            data = session.exec(statement).first()
            if data is None:
                return False
            session.delete(data)
            session.commit()
            return True

    def update(
        self,
        field: str,
        old_value: object,
        new_value: object,
    ) -> ModelT | None:
        """Update *field* on the first matching row and return that row."""
        self.logger.debug("%s", self.update.__name__)
        column = self._column(field)
        statement = select(self.model).where(column == old_value)
        with Session(self.engine) as session:
            data = session.exec(statement).first()
            if data is None:
                return None
            setattr(data, field, new_value)
            session.add(data)
            session.commit()
            session.refresh(data)
            return data
