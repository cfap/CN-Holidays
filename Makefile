.PHONY: generate check test new-year

generate:
	python3 scripts/generate_calendar.py

check:
	python3 scripts/generate_calendar.py --check

test:
	python3 -m unittest discover -s tests -v

new-year:
	python3 scripts/scaffold_year.py $(YEAR)
