# docs/ - Documentation

Architecture documents, guides, and references.

## Key Documents

| File                   | Purpose                          |
| ---------------------- | -------------------------------- |
| `nats-architecture.md` | Inter-agent communication design |
| `nats-setup.md`        | How to run NATS locally          |

## reviews/

Post-implementation reviews and analysis documents.

## Documentation Conventions

1. **Architecture docs** - Explain design decisions and patterns
2. **Setup guides** - Step-by-step instructions
3. **Reviews** - Retrospectives on completed work

## NATS Documentation

The NATS message bus is central to agent coordination:

- **nats-architecture.md** - Subject hierarchy, message types, patterns
- **nats-setup.md** - Docker setup, monitoring, troubleshooting

## Related

- Plans: [plans/](../plans/AGENTS.md)
- Examples: [examples/](../examples/)
- NATS code: [src/coordination/](../src/coordination/AGENTS.md)
