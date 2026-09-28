"""SERVER SETTINGS for the online copy of the farm web (Render).

Gunicorn reads a file with this name by itself when it is started from this
folder, so the Start Command on the hosting site can stay short - even the bare
"gunicorn" or "gunicorn app:app" - and the app still listens where the host
expects it. It fixes the two things that silently break a hosting site:

  * bind     a hosting site tells the app which port to use through the PORT
             environment variable. Left to itself the server would sit on
             127.0.0.1:8000 and the host would say "failed to bind to port".
  * workers  the farm keeps everything in ONE sqlite file (backend/farm.db), so
             one worker is used unless you ask for more with FB_WORKERS. More
             workers on a small plan only bring "database is locked" errors.

Everything here can be changed from the hosting site's Environment settings
without touching the code: PORT, FB_WORKERS, FB_TIMEOUT, FB_LOG_LEVEL.
"""

import os


def _number(name, default):
    """Read a whole number from the environment, ignoring anything silly."""
    try:
        return max(1, int(str(os.environ.get(name) or '').strip()))
    except (TypeError, ValueError):
        return default


# The port the hosting site routes traffic to. Render always sets PORT; 10000 is
# what Render uses when it does not.
PORT = (os.environ.get('PORT') or '').strip() or '10000'

# Listen on every address, on the host's port. A "-b ..." on the command line
# simply overrides this.
bind = '0.0.0.0:%s' % PORT

# So that even a Start Command of just "gunicorn" finds the app.
wsgi_app = 'app:app'

workers = _number('FB_WORKERS', 1)
threads = _number('FB_THREADS', 1)
timeout = _number('FB_TIMEOUT', 120)
graceful_timeout = 30
keepalive = 5

# Send the logs to the hosting site's log console instead of to a file.
accesslog = '-'
errorlog = '-'
loglevel = (os.environ.get('FB_LOG_LEVEL') or 'info').strip() or 'info'
proc_name = 'fandb-poultry'
