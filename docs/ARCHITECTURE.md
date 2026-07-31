# Golf Watcher Architecture

## Current version

Golf Watcher monitors golf competition data and sends push notifications when something changes.

Current flow:

Tournytt / Min Golf
→ watcher.py
→ state.json
→ ntfy
→ iPhone notification

## Current responsibilities

- `watcher.py`: reads competition data and detects changes
- `state.json`: stores the last known state
- `ntfy`: delivers push notifications to the phone
- GitHub Actions: runs the watcher on a schedule and on demand

## Future platform direction

Golf Watcher is the first provider in a broader event platform.

Planned platform layers:

### Providers
- Golf
- Innebandy
- Hockey
- Other event sources

### Core
- Watches
- State
- Event detection
- Rule evaluation

### Notifications
- ntfy
- Email
- Future mobile app

## Design principle

The core platform should not depend on golf-specific logic.
Golf is the first use case, not the final product.
