
import sys
import os

# Set dummy env vars to simulate Cloud Run environment partially
os.environ["PORT"] = "8080"
# Ensure we don't crash on auth if possible (simulating no-creds environment to see if code handles it)
os.environ["GOOGLE_CLOUD_PROJECT"] = "dummy-project"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"

try:
    print("Attempting to import app.fast_api_app...")
    import app.fast_api_app
    print("Import successful.")
except Exception as e:
    print(f"CRASH ON IMPORT: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("Attempting to load app object...")
try:
    app = app.fast_api_app.app
    print("App object loaded successfully.")
except Exception as e:
    print(f"CRASH ON APP ACCESS: {e}")
    traceback.print_exc()
    sys.exit(1)
