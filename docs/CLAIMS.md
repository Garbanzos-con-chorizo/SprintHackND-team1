# Claims on shared files

Add a row before editing anything outside your lane (shared config, dependency files, contracts). Delete your row when your PR is merged. Check here before touching shared files.

| Path | Who | Since | Why |
|------|-----|-------|-----|
| `server.py`, `Dockerfile`, `requirements-server.txt`, `.dockerignore` (new, root) | Victor | 2026-10-04 04:10 | decision 008: thin static server + Docker image |
