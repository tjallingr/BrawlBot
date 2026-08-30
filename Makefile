PYTHON := venv/bin/python

install:
	$(PYTHON) -m pip install -r requirements.txt
	$(PYTHON) -m playwright install chromium

test:
	$(PYTHON) -m pytest

scrape-ufcstats:
	$(PYTHON) -m stages.scrape.cli ufcstats $(ARGS)

scrape-odds:
	$(PYTHON) -m stages.scrape.cli bestfightodds $(ARGS)

.PHONY: install test scrape-ufcstats scrape-odds
