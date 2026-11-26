# AKI License System

Flask online-license API + admin dashboard + PostgreSQL deployment for Render.

## Deploy
1. Create a Render Blueprint from this repository.
2. Review the proposed web service and PostgreSQL resource.
3. Enter `AKI_ADMIN_USERNAME` and `AKI_ADMIN_PASSWORD` during initial Blueprint setup.
4. Review the recurring PostgreSQL Basic charge before applying.
5. After deployment is live, open `/admin/login`.

The web service and PostgreSQL both use Render Free. IMPORTANT: Free Postgres has a 1 GB storage limit, no backups, and expires 30 days after creation. After expiry, it is inaccessible unless upgraded; after a further 14-day grace period, Render deletes it and all license records. This setup is for a temporary test only. Export or migrate the database before expiry. The Free web service also spins down after 15 minutes without inbound traffic and can take about a minute to wake.

## Features
- Generate 7 / 10 / 30-day or custom licenses (1–3650 days).
- Expiration starts on first successful activation.
- One license is bound to the first device ID that activates it.
- Online verification is required each time the client starts.
- Admin can search, view status, and revoke keys.
- Only SHA-256 key hashes are stored; the full key is displayed once.

## Source package
The application source is stored in `aki-source.tgz.b64`. The Render build command extracts it before installing dependencies. The bundle is base64-encoded gzip/tar, not encryption.

## Python client
After deployment, update `AKI_LICENSE_API` in `aki_license_client_snippet.py` to:
`https://YOUR-RENDER-SERVICE.onrender.com/api/verify`

Paste the client snippet near the top of your protected Python program. Keep admin credentials, database URLs, and session secrets on the server only.

## Local development
```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:AKI_SESSION_SECRET = "set-a-long-random-value"
$env:AKI_ADMIN_USERNAME = "admin"
$env:AKI_ADMIN_PASSWORD = "use-a-strong-unique-password"
$env:AKI_COOKIE_SECURE = "false"
py app.py
```
Open `http://127.0.0.1:10000/admin/login`.

## Security notes
- The repository currently contains no production credentials. Do not commit `.env`, service secrets, or database URLs.
- Make the repository Private in GitHub Settings if you prefer to restrict source visibility.
- The local device ID file can be copied by a determined user; this is a basic one-device binding, not hardware attestation.
- Client-side Python cannot be made impossible to reverse engineer. Server-side verification protects the key-generation secret, but cannot stop a skilled attacker from patching their local program.
