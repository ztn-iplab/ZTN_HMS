# run.py or wsgi.py
import sys
import os
from main import create_app

# ✅ Make sure current directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

app = create_app()

