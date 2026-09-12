dev:
	@echo "Start apps/web and apps/api separately during initial setup"

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
