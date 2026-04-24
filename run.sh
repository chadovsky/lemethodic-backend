#!/bin/bash
pip install -r requirements.txt --break-system-packages -q
# Dev mode:
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
