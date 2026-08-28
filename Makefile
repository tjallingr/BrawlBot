PYTHON := venv/bin/python

install:
	$(PYTHON) -m pip install -r requirements.txt
	$(PYTHON) -m playwright install chromium

test:
	$(PYTHON) -m pytest scrape/tests/

scrape-ufcstats:
	$(PYTHON) -m scrape.cli ufcstats $(ARGS)

scrape-odds:
	$(PYTHON) -m scrape.cli bestfightodds $(ARGS)

.PHONY: install test scrape-ufcstats scrape-odds
