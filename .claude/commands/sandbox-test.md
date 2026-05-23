# Sandbox Test

Build the Docker sandbox image and run a smoke test to verify the container works correctly.

## Steps

1. Build the sandbox image from `Dockerfile.sandbox`:
```bash
docker build -t autoreview-sandbox:latest -f Dockerfile.sandbox .
```

2. Smoke test — run `pytest --version` inside the container to confirm the image is healthy:
```bash
docker run --rm --network none autoreview-sandbox:latest pytest --version
```

3. Smoke test — run `bandit --version`:
```bash
docker run --rm --network none autoreview-sandbox:latest bandit --version
```

4. Smoke test — run `ruff --version`:
```bash
docker run --rm --network none autoreview-sandbox:latest ruff --version
```

Report: which steps passed, which failed, and the output of each command.
