# Troubleshooting

## Django admin rejects a newly created production superuser

Django admin and the application use the same `default` database alias. In `config.settings.production`, that alias is PostgreSQL; there is no separate SQLite database for admin and no database router in this project. The admin login problem is therefore not explained by an application-level split between SQLite and PostgreSQL.

The live OCI cause cannot be confirmed from the repository alone. A common cause is that `createsuperuser` was run in an SSH shell with a different settings module or database environment than the Gunicorn systemd service. Django does not load `.env` automatically. A successful superuser command only proves that an account was created in the database selected by that command.

On the OCI host, compare the environment file configured for `wbpsc-platform` with the one used by the account-management command. Do not print or copy the protected environment file. The deployment guide's `wbpsc-db-identity` command runs Django using the Gunicorn runtime environment and reports only the settings module, database engine, name, host, and port. Use that same environment for the account flag check and, if needed, `createsuperuser` or `changepassword`.

Interpret the result carefully:

- A database name/host/port different from the intended production database indicates a configuration mismatch. Correct the systemd environment source only after confirming the intended database; do not reset or delete any database.
- No user row in the Gunicorn database means the account was created elsewhere or was not created successfully. Create it using the runtime environment file.
- A row with `is_active=False` or `is_staff=False` cannot sign in to Django admin. A superuser should also have `is_superuser=True`. Use the reviewed operator process to repair account status; do not edit database rows manually.
- The standard “Please enter the correct username and password for a staff account” response indicates rejected credentials or account status, and can also occur when the account is absent from the database Gunicorn uses.
- A CSRF 403, session loop, or login redirect is not evidence of a database mismatch. Check HTTPS proxy headers, secure-cookie settings, browser cookies, and session/database health.

Never share passwords, environment-file contents, secret values, session cookies, or full user records while diagnosing. Safe identifiers for a support report are the settings module, database engine/name/host/port, and the three account flags. The actual OCI database and account state must be checked on the instance by an authorized operator.
