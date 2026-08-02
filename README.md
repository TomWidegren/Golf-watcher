# Event Platform

Event Platform is a lightweight framework for monitoring live events from different data sources and notifying subscribers when something changes.

## Current Status

**Version:** 1.0.0

The first production-ready connector has been verified in live operation.

## Architecture

```
Event Platform
│
├── connectors/
│     ├── haninge.py
│     └── ...
│
├── watcher.py
├── config.yml
├── state.json
└── README.md
```

## Current Features

- Live event monitoring
- Change detection
- State persistence
- Push notifications using ntfy
- GitHub Actions scheduler

## Current Connectors

| Connector | Status |
|-----------|--------|
| Haninge Golf Club | ✅ Production |
| Tournytt | Planned refactoring |

## Roadmap

### Version 1.1

- Multiple connectors
- Connector interface
- Better logging
- Improved notifications

### Version 2.0

- Multiple sports
- Multiple subscribers
- Event Platform architecture
- Connector SDK

## License

Private project.
