
import sys
import os

# Thêm root vào sys.path
sys.path.append(os.getcwd())

from backend.app.main import app

print("Listing all registered routes:")
for route in app.routes:
    print(f"{route.path} [{route.methods}]")
