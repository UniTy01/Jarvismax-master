# CI Spam Prevention

## Changes to deploy.yml

### 1. Path filtering — skip CI for docs-only changes
```yaml
paths-ignore:
  - 'docs/**'
  - '*.md'
  - 'LICENSE'
```

### 2. Concurrency group — cancel stale runs
```yaml
concurrency:
  group: deploy-production
  cancel-in-progress: true
```

### 3. Manual trigger
```yaml
workflow_dispatch:  # allows manual re-run from GitHub UI
```

### Effect
- Docs-only commits no longer trigger CI/deploy
- Rapid successive pushes cancel previous runs (no pile-up)
- Manual re-run available for debugging
