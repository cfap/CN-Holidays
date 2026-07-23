.PHONY: generate check test

generate:
	python3 scripts/generate_calendar.py

check:
	python3 scripts/generate_calendar.py --check

test:
	python3 -m unittest discover -s tests -v
