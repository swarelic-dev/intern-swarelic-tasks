# Exercise 4.2 — Rules engine

Pure Python, no database or web service. Stable priority ordering, first-match semantics, strict JSON loading, and immutable action/condition descriptions. The supplied after-hours example uses a mutually impossible AND condition (`hour >= 21` and `hour <= 8`); the sample config fixes this using two separate rules because the exercise requires AND within a rule.

```powershell
python -m pip install -r requirements.txt
python -m pytest tests -v
```

Configuration: `config/rules.json`; no secrets or external services. Pass an explicit context dictionary to `RulesEngine.evaluate()`. Action execution is intentionally outside the engine.
