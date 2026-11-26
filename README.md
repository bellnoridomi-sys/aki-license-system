# AKI License System

Flask license API + admin dashboard + PostgreSQL deployment for Render.

This repository contains no production credentials. Configure all admin credentials and session secrets through Render Environment Variables.

## Deploy
1. Open Render and create a Blueprint from this repository.
2. Review the web service and PostgreSQL plan shown by Render.
3. Set the requested `AKI_ADMIN_USERNAME` and `AKI_ADMIN_PASSWORD` values in Render.
4. Apply only after reviewing the recurring database cost.
5. Once live, open `/admin/login`.

The web service is configured on the Free plan. PostgreSQL uses Basic storage so license records are not on the 30-day expiring Free database tier.

## License behavior
- Keys are generated only by the server and stored as SHA-256 hashes.
- Key expiry starts on first successful activation.
- Each key is bound to the first device ID that activates it.
- Every client launch must verify online.
- Admin can revoke a key at any time.

## Security
Use a unique strong admin password. Never add `.env`, database URLs, session secrets, or credentials to Git. The Python client contains no key-generation secret.

See `render.yaml` for infrastructure configuration.
