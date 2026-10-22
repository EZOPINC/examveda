# OCI pilot deployment and operations

This is a deliberately small single-instance pilot layout for the existing Django monolith. It is a deployment baseline, not evidence of production readiness. Complete the Phase 5 restore, rate-limit, monitoring, and performance gates before public launch.

## Topology and traffic boundaries

Use an OCI-supported Ubuntu LTS image, a VCN with a public web subnet, one compute instance, Nginx, Gunicorn, and PostgreSQL on the same host for the initial pilot. OCI publishes Ubuntu 24.04 images; however, the approved Python 3.13 runtime must be sourced and security-maintained on the chosen image before provisioning. Do not silently use the OS Python if its version differs or use development-only repositories for production. Attach a private Object Storage bucket for off-host database and uploaded-media backups. A single host is a single failure domain for the app and database: a host or boot-volume failure takes the service offline until recovery. A same-host PostgreSQL database also makes routine maintenance a full service interruption. This design does not establish capacity or availability, and the INR 5,000–15,000/month target is not a cost guarantee.

Apply stateful ingress rules at both the OCI NSG/security list and host firewall:

| Protocol/port | Source | Purpose |
| --- | --- | --- |
| TCP 80 | `0.0.0.0/0` and `::/0` | HTTP to HTTPS redirect and initial certificate validation |
| TCP 443 | `0.0.0.0/0` and `::/0` | Public HTTPS |
| TCP 22 | Administrator's fixed public CIDR only | SSH administration; do not use `0.0.0.0/0` |
| TCP 5432 | No public ingress rule | PostgreSQL listens on loopback only |
| TCP 8000 | No ingress rule | Gunicorn binds to loopback only |

Permit only required outbound traffic, including DNS, NTP, OS/package updates, OCI Object Storage, and certificate renewal. Do not expose PostgreSQL through an Internet gateway. Set PostgreSQL `listen_addresses = '127.0.0.1'`; verify `pg_hba.conf` accepts the application role only from loopback and uses SCRAM authentication. Give the application role only the database/schema rights it needs; use a separately controlled release role for schema migrations.

The instance's dynamic group should be scoped to the backup bucket and only the object permissions needed to create/overwrite and verify uploads (`OBJECT_CREATE`, `OBJECT_OVERWRITE`, `OBJECT_INSPECT`, and `OBJECT_READ`); do not grant it `OBJECT_DELETE`. The backup job uses OCI instance-principal authentication so no OCI API key is stored on the host. Keep the bucket private, enable Object Storage's server-side encryption, configure and verify a retention/lifecycle policy, and alert on missing backups. Configure a separate operator identity for restore reads. Do not grant public bucket access. OCI policies can scope by `target.bucket.name` and condition on `request.permission`; validate the final policy in the target tenancy before enabling the timer.

The app currently stores `ResourceFile` uploads under `MEDIA_ROOT` and has no OCI Object Storage storage backend. Keep that directory outside all Nginx aliases and back it up off-host with the database. Do not move application uploads to Object Storage until a separately reviewed storage/delivery integration preserves publication and access checks. No restricted-file endpoint is added here.

## Files in this directory

- `nginx/wbpsc-platform.conf`: HTTPS reverse proxy, static alias, query-string-free access log, and no media alias. Replace the example host and certificate paths.
- `systemd/wbpsc-platform.service`: Gunicorn service bound to loopback, using the existing `config.wsgi:application` entry point and a root-managed environment file.
- `scripts/wbpsc-backup-to-oci.sh`, `systemd/wbpsc-backup.service`, and `systemd/wbpsc-backup.timer`: daily PostgreSQL custom-format dump and uploaded-media archive, uploaded to a private bucket using instance principals.

The initial two Gunicorn workers are a conservative starting point only. Tune worker count from memory and latency measurements; each worker consumes memory. Do not infer concurrent-user capacity from this configuration.

## Provisioning checklist

1. Select OCI region, compartment, Ubuntu LTS image, VM shape, boot volume, domain, and public IP. Check current OCI pricing and free-tier eligibility before provisioning; stop if any selected resource is billable without approval. No OCI resources are created by this repository change.
2. Create a VCN/subnet, internet gateway and route, NSG rules as above, and a reserved public IP if the DNS plan needs one. Add the instance to a dynamic group with a bucket-scoped policy for the backup job. Create a private bucket and retention rule.
3. Point the domain A/AAAA records to the VM. Confirm DNS from outside the VCN. Create a non-root SSH admin, disable password SSH after key access is verified, install security updates, enable the host firewall, and restrict SSH to the admin CIDR.
4. Install Python 3.13, PostgreSQL 18, Nginx, OCI CLI, PostgreSQL client utilities, and Certbot from supported repositories. Verify package sources and versions. Enable PostgreSQL local-only listening and SCRAM auth. Use separate runtime and release roles; keep credentials only in protected environment files. For example, interactively create roles and let `\\password` prompt for each secret:

   ```sql
   CREATE ROLE wbpsc_release LOGIN;
   \\password wbpsc_release
   CREATE ROLE wbpsc_app LOGIN;
   \\password wbpsc_app
   CREATE DATABASE wbpsc_mock_platform OWNER wbpsc_release ENCODING 'UTF8';
   ```

   Then connect as `wbpsc_release` and grant `CONNECT` on the database, `USAGE` on schema `public`, `SELECT, INSERT, UPDATE, DELETE` on all tables, and `USAGE, SELECT, UPDATE` on all sequences to `wbpsc_app`. Set matching default privileges for future tables and sequences before applying migrations. The app role needs no DDL rights; use the release role in the temporary migration environment.
5. Create system user/group `wbpsc-platform`, release directories `/srv/wbpsc-platform/releases/` and `/srv/wbpsc-platform/shared/media/`, and virtual environment `/srv/wbpsc-platform/venv/`. Deploy a reviewed Git revision into a new release directory; install pinned `requirements.txt` there. Link its `media` directory to the shared media directory.
6. Create `/etc/wbpsc-platform/environment` as root-owned mode `0600`. Set `DJANGO_SETTINGS_MODULE=config.settings.production`, a newly generated `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS` to exact public hostnames, and `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST=127.0.0.1`, `DB_PORT=5432`. Do not copy `.env` from a workstation or put real values in Git, shell history, or deployment logs. Add `OCI_BUCKET_NAME` and `OCI_REGION` for the backup timer only if instance-principal access is configured.
7. Before changing the active release, take a database and media backup using the reviewed backup procedure. Set `current` to the new release only after its code and Python dependencies are present.
8. In the new release, run `python manage.py check --deploy`, `python manage.py check --database default`, and `python manage.py migrate --plan` with the production environment. Review migrations; then apply with the release role. Run `python manage.py collectstatic --noinput`. Do not run demo-data seeding in production.
9. Obtain the TLS certificate with Certbot after DNS and port 80 are verified. For first issuance, stop Nginx and run `sudo certbot certonly --standalone -d example.com -d www.example.com`; install `nginx/wbpsc-platform.conf` with the actual names and certificate paths; then test `nginx -t` and enable/reload Nginx. Enable the Certbot renewal timer and configure a deploy hook to reload Nginx after renewal. Install and enable the Gunicorn service. Confirm Gunicorn listens only on `127.0.0.1:8000` and that ports 5432 and 8000 are not allowed at OCI or host firewalls.
10. Install the backup script at `/usr/local/sbin/wbpsc-backup-to-oci.sh` with root ownership and mode `0750`; install the backup service and timer units; run the service once manually and verify both objects in the private bucket. Enable the timer only after a restore rehearsal succeeds.

## Production environment and migration safety

The existing `config.settings.production` requires a non-empty secret, exact allowed hosts, and PostgreSQL connection values; it sets `DEBUG=False`, HTTPS redirect, secure session/CSRF cookies, trusted proxy scheme handling, HSTS, `nosniff`, and same-origin referrer policy. Gunicorn must be reachable only over loopback from Nginx. Nginx overwrites `X-Forwarded-Proto` with `https`; never accept that header from a direct public client. Do not enable HSTS subdomains or preload until all subdomains are confirmed HTTPS-only.

For each release, first run tests and deploy checks in CI or a disposable PostgreSQL environment. On the host: back up DB and media; upload code to a new release directory; install pinned dependencies; run `migrate --plan`; review and apply migrations; run `collectstatic`; change the `current` symlink; restart Gunicorn; inspect logs and smoke tests. Do not run migrations automatically in service startup. Prefer additive, backward-compatible schema changes. If a migration is destructive or incompatible with the prior code, split it across releases and require a tested restore plan.

Run management commands as short-lived systemd jobs so systemd reads the root-protected environment file without printing it. Use `/etc/wbpsc-platform/release-environment` instead for `migrate` commands; it contains the same Django settings values but uses the release DB role.

### Admin account and database consistency

Django admin, Django authentication, and the platform's application models all use the same Django database alias, `default`. This project has no database router or separate admin database. The `config.settings.production` settings define `default` as PostgreSQL and have no SQLite fallback. A superuser created with a different settings module or different `DB_NAME`/`DB_HOST`/`DB_USER` environment can therefore exist in a different database from the one Gunicorn serves. A `.env` file is not loaded automatically.

First confirm which environment file Gunicorn uses without printing its contents:

```sh
sudo systemctl show wbpsc-platform --property=EnvironmentFiles --no-pager
```

The expected runtime file is `/etc/wbpsc-platform/environment`. Use that exact file and the same release path/virtualenv for a read-only check of the effective Django settings and connected database identity. This prints database identifiers only, never a password:

```sh
sudo systemd-run --wait --pipe --collect --unit=wbpsc-db-identity \
  -p User=wbpsc-platform -p WorkingDirectory=/srv/wbpsc-platform/current \
  -p EnvironmentFile=/etc/wbpsc-platform/environment \
  /srv/wbpsc-platform/venv/bin/python manage.py shell -c \
  'import os; from django.db import connection; connection.ensure_connection(); print({"settings_module": os.environ.get("DJANGO_SETTINGS_MODULE"), "alias": "default", "engine": connection.settings_dict["ENGINE"], "name": connection.settings_dict["NAME"], "host": connection.settings_dict["HOST"], "port": connection.settings_dict["PORT"]})'
```

Compare the reported database name, host, and port with the intended production database. The command uses Gunicorn's environment file, so it is the relevant identity for the deployed app. Do not use the release environment for user creation: it may use a different PostgreSQL role and exists only for schema migrations.

If the account may already exist in this same database, inspect only its access flags (replace the username; do not print the whole user object or password fields):

```sh
sudo systemd-run --wait --pipe --collect --unit=wbpsc-admin-user-check \
  -p User=wbpsc-platform -p WorkingDirectory=/srv/wbpsc-platform/current \
  -p EnvironmentFile=/etc/wbpsc-platform/environment \
  /srv/wbpsc-platform/venv/bin/python manage.py shell -c \
  'from django.contrib.auth import get_user_model; print(get_user_model().objects.filter(username="ADMIN_USERNAME").values("is_active", "is_staff", "is_superuser").first())'
```

If no record is returned, create the admin user in the same runtime database, not from an SSH shell with an assumed settings module. This prompts interactively and does not put the password in shell history:

```sh
sudo systemd-run --wait --pty --collect --unit=wbpsc-create-superuser \
  -p User=wbpsc-platform -p WorkingDirectory=/srv/wbpsc-platform/current \
  -p EnvironmentFile=/etc/wbpsc-platform/environment \
  /srv/wbpsc-platform/venv/bin/python manage.py createsuperuser
```

If the account exists but its password is uncertain, run `manage.py changepassword ADMIN_USERNAME` in the same `systemd-run` form with the same `EnvironmentFile`; it prompts for the new password. Never create or reset an administrator account by editing database rows directly. A login form reporting invalid credentials points to a rejected password/account or a database mismatch; a CSRF 403 or repeated login redirect should be investigated as a proxy, HTTPS, cookie, or session issue instead. See [the troubleshooting guide](../TROUBLESHOOTING.md).

```sh
sudo systemd-run --wait --pipe --collect --unit=wbpsc-deploy-check \
  -p User=wbpsc-platform -p WorkingDirectory=/srv/wbpsc-platform/current \
  -p EnvironmentFile=/etc/wbpsc-platform/environment \
  /srv/wbpsc-platform/venv/bin/python manage.py check --deploy
sudo systemd-run --wait --pipe --collect --unit=wbpsc-migration-plan \
  -p User=wbpsc-platform -p WorkingDirectory=/srv/wbpsc-platform/current \
  -p EnvironmentFile=/etc/wbpsc-platform/release-environment \
  /srv/wbpsc-platform/venv/bin/python manage.py migrate --plan
sudo systemd-run --wait --pipe --collect --unit=wbpsc-collectstatic \
  -p User=wbpsc-platform -p WorkingDirectory=/srv/wbpsc-platform/current \
  -p EnvironmentFile=/etc/wbpsc-platform/environment \
  /srv/wbpsc-platform/venv/bin/python manage.py collectstatic --noinput
sudo systemctl restart wbpsc-platform
sudo systemctl status wbpsc-platform --no-pager
sudo journalctl -u wbpsc-platform -n 100 --no-pager
curl --fail --silent --show-error https://example.com/health/
```

Replace abbreviated service names with `wbpsc-platform` in the remaining commands. To apply migrations, review the plan, ensure the backup succeeded, and run an analogous short-lived job with `release-environment` and `manage.py migrate`. Never print a protected environment file or include it in command output.

## Backup, restore rehearsal, retention

The backup timer creates a custom-format PostgreSQL dump and an archive of `shared/media`, then uploads both to the private Object Storage bucket. Use Object Storage lifecycle rules for a documented retention period (proposed initial value: 35 daily copies, subject to cost and recovery requirements). Verify upload time, object size, and the timer's last result. A backup is not considered reliable until restoration is tested into a separate disposable environment.

Restore rehearsal: download a selected DB dump and media archive to a disposable Linux host/database; create a new empty verification database (never restore over production); restore with `pg_restore --no-owner --dbname=<verification-db> <dump>` using an appropriately privileged restore role; unpack media into a fresh directory; point a temporary copy of the app to that DB/media; run `manage.py check --database default`, inspect migration state and representative users/content/attempt scores, and exercise public pages, admin login, draft invisibility, and protected-file behavior. Record backup age (recovery point), restore duration (recovery time), object checksums/sizes, and results. Remove only the disposable environment after recording evidence. Repeat after significant schema changes and regularly thereafter.

## Health, monitoring, logs, and incident response

- Use `/health/` for a low-information application-process check; it intentionally does not prove PostgreSQL availability. Monitor PostgreSQL separately with `manage.py check --database default` in a controlled operator check and host-level service/connection alarms.
- Enable OCI Compute platform metrics and OCI Monitoring alarms for instance status, sustained CPU/memory pressure, disk usage, and network availability. Install/configure the OCI management agent if guest memory/disk metrics are required. Add an external HTTPS uptime check for `/health/`.
- Alert on systemd service failure, repeated Nginx 5xx responses, disk below 20% free, PostgreSQL unavailable, and backup timer/upload failure. Treat these initial thresholds as operator starting points and tune using baseline measurements.
- Review `journalctl -u wbp...` (the unit is `wbpsc-platform`) and Nginx logs. Configure bounded journald retention and log rotation. The Nginx format records `$uri` without query strings. Do not add passwords, cookies, request bodies, session IDs, or exam answers to logs.
- Incident sequence: acknowledge/record impact; check OCI instance/monitoring, disk, PostgreSQL, Gunicorn and Nginx; preserve logs; stop unsafe deploys; restore service using rollback steps; escalate suspected credential exposure by rotating secrets and reviewing access; record timeline and follow-up.

Rate limiting for authentication and high-impact exam routes remains an open Phase 5 launch item. Validate suitable limits and shared-IP behavior before enabling edge rate limits; do not assume this configuration solves abuse protection.

## Smoke and security checks

After each deploy, verify HTTPS redirect and certificate chain; `/health/` returns only `ok`; home, Free Study Materials, login, and public mock-test pages return expected codes; static CSS/JS load; an authorized administrator can reach `/admin/`; an anonymous request to a known draft returns 404; a student cannot read another user's attempt; restricted file URLs remain unavailable; public PDFs are served only through the approved Django route; `DEBUG` is false; and secure cookies are set on authenticated responses. Check Nginx/Gunicorn/PostgreSQL listeners and OCI security rules. Never use real student data for first-run smoke tests.

## Rollback

Keep the previous release directory and record the active release identifier. For an application-only failure with backward-compatible schema, point `current` back to the previous release, restart Gunicorn, run health/page checks, and inspect logs. Do not delete a release or database during incident response. If schema migrations have already run, do not blindly reverse them: determine whether the migration is reversible and compatible, preserve a fresh backup, and prefer a forward fix. Restore database/media only into a separate recovery target first; production restore requires an approved incident decision and documented data-loss window. A single VM has no automatic failover.

## Evidence still required before public launch

- A real OCI deployment and domain/DNS/TLS verification.
- `check --deploy` and DB checks on the deployed environment with real hostnames and strong operator-generated secrets.
- An actual Object Storage upload, scheduled backup, and successful isolated restore with recorded recovery point/time.
- Verification of OCI and host firewall rules, database/Gunicorn bind addresses, admin/draft/restricted-file behavior, and rollback.
- Monitoring alarms and alert delivery exercised; rate-limit behavior tested; authorized staging load test with synthetic users.
- Verified monthly OCI cost, VM shape/resource baseline, and agreed availability/recovery objectives.

## References

- [Django deployment checklist](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/)
- [Gunicorn deployment guidance](https://docs.gunicorn.org/en/stable/deploy.html)
- [OCI security lists](https://docs.oracle.com/en-us/iaas/Content/Network/Concepts/securitylists.htm)
- [OCI Object Storage CLI upload](https://docs.oracle.com/en-us/iaas/tools/oci-cli/latest/oci_cli_docs/cmdref/os/object/put.html)
- [OCI Object Storage permissions and bucket policy conditions](https://docs.oracle.com/en-us/iaas/Content/Identity/Reference/objectstoragepolicyreference.htm)
- [OCI Ubuntu 24.04 images](https://docs.oracle.com/en-us/iaas/images/ubuntu-2404/)
