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
2. Update .env file
2. Start the application -> code -> run migrations -> localhost/health
    Use debug for VSConde
3. Seed endpoint

POST /api/v1/seed
POST /api/v1/seed/cleanup

Testing
For testing without AI, set AI_ENABLED=false (won't require API key)