import sys
import os
from pathlib import Path

# Add the project root directory to the Python path
# so that api_server.py can be imported correctly
sys.path.append(str(Path(__file__).parent.parent))

from api_server import app

# Vercel handles the server execution. We just need to expose the 'app' instance.
