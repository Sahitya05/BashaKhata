# Deployment preparation — not deployed

The working build is a local, single-shop SQLite application. Do not put its
SQLite ledger on Streamlit Community Cloud's temporary filesystem. Hosted mode
is intentionally blocked. The optional local password is not tenant isolation.

## Required next implementation milestone

1. Provision a PostgreSQL database (for example Supabase) in an owner-controlled
   account. Keep its connection string in Streamlit secrets, not Git or chat.
2. Add a PostgreSQL repository implementation and schema migration. Port the
   ledger contract tests; test concurrent settlement and duplicate requests on
   PostgreSQL itself. Do not assume SQLite tests establish PostgreSQL behavior.
3. Configure an identity provider; map authenticated identities to authorized
   shop IDs on the server. Scope every account, transaction, export, and request
   key to that shop. Add cross-shop read/write denial tests, logout, and session
   expiry. Require TLS and apply least-privilege database roles.
4. Add backups and exercise a restore. Deploy a separate fictional demo database.
5. After these checks pass, replace the hosted-mode blocker. Change the server
   binding for the deployment environment, keeping XSRF protection enabled.

## Owner actions after the hosting milestone is verified

- Authorize pushing the reviewed commit to the existing GitHub remote.
- In Streamlit Community Cloud, create an app from that repository, select the
  reviewed branch and `app.py`, and add credentials through Advanced settings /
  Secrets. Never upload the local secrets file to GitHub.
- Authorize deployment of the fictional demo; retain private records locally.
- Verify the actual URL in a separate browser: authentication, access isolation,
  four consecutive recordings, restart persistence, reversal and CSV download.
- Record the tested URL and date in PROJECT_STATUS.md.

There is no public deployment URL yet. Database provisioning alone does not
complete this milestone; the hosted adapter and access-control implementation
are still required.
