# Development

## Install development dependencies

```powershell
uv sync --frozen
```

The lockfile supplies Ruff, Mypy, Pytest, MkDocs Material, and mkdocstrings.

## Run quality checks

```powershell
uv run ruff format --check elims_instruments tests examples
uv run ruff check elims_instruments tests examples
uv run mypy elims_instruments
uv run pytest
uv run mkdocs build --strict
```

The documentation build is strict both locally and in CI: missing navigation
entries, invalid links, unresolved API objects, and other warnings fail the job.

## Preview documentation

```powershell
uv run mkdocs serve
```

Open `http://127.0.0.1:8000/`. MkDocs rebuilds when documentation, source, or
configuration files change. Generated output is written to `site/`, which is
ignored by Git.

## Database migrations

Schema revisions live under
`elims_instruments/database/migration_scripts/versions/`. Add a new migration
instead of changing a revision that has already shipped.

Validate a migration from an empty database and from the immediately preceding
revision. Apply the current schema with:

```powershell
uv run elims database upgrade --config bench.toml
```

## Documentation conventions

- Write task-oriented instructions in the user guide.
- Keep architecture pages conceptual and decision-focused.
- Put Python API details in docstrings and render them with mkdocstrings.
- Use relative links for pages within this site.
- Include language identifiers on fenced code blocks.
- Add every Markdown page to `nav` so strict builds remain intentional.
