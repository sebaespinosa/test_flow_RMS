# test_flow_RMS

Code Challenge from Flow RMS

## Context

Please read [Assumptions](Assumptions.md) before moving on for general technical context

Although the application is heavy developed using AI Coding Assitance (copilot in my case), the documents on [docs](docs/) document all of the architecture and software definition in this project. Although they are AI generated as well, I carefully review them. The output of all of this practices, is on [copilot-instructions file](.github/copilot-instructions.md) which is the file for the AI coding assitant with all guidelines define by me for this projects

- [Architecture](docs/Architecture.md) documents all the architecture and software architecture definitions and implementations, including database/ORM optimizations
- [Patterns](docs/Patterns.md) documents all of the patterns, principles, and strategies implemented throught this project
- [Scoring](docs/Scoring.md) documents the scoring process/euristic I decide to implement for this project
- [Scaffolding] (docs/Scaffolding-Guide.md) is guide of the folder/layers structure defined for the project and how to implement a new one
- [AI Usage Guide](docs/AI_Usage_Guide.md) is a guide for the AI LLM implementation

## Run the application

1. The project uses poetry for virtual environment handling, althought a requirements.txt file is provided for using another tool
```bash
poetry install --no-root
# Use file requirements.txt with another virtual environment and dependency manager
```
2. Set up environment variables:
   - Update `.env` (DO NOT commit `.env` - it contains secrets)
   - Set `ENABLE_SEED_ENDPOINTS=true` before calling any seed endpoints; they are off by default to prevent accidents
3. Run Alembic migrations (from repo root; point Alembic to the config under app/):
```bash
poetry run alembic -c app/alembic.ini upgrade head
```
4. Run the Development Server
    - Via CLI:
    ```bash
    #From the project root folder
    poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
    ```
    - Via VS Code Debugger:
        1. Open `.vscode/launch.json`
        2. Click "Run and Debug" (or press `F5`)
        3. Select "test_flow_RMS" configuration
        4. Server starts with breakpoint support
    - Visit: [http://localhost:8000/docs](http://localhost:8000/docs) for interactive API docs.

5. Seed Test Data (Optional, requires ENABLE_SEED_ENDPOINTS=true)
```bash
curl -X POST http://localhost:8000/api/v1/seed
```
- **Inspect data**:
```bash
curl http://localhost:8000/api/v1/seed/status
```
- **Clean up**:
```bash
curl -X POST http://localhost:8000/api/v1/seed/cleanup
```

---

## Run Tests

### Run all tests:
```bash
poetry run pytest tests/ -v
```

### Run specific test module:
```bash
poetry run pytest tests/tenants/ -v
poetry run pytest tests/invoices/ -v
poetry run pytest tests/bank_transactions/ -v
poetry run pytest tests/reconciliation/ -v
poetry run pytest tests/ai/ -v  # Requires AI to be enabled
```

### Run with coverage:
```bash
poetry run pytest tests/ --cov=app --cov-report=html
```

### Run in watch mode (auto-rerun on file changes):
```bash
poetry run pytest tests/ -v --tb=short --looponfail
```

---

## Manual Integration Testing with Postman

For hands-on E2E testing of API workflows, seed data management, and idempotency:

1. Import Postman collection: [postman/RMS-API.postman_collection.json](postman/RMS-API.postman_collection.json)
2. Import environment: [postman/RMS-API-Environment.postman_environment.json](postman/RMS-API-Environment.postman_environment.json)
3. See [postman/README.md](postman/README.md) for detailed usage guide
4. See [postman/HAPPY_PATH.md](postman/HAPPY_PATH.md) for detailed usage guide


---


