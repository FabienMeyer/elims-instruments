"""Reusable CRUD operations for SQLModel tables."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from tomllib import TOMLDecodeError, load
from typing import TYPE_CHECKING, Generic, Protocol, TypeVar

from sqlalchemy.engine import URL, make_url
from sqlmodel import Session, SQLModel, create_engine, select

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from sqlalchemy.engine import Engine
    from sqlalchemy.orm.attributes import InstrumentedAttribute

ModelT = TypeVar("ModelT", bound=SQLModel)


class DebugLogger(Protocol):
    """Minimum logger interface required by CRUD repositories."""

    def debug(self, message: str, /, *args: object) -> None:
        """Log a repository diagnostic message."""
        ...


class DatabaseConfigurationError(ValueError):
    """Raised when a database TOML file is missing required configuration."""


class DuplicateAssetTagError(ValueError):
    """Raised when an asset tag is already assigned to another record."""

    def __init__(self, asset_tag: str) -> None:
        """Initialize the error with the conflicting asset tag."""
        self.asset_tag = asset_tag
        super().__init__(f"Asset tag already exists: {asset_tag}")


@dataclass(frozen=True)
class DatabaseSettings:
    """Validated database engine settings."""

    url: URL
    echo: bool


def read_database_settings(toml_path: Path) -> DatabaseSettings:
    """Read database settings and resolve relative SQLite paths beside TOML."""
    try:
        with toml_path.open("rb") as configuration_file:
            configuration = load(configuration_file)
        database = configuration["database"]
        raw_url = database["url"]
    except (OSError, TOMLDecodeError, KeyError, TypeError) as error:
        message = f"Invalid database configuration: {toml_path}"
        raise DatabaseConfigurationError(message) from error

    if not isinstance(raw_url, str) or not raw_url.strip():
        raise DatabaseConfigurationError("database.url must be a non-empty string")

    echo = database.get("echo", False)
    if not isinstance(echo, bool):
        raise DatabaseConfigurationError("database.echo must be a boolean")

    url = make_url(raw_url)
    if url.drivername == "sqlite" and url.database not in {None, ":memory:"}:
        database_path = Path(url.database)
        if not database_path.is_absolute():
            resolved = (toml_path.resolve().parent / database_path).resolve()
            url = url.set(database=str(resolved))
    return DatabaseSettings(url=url, echo=echo)


class Crud(Generic[ModelT]):
    """Provide common create, read, update, and delete operations.

    The configuration file must contain a ``[database]`` table with a SQLAlchemy
    ``url``. The optional ``echo`` flag enables SQL statement logging.
    """

    def __init__(
        self,
        logger: DebugLogger,
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
        settings = read_database_settings(self.toml_path)
        return create_engine(settings.url, echo=settings.echo)

    def _column(self, field: str) -> InstrumentedAttribute[object]:
        """Return a model column after validating its public field name."""
        if field not in self.model.model_fields:
            raise ValueError(f"Unknown {self.model.__name__} field: {field}")
        column: InstrumentedAttribute[object] = getattr(self.model, field)
        return column

    def fetchall(self) -> list[ModelT]:
        """Return all rows for the configured model."""
        self.logger.debug(self.fetchall.__name__)
        with Session(self.engine) as session:
            return list(session.exec(select(self.model)).all())

    def fetch(self, field: str, value: object) -> ModelT | None:
        """Return the first row where *field* equals *value*, if one exists."""
        self.logger.debug(self.fetch.__name__)
        statement = select(self.model).where(self._column(field) == value)
        with Session(self.engine) as session:
            return session.exec(statement).first()

    def add(self, data: ModelT) -> ModelT:
        """Persist and return *data*."""
        self.logger.debug(self.add.__name__)
        data = self.model.model_validate(data.model_dump())
        with Session(self.engine) as session:
            values = data.model_dump()
            asset_tag = values.get("asset_tag")
            if isinstance(asset_tag, str):
                statement = select(self.model).where(
                    self._column("asset_tag") == asset_tag
                )
                if session.exec(statement).first() is not None:
                    raise DuplicateAssetTagError(asset_tag)
            session.add(data)
            session.commit()
            session.refresh(data)
            return data

    def remove(self, field: str, value: object) -> bool:
        """Delete the first matching row and report whether one was found."""
        self.logger.debug(self.remove.__name__)
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
        self.logger.debug(self.update.__name__)
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

    def update_by_asset_tag(
        self,
        asset_tag: str,
        changes: Mapping[str, object],
    ) -> ModelT | None:
        """Update a record selected by its laboratory asset tag.

        The primary ``id`` is immutable. All changes are validated together before
        they are persisted.
        """
        invalid_fields = set(changes) - set(self.model.model_fields)
        if invalid_fields:
            fields = ", ".join(sorted(invalid_fields))
            raise ValueError(f"Unknown {self.model.__name__} fields: {fields}")
        if "id" in changes:
            raise ValueError("The record ID cannot be changed")

        statement = select(self.model).where(self._column("asset_tag") == asset_tag)
        with Session(self.engine) as session:
            data = session.exec(statement).first()
            if data is None:
                return None

            values = data.model_dump()
            values.update(changes)
            validated = self.model.model_validate(values)
            new_asset_tag = validated.model_dump().get("asset_tag")
            if isinstance(new_asset_tag, str) and new_asset_tag != asset_tag:
                duplicate_statement = select(self.model).where(
                    self._column("asset_tag") == new_asset_tag
                )
                if session.exec(duplicate_statement).first() is not None:
                    raise DuplicateAssetTagError(new_asset_tag)
            for field in changes:
                setattr(data, field, getattr(validated, field))
            session.add(data)
            session.commit()
            session.refresh(data)
            return data

    def upsert_many(self, records: Sequence[ModelT]) -> tuple[int, int]:
        """Insert missing records and fully update existing records by ID."""
        records = [
            self.model.model_validate(record.model_dump()) for record in records
        ]
        identifiers = [record.model_dump()["id"] for record in records]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("The record list contains duplicate IDs")
        asset_tags = [record.model_dump()["asset_tag"] for record in records]
        seen_asset_tags: set[object] = set()
        for asset_tag in asset_tags:
            if asset_tag in seen_asset_tags:
                raise DuplicateAssetTagError(str(asset_tag))
            seen_asset_tags.add(asset_tag)

        created = 0
        updated = 0
        with Session(self.engine) as session:
            for identifier, asset_tag in zip(identifiers, asset_tags, strict=True):
                statement = select(self.model).where(
                    self._column("asset_tag") == asset_tag
                )
                existing = session.exec(statement).first()
                if (
                    existing is not None
                    and existing.model_dump()["id"] != identifier
                ):
                    raise DuplicateAssetTagError(str(asset_tag))

            for incoming in records:
                identifier = incoming.model_dump()["id"]
                stored = session.get(self.model, identifier)
                if stored is None:
                    session.add(incoming)
                    created += 1
                    continue

                for field in self.model.model_fields:
                    if field != "id":
                        setattr(stored, field, getattr(incoming, field))
                session.add(stored)
                updated += 1
            session.commit()
        return created, updated
