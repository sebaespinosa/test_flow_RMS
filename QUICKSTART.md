# Quick Start Guide

Get the RMS project running in 5 minutes.

## Prerequisites

- Python 3.13+
- pip or poetry
- Git

## Installation

### 1. Clone & Navigate

```bash
cd /Users/seba/no_sync/Githubs/Seba/test_flow_RMS
```

### 2. Install Dependencies

```bash
# Option A: Using pip (recommended)
pip install -e ".[dev]"

# Option B: Using poetry
poetry install --with dev
```

### 3. Setup Database

```bash
# Create tables and schema
alembic upgrade head

# Or use make
make migrate
```

### 4. Run Tests (Optional but Recommended)

```bash
# Run all tests to verify setup
make test

# Output should show:
# tests/test_api.py::test_health_check PASSED
# tests/test_api.py::test_root_endpoint PASSED
# tests/test_idempotency.py::test_first_request_creates_record PASSED
# ... (5 total idempotency tests)
```

### 5. Start Development Server

```bash
make run

# Server starts on http://localhost:8000
# API Docs available at http://localhost:8000/docs
```

## Verify Installation

Open your browser or use curl:

```bash
# Health check
curl http://localhost:8000/health
# Response: {"status":"healthy","environment":"development"}

# API info
curl http://localhost:8000/
# Response: {"name":"RMS API","version":"0.1.0",...}
```

Visit http://localhost:8000/docs for interactive API documentation.

## Common Commands

```bash
# Development
make run              # Start dev server
make test             # Run all tests
make test-watch       # Run tests in watch mode
make lint             # Check code quality
make format           # Auto-format code

# Database
make migrate          # Run migrations
make migrate-make NAME="description"  # Create new migration

# Cleanup
make clean            # Remove cache and artifacts
```

## Project Structure

```
app/                           # Main application code
├── config/                    # Settings, logging, exceptions
├── database/                  # SQLAlchemy setup, migrations
├── common/                    # Shared base classes
└── infrastructure/idempotency # Idempotency system

tests/                         # Test suite
docs/                          # Architecture & pattern documentation
```

## Next: Create Your First Domain

To add a new API endpoint (e.g., managing invoices):

1. Create domain folder: `mkdir -p app/invoices/{rest,graphql}`
2. Create files following the pattern in `docs/Definitions/Patterns.md`
3. Add model to Alembic: Import in `app/database/base.py`
4. Create migration: `make migrate-make NAME="Add invoices table"`
5. Register router in `app/main.py`

See `docs/Scaffolding-Guide.md` section "Adding a New Domain" for detailed steps.

## Documentation

- **Architecture**: See [docs/Architecture.md](docs/Architecture.md)
- **Implementation Patterns**: See [docs/Definitions/Patterns.md](docs/Definitions/Patterns.md)
- **Scaffolding Guide**: See [docs/Scaffolding-Guide.md](docs/Scaffolding-Guide.md)
- **Developer Instructions**: See [.github/copilot-instructions.md](.github/copilot-instructions.md)

## Troubleshooting

### Port Already in Use
```bash
# Use a different port
python -m app.main --port 8001
```

### Database Issues
```bash
# Reset database
rm -f test_rms_dev.db
make migrate
```

### Dependency Issues
```bash
# Reinstall from scratch
rm -rf venv .venv
pip install -e ".[dev]" --force-reinstall
```

## What's Included

✅ FastAPI application factory  
✅ SQLAlchemy async ORM with Alembic migrations  
✅ Pydantic data validation with camelCase/snake_case bridge  
✅ Idempotency infrastructure with TTL  
✅ Multi-tenant isolation patterns  
✅ Structured logging with loguru  
✅ Comprehensive test suite  
✅ Code quality tools (Black, Ruff, MyPy)  
✅ Development utilities (Make, hot-reload)  

## Support

For questions about architecture patterns, refer to the documentation files. For specific implementation examples, check the test cases in `tests/test_idempotency.py`.

---

**Happy coding!** 🚀
