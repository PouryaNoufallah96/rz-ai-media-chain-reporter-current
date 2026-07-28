# ChainReporter Deployment Safety Lock

This folder is ChainReporter.

It must deploy only to VPS `5.75.207.209`.

It must use remote folder `/var/www/chainreporter`.

It must never deploy to the forbidden VPS `51.255.163.171`.

It must never deploy to the forbidden remote folder `/var/www/rzecosystem`.

The ChainReporter SQLite database lives at:

`/var/www/chainreporter/backend/data/app.db`

Do not copy, overwrite, move, or replace this SQLite database during deployment unless explicitly instructed.
