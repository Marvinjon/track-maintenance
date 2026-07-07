# Security Policy

## Supported versions

Security fixes are applied to the latest release on the `main` branch.

## Reporting a vulnerability

Please **do not** open a public GitHub issue for security vulnerabilities.

Instead, report them privately by opening a [GitHub Security Advisory](https://github.com/Marvinjon/track-maintenance/security/advisories/new) or contacting the repository maintainer directly.

Include:

- A description of the issue and its impact
- Steps to reproduce
- Affected versions or commits, if known

We aim to acknowledge reports within a few business days.

## Scope notes

- This service integrates with Traccar via its REST API and webhooks. Vulnerabilities in Traccar itself should be reported to the [Traccar project](https://www.traccar.org/).
- The webhook endpoint must remain reachable only on localhost in production deployments (see `deploy/nginx.conf.example`).
