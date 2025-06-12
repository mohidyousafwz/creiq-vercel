#!/usr/bin/env python3
"""
Entry point to expose FastAPI app.
"""

from src.creiq.web_app import create_app

app = create_app()
