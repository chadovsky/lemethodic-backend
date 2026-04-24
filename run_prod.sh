#!/bin/bash
pip install -r requirements.txt --break-system-packages -q
gunicorn main:app -w 2 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
