# Documentation Index

**Project Documentation v1.0**  
**Last Updated:** January 20, 2026

## Overview

This documentation set provides comprehensive guidance for building and maintaining a FastAPI + GraphQL + SQLAlchemy application following SOLID principles and vertical slice architecture.

---

## Quick Start

1. **New to the project?** Start with [.copilot-instructions.md](../.copilot-instructions.md) for quick reference
2. **Setting up infrastructure?** See [Scaffolding-Guide.md](./Scaffolding-Guide.md)
3. **Need implementation examples?** Check [Definitions/Patterns.md](./Definitions/Patterns.md)
4. **Understanding the architecture?** Read [Architecture.md](./Architecture.md)

---

## Documentation Files

### [.copilot-instructions.md](../.copilot-instructions.md)

**Purpose:** Quick reference for AI-assisted development and daily coding

**Use when:**
- Writing new code
- Reviewing pull requests
- Onboarding new developers
- Resolving naming/structure questions

**Key topics:**
- SOLID principles enforcement
- Naming conventions (PascalCase, snake_case, camelCase)
- Folder structure template
- Quick decision matrix
- Common anti-patterns

---

### [Architecture.md](./Architecture.md)

**Purpose:** System-level architecture and design decisions

**Use when:**
- Designing new features
- Understanding data flow
- Planning infrastructure
- Making technology choices

**Key topics:**
- Vertical slice organization
- Multi-layer design (REST/GraphQL → Service → Repository → Models)
- Multi-tenancy strategy
- Transaction management
- N+1 query prevention
- AI integration patterns
- Recommended technology stack
- Middleware vs dependencies
- Performance optimization

---

### [Definitions/Patterns.md](./Definitions/Patterns.md)

**Purpose:** Detailed implementation patterns with working code examples

**Use when:**
- Implementing a specific pattern
- Solving a known problem (N+1, idempotency, etc.)
- Learning best practices
- Creating reusable components

**Key topics:**
- Pydantic alias generator (camelCase/snake_case bridge)
- Base classes (BaseSchema, BaseRepository, BaseService)
- Repository pattern implementation
- Service layer pattern
- Dependency injection strategies
- GraphQL DataLoader pattern
- Multi-tenancy enforcement
- Idempotency pattern
- Testing patterns (unit, integration, API)

---

### [Scaffolding-Guide.md](./Scaffolding-Guide.md)

**Purpose:** Step-by-step code generation and project setup

**Use when:**
- Starting a new project
- Adding a new domain/feature
- Setting up infrastructure
- Creating base classes

**Key topics:**
- Project initialization
- Base infrastructure setup (database, logging, middleware)
- Adding a new domain (12-step process)
- Domain checklist
- Code templates
- Testing templates

---

## Documentation Structure

```
docs/
├── README.md                    # This file - documentation index
├── Architecture.md              # System architecture and design
├── Scaffolding-Guide.md        # Project setup and code generation
└── Definitions/
    └── Patterns.md             # Implementation patterns with code

../.copilot-instructions.md     # Quick reference (workspace root)
```

---

## Quick Reference Tables

### When to Use Which Document

| Need | Document | Section |
|------|----------|---------|
| Class naming convention | .copilot-instructions.md | Naming Conventions |
| Folder structure | .copilot-instructions.md | Project Structure |
| Why vertical slices? | Architecture.md | Architectural Principles |
| Multi-tenancy design | Architecture.md | Multi-Tenancy Architecture |
| Pydantic camelCase bridge | Definitions/Patterns.md | Naming Conventions & Bridge |
| Prevent N+1 in GraphQL | Definitions/Patterns.md | GraphQL DataLoader Pattern |
| Implement idempotency | Definitions/Patterns.md | Idempotency Pattern |
| Create new domain | Scaffolding-Guide.md | Adding a New Domain |
| Setup database | Scaffolding-Guide.md | Base Infrastructure Setup |
| Testing strategy | Definitions/Patterns.md | Testing Patterns |

### Common Tasks

| Task | Steps |
|------|-------|
| **Add new feature** | 1. Review Architecture.md for design principles<br>2. Use Scaffolding-Guide.md to create domain structure<br>3. Reference Patterns.md for implementations<br>4. Follow .copilot-instructions.md for naming |
| **Optimize slow query** | 1. Check Architecture.md → N+1 Prevention<br>2. For REST: Use eager loading (Patterns.md)<br>3. For GraphQL: Implement DataLoader (Patterns.md) |
| **Add authentication** | 1. See Architecture.md → Middleware vs Dependencies<br>2. Implement auth dependency (Patterns.md)<br>3. Create auth domain (Scaffolding-Guide.md) |
| **Setup new project** | 1. Follow Scaffolding-Guide.md → Project Initialization<br>2. Setup infrastructure (Scaffolding-Guide.md)<br>3. Review Architecture.md for understanding<br>4. Keep .copilot-instructions.md open while coding |

---

## Version History

### v1.0 - January 20, 2026
- Initial documentation set
- Complete architecture guidelines
- Implementation patterns with code examples
- Scaffolding templates and checklists

---

## Contributing to Documentation

When updating these docs:

1. **Update version number** at the top of the file
2. **Update "Last Updated" date** to current date
3. **Update this README.md** if you add/remove sections
4. **Maintain consistency** across all documents
5. **Keep code examples** working and tested

---

## Support

For questions or clarifications:
- Review the relevant documentation file
- Check the Quick Reference Tables above
- Refer to inline code comments in base classes
- Consult the decision matrices in each guide

---

**Remember:** These documents are living guides. Update them as patterns evolve and new best practices emerge.
