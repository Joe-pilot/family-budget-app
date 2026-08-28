# Security Policy

## Reporting a vulnerability

Please do not disclose security vulnerabilities in a public issue. Use GitHub's private vulnerability reporting feature on the repository's **Security** tab. Include the affected component, reproduction steps, impact, and any suggested mitigation. Do not include real credentials, financial records, or personal information in the report.

If private vulnerability reporting is unavailable, contact the repository owner through their public GitHub profile and ask for a private reporting channel.

## Deployment scope

Family Budget is intended for self-hosting on a trusted private network. A shared API key protects all financial routes, while the health endpoint remains public. Because the browser must receive the shared key, it does not provide per-user identity or protect against an authorized browser user. Deployments exposed outside a trusted network require additional controls such as TLS, individual authentication, rate limiting, and network policies.

## Secret handling

Never commit Telegram tokens, API keys, database passwords, populated `.env` files, Kubernetes Secrets, database dumps, logs containing transaction data, or private network details. If a credential is exposed, rotate it immediately; deleting it from the latest revision does not remove it from Git history.
