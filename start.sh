#!/bin/bash
# filepath: d:\Sony-Reaaltime\start.sh

# Activate the virtual environment (if applicable)
source venv/bin/activate

# Run the Flask app with Gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 app:app