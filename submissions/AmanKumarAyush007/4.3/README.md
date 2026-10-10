# Exercise 4.3 — Agent state machine

The state machine rejects invalid transitions, requires call IDs on incoming calls, records audit events, and tracks agent session metrics. Times are timezone-aware UTC. The implementation is local and synchronous: cross-process state synchronization and persistent event logging are intentionally outside the standalone exercise.

```powershell
python -m pip install -r requirements.txt
python -m pytest tests -v
```
