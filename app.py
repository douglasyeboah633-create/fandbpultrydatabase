"""ENTRY POINT for the ONLINE copy of the farm web (Render, and any host that
starts the server from the project root).

The real application lives in backend/app.py. On your own PC run.bat starts it
from inside the backend folder, so the file is simply "app.py" there.

A hosting site starts the server from the ROOT folder instead, usually with

    gunicorn app:app

That failed on Render with

    ModuleNotFoundError: No module named 'app'

because this root folder had no app.py at all - only backend/app.py. This file
is the missing piece: it loads the very same backend/app.py (nothing about the
farm app changes) and hands the Flask app to the server, so all of these work
as-is, whichever one the hosting site is set to:

    gunicorn                                (uses gunicorn.conf.py)
    gunicorn app:app
    gunicorn -b 0.0.0.0:$PORT app:app
    gunicorn wsgi:app

To run the farm on your PC you still just double-click run.bat, or use
"cd backend" then "python app.py" - that path also keeps the one-server-only
guard, which this file deliberately does not touch.

The database, the photos and the login key stay exactly where backend/app.py
puts them (that file already falls back to a writable folder when the folder it
lives in cannot be written to).
"""

import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(HERE, 'backend')
BACKEND_APP = os.path.join(BACKEND_DIR, 'app.py')

if not os.path.isfile(BACKEND_APP):
    raise ImportError(
        'app.py could not find backend/app.py next to it. The farm web must be '
        'uploaded as a whole folder - both backend/ and frontend/ are needed.')

# backend/app.py starts with "from models import ...", so its own folder must be
# on the import path before it runs.
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# Load it under our own name. The file we are loading is called app.py and so is
# this one, so a plain "import app" would just load this file over and over.
_spec = importlib.util.spec_from_file_location('fb_farm_backend', BACKEND_APP)
_backend = importlib.util.module_from_spec(_spec)
sys.modules['fb_farm_backend'] = _backend
_spec.loader.exec_module(_backend)

app = _backend.app          # the Flask app the hosting site serves
application = app           # some hosts look for this name instead
