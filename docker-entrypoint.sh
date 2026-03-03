#!/bin/sh
# Fix ownership of the data directory in case it was created by a previous
# root-owned container (e.g. after upgrading to a non-root image).
chown -R appuser:appuser /app/data
exec gosu appuser /app/.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
