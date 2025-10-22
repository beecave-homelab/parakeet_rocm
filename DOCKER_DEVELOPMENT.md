# Docker Development Setup

This guide explains how to use the development Docker environment with **hot-reloading** for faster iteration.

## Quick Start

```bash
# Build development image (only needed once, or when requirements-all.txt changes)
docker compose -f docker-compose.dev.yaml build

# Start development container with hot-reload
docker compose -f docker-compose.dev.yaml up

# WebUI available at: http://localhost:7861
```

## Key Features

### ✨ Hot-Reload (No Rebuild Needed)

Changes to these files sync **instantly** without rebuilding:

- ✅ **Python source code** (`parakeet_rocm/**/*.py`)
- ✅ **Scripts** (`scripts/**/*.py`)
- ✅ **Tests** (`tests/**/*.py`)
- ✅ **Configuration** (`.env`, `pyproject.toml`)

**Just save your file and refresh the browser!** No `docker compose build` required.

### 🚀 Fast Iteration Workflow

```bash
# 1. Edit code in your IDE
vim parakeet_rocm/webui/app.py

# 2. Save the file (Ctrl+S)

# 3. Restart the container (preserves dependency cache)
docker compose -f docker-compose.dev.yaml restart

# Changes are live! (usually < 5 seconds)
```

### 📦 Dependency Caching

The development image caches installed dependencies:

```bash
# Only rebuild if requirements-all.txt changes
docker compose -f docker-compose.dev.yaml build

# This is fast because dependencies are cached
```

**When to rebuild:**

- ✅ After updating `requirements-all.txt`
- ✅ After updating system dependencies (Dockerfile changes)
- ❌ NOT needed for code changes (hot-reload handles it)

## Usage

### Development WebUI (Default)

```bash
# Launch WebUI with debug mode enabled
docker compose -f docker-compose.dev.yaml up

# Access at: http://localhost:7861
```

### Watch Mode (Auto-Transcription)

Uncomment in `docker-compose.dev.yaml`:

```yaml
command: ["parakeet-rocm", "transcribe", "--watch", "/data/watch/", "--verbose"]
```

Then place audio files in `./data/watch/` and they'll be transcribed automatically.

### Interactive Shell (Manual Testing)

Uncomment in `docker-compose.dev.yaml`:

```yaml
command: ["bash"]
```

Then connect:

```bash
docker compose -f docker-compose.dev.yaml up -d
docker exec -it parakeet-rocm-dev bash

# Inside container:
parakeet-rocm transcribe /data/sample.wav
parakeet-rocm webui
pytest tests/unit/ -v
```

### Run Tests Inside Container

Uncomment in `docker-compose.dev.yaml`:

```yaml
command: ["pytest", "tests/unit/", "-v"]
```

Or run manually:

```bash
docker compose -f docker-compose.dev.yaml exec parakeet-rocm-dev pytest tests/unit/ -v
```

## Common Workflows

### Workflow 1: WebUI Development

```bash
# 1. Start dev container
docker compose -f docker-compose.dev.yaml up

# 2. Edit parakeet_rocm/webui/app.py in your IDE

# 3. Save the file

# 4. Restart container to reload code
docker compose -f docker-compose.dev.yaml restart

# 5. Refresh browser at http://localhost:7861
```

### Workflow 2: CLI Development

```bash
# Start container in shell mode
docker compose -f docker-compose.dev.yaml run --rm parakeet-rocm-dev bash

# Inside container, test CLI changes
parakeet-rocm transcribe /data/sample.wav --verbose
```

### Workflow 3: Testing Changes

```bash
# Edit code
vim parakeet_rocm/transcribe.py

# Run tests (hot-reload works for tests too)
docker compose -f docker-compose.dev.yaml exec parakeet-rocm-dev pytest tests/unit/ -v

# Or with coverage
docker compose -f docker-compose.dev.yaml exec parakeet-rocm-dev \
  pytest --cov=parakeet_rocm tests/unit/ -v
```

## Volume Mounts Explained

The development compose file mounts these volumes:

```yaml
volumes:
  # Source code (hot-reload enabled)
  - "./parakeet_rocm:/app/parakeet_rocm"       # Main package
  - "./scripts:/app/scripts"                   # Scripts
  - "./tests:/app/tests"                       # Tests
  
  # Configuration (read-only hot-reload)
  - "./pyproject.toml:/app/pyproject.toml:ro"
  - "./.env:/app/.env:ro"
  
  # Data directory
  - "./data:/data"                             # Transcription I/O
  
  # Cache prevention (avoid host pollution)
  - /app/parakeet_rocm/__pycache__             # Anonymous volume
  - /app/parakeet_rocm/**/__pycache__          # Prevent .pyc leakage
```

## Troubleshooting

### Issue: Changes Not Reflecting

**Solution 1**: Restart the container

```bash
docker compose -f docker-compose.dev.yaml restart
```

**Solution 2**: Check file is actually mounted

```bash
docker compose -f docker-compose.dev.yaml exec parakeet-rocm-dev \
  cat /app/parakeet_rocm/webui/app.py
```

**Solution 3**: Force reload by stopping and starting

```bash
docker compose -f docker-compose.dev.yaml down
docker compose -f docker-compose.dev.yaml up
```

### Issue: Module Import Errors

**Cause**: Package not installed in editable mode

**Solution**: Rebuild the image

```bash
docker compose -f docker-compose.dev.yaml build --no-cache
docker compose -f docker-compose.dev.yaml up
```

### Issue: Permission Errors

**Cause**: Docker creates files as root

**Solution**: Fix ownership (run on host)

```bash
sudo chown -R $USER:$USER ./parakeet_rocm ./data ./tests
```

### Issue: Slow Performance

**Cause**: Volume mount overhead on some systems (especially macOS)

**Solution 1**: Use `:cached` mount option (macOS)

```yaml
volumes:
  - "./parakeet_rocm:/app/parakeet_rocm:cached"
```

**Solution 2**: Use Docker Desktop with VirtioFS (macOS/Windows)

**Solution 3**: Develop inside the container using VS Code Remote Containers

## Differences from Production

| Aspect | Production (`docker-compose.yaml`) | Development (`docker-compose.dev.yaml`) |
|--------|-----------------------------------|----------------------------------------|
| **Source Code** | Copied into image | Mounted as volume (hot-reload) |
| **Install Mode** | `pip install -e .` (one-time) | `pip install -e .` (with mounted source) |
| **Debug Mode** | Off | On (`--debug`) |
| **Batch Size** | 1 (production) | 4 (faster testing) |
| **Chunk Length** | 120s (production) | 60s (faster testing) |
| **Restart Policy** | `unless-stopped` | `unless-stopped` |
| **Healthcheck** | Optional | Enabled (monitors WebUI) |

## Tips & Best Practices

### 1. Use `.dockerignore` to Speed Up Builds

Already configured, but ensure it includes:

```txt
**/__pycache__
**/*.pyc
**/*.pyo
.git
.pytest_cache
.coverage
*.egg-info
```

### 2. Layer Caching Strategy

The `Dockerfile.dev` is optimized for caching:

1. ✅ **System packages** (rarely change)
2. ✅ **Python dependencies** (change on `requirements-all.txt` updates)
3. ✅ **Package structure** (enables editable install)
4. ❌ **Source code** (mounted, not copied)

### 3. Rebuild Only When Needed

```bash
# ❌ DON'T: Rebuild for every code change
docker compose -f docker-compose.dev.yaml up --build

# ✅ DO: Rebuild only for dependency changes
# Edit requirements-all.txt
docker compose -f docker-compose.dev.yaml build

# ✅ DO: Just restart for code changes
docker compose -f docker-compose.dev.yaml restart
```

### 4. Use Smaller Test Datasets

Place small audio files in `./data/` for faster iteration:

```bash
# Use short clips (5-10 seconds) for testing
cp sample_short.wav data/test.wav

# Test transcription
docker compose -f docker-compose.dev.yaml exec parakeet-rocm-dev \
  parakeet-rocm transcribe /data/test.wav
```

### 5. Parallel Development

Run multiple containers for different tasks:

```bash
# Terminal 1: WebUI
docker compose -f docker-compose.dev.yaml up

# Terminal 2: Run tests
docker compose -f docker-compose.dev.yaml exec parakeet-rocm-dev pytest

# Terminal 3: Interactive shell
docker compose -f docker-compose.dev.yaml exec parakeet-rocm-dev bash
```

## Integration with IDEs

### VS Code

Install **Remote - Containers** extension, then:

1. Open project in VS Code
2. Command Palette → "Reopen in Container"
3. Edit code directly inside container
4. Zero sync delay!

### PyCharm Professional

1. Settings → Build, Execution, Deployment → Docker
2. Add Docker Compose configuration
3. Use `docker-compose.dev.yaml`
4. Enable automatic deployment

## Performance Comparison

| Action | Production Setup | Development Setup | Time Savings |
|--------|-----------------|-------------------|--------------|
| **Code change** | Rebuild + restart (2-5 min) | Save + restart (5-10s) | **~95% faster** |
| **Add dependency** | Rebuild (2-5 min) | Rebuild (2-5 min) | Same |
| **Test iteration** | Run outside container | Run inside (mounted) | **~90% faster** |

## Next Steps

- ✅ Start development: `docker compose -f docker-compose.dev.yaml up`
- ✅ Make code changes in your IDE
- ✅ See changes instantly (just restart container)
- ✅ Run tests without leaving Docker
- ✅ Only rebuild when dependencies change

Happy developing! 🚀
