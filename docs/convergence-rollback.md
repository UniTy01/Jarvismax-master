# Convergence Rollback Playbook

## Quick Rollback
```bash
git revert HEAD --no-edit
docker compose restart jarvis
```

## Full Rollback to Known Good
```bash
git checkout <known_good_commit>
docker compose down && docker compose up -d
```

## Verify After Rollback
```bash
curl -sf https://jarvis.jarvismaxapp.co.uk/health
curl -sf https://jarvis.jarvismaxapp.co.uk/diagnostic -H "Authorization: Bearer $TOKEN"
```

## Feature Flag Rollback
Use feature flags in config/policy.yaml to disable specific capabilities without code changes:

Restart container after changes.

## Feature Flag Rollback

Use feature flags in config/policy.yaml to disable specific capabilities without code changes.
Set any feature to false and restart the container.

This allows partial rollback of new features without reverting code.
