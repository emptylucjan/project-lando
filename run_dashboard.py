"""
Run the dashboard web server.
Usage: python run_dashboard.py
"""
import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from dashboard.app import app

if __name__ == "__main__":
    print("=" * 50)
    print("Zalando Scraper Dashboard")
    print("http://localhost:5000")
    print("=" * 50)
    app.run(debug=True, port=5000)
