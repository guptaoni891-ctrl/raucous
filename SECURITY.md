# Security policy

## Reporting a vulnerability

Please open a private GitHub security advisory rather than a public issue.
Include affected versions, reproduction steps and the expected impact.

## Credential handling

VinylPulse uses Spotify PKCE and does not require a client secret. Never commit
OAuth cache files, `.env` files or access/refresh tokens.
