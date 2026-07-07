## Summary

<!-- What does this PR change and why? -->

## Test plan

- [ ] `cd backend && .venv/bin/python -m pytest`
- [ ] `cd frontend && npm run build` (if frontend changed)
- [ ] Manual verification steps:

## Checklist

- [ ] User-visible text is in `frontend/src/i18n/` (not hardcoded in JSX)
- [ ] No secrets or `.env` files committed
- [ ] DB changes include an Alembic migration (if applicable)
