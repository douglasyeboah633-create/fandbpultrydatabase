"""Lets the F & B Poultry Farm web run on a hosting site (Vercel).

This file is only for the ONLINE copy. It does not change the farm app: it
loads the very same backend/app.py that run.bat runs on your PC.

Hosting sites hand the code to a folder that cannot be written to, but the farm
app must be able to write three things:

    farm.db        the database (daily reports, workers, records)
    uploads/       the mortality photos
    .secret_key    keeps logins valid after a restart

So the app is first copied into a writable temporary folder and loaded from
there. Nothing inside the app itself is touched.
"""

import importlib.util
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))

# Live data must never be overwritten by the copy of the code.
KEEP = {'farm.db', '.secret_key', '.env'}


def _writable_copy():
    """Copy backend/ + frontend/ to a folder we are allowed to write to.

    Returns the path of the backend folder to load, or None when those folders
    are not next to this file (then the app is loaded straight from here)."""
    if not os.path.isdir(os.path.join(HERE, 'backend')):
        return None
    base = os.path.join(tempfile.gettempdir(), 'fb_farm_web')
    try:
        for folder in ('backend', 'frontend'):
            src = os.path.join(HERE, folder)
            if not os.path.isdir(src):
                continue
            dst = os.path.join(base, folder)
            for root, dirs, files in os.walk(src):
                dirs[:] = [d for d in dirs if d not in ('__pycache__', '.git')]
                rel = os.path.relpath(root, src)
                target = dst if rel == '.' else os.path.join(dst, rel)
                os.makedirs(target, exist_ok=True)
                for name in files:
                    out = os.path.join(target, name)
                    if name in KEEP and os.path.exists(out):
                        continue
                    try:
                        shutil.copy2(os.path.join(root, name), out)
                    except Exception:
                        pass
        return os.path.join(base, 'backend')
    except Exception as exc:
        print('Could not prepare a writable working folder:', exc)
        return None


backend = _writable_copy()
if backend is None:
    backend = os.path.join(HERE, 'backend')

sys.path.insert(0, backend)
os.chdir(backend)

_spec = importlib.util.spec_from_file_location(
    'fb_farm_backend', os.path.join(backend, 'app.py'))
_backend = importlib.util.module_from_spec(_spec)
sys.modules['fb_farm_backend'] = _backend
_spec.loader.exec_module(_backend)

app = _backend.app          # the Flask app the hosting site serves
application = app           # some hosts look for this name instead
