# InfoTech in the existing PythonAnywhere Web App

The student guide is served by Django at `/infotech/`. Its source lives in
`backend/infotech/`; the original standalone local project is retained.
Blog API `/api/v1/` and admin `/admin/` keep their existing routes.

InfoTech has a URL namespace, templates under `infotech/`, static assets under
`/static/infotech/`, and its own SQLite database. The database router sends only
the `courses` app's tables to the `infotech` database. The app label is retained
for compatibility with the original migration history and data. InfoTech's
access and language session keys are distinct; locking it retains admin login.
Both sites share the Django process and hosting resource limits.

## Configure

Set in the server's existing `backend/.env`:

```dotenv
INFOTECH_ENABLED=true
INFOTECH_REQUIRE_PASSWORD=false
INFOTECH_PASSWORD=<shared-access-password>
INFOTECH_DATABASE_PATH=/home/jdChen3398/Hajiwo.github.io/backend/infotech.sqlite3
```

The feature defaults to disabled. Password access is temporarily disabled:
visitors can view, add and edit content directly. To restore the existing shared
password gate, set `INFOTECH_REQUIRE_PASSWORD=true` and reload. In that mode,
an unconfigured password returns 503. Passwords and databases must not be committed.

## Initial data transfer

Export only courses, links and tips from the original local project:

```sh
cd "/Users/dong/Documents/Projects/Github/InfoTech info"
.venv/bin/python manage.py dumpdata courses --indent 2 --output /tmp/infotech-initial.json
```

Upload this private fixture to PythonAnywhere. Before the first import, confirm
the new InfoTech database has no content. `loaddata` retains primary keys and
would overwrite matching rows if repeated after users start editing.
Keep a backup of both databases before upgrades.

```sh
cd /home/jdChen3398/Hajiwo.github.io
git pull --ff-only origin main
backend/.venv/bin/python backend/manage.py migrate
backend/.venv/bin/python backend/manage.py migrate --database=infotech
backend/.venv/bin/python backend/manage.py loaddata /home/jdChen3398/infotech-initial.json --database=infotech
backend/.venv/bin/python backend/manage.py collectstatic --noinput
backend/.venv/bin/python backend/manage.py check
```

For later deployments omit `loaddata`. Reload the existing Web App using the
Web tab. Its existing `/static/` mapping to `backend/staticfiles/` also serves
the namespaced InfoTech assets. Check entry, password access, course/link/tip
forms, language and lock; then check the existing article API and admin.
Disable `INFOTECH_ENABLED` and reload to remove the route without deleting data.

## Local verification

```sh
INFOTECH_ENABLED=true backend/.venv/bin/python backend/manage.py test infotech blog
INFOTECH_ENABLED=true backend/.venv/bin/python backend/manage.py makemigrations --check --dry-run
```
