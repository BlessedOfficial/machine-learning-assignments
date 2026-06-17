PYTHON ?= .venv/Scripts/python.exe

.PHONY: eval eval-diff write-baseline

# Full pairwise run (API) + print delta vs baseline.json
eval:
	$(PYTHON) -m eval --pairwise-20 --no-judge-fallback --compare-baseline

# Offline diff: parse last console log, no API calls
eval-diff:
	$(PYTHON) -m eval --diff-baseline-log

# Refresh baseline.json from the last console log (offline)
write-baseline:
	$(PYTHON) -m eval --diff-baseline-log --write-baseline

replay:
	$(PYTHON) -m Observability.replay $(TRACE_ID) $(REPLAY_ARGS)
