#!/bin/bash

# Define the root directory name
PROJECT_ROOT="signbridge-live"

echo "🚀 Creating project structure for '$PROJECT_ROOT'..."

# Create root directory and navigate into it
mkdir -p "$PROJECT_ROOT"
cd "$PROJECT_ROOT" || exit

# ==========================================
# 1. Create Directory Trees
# ==========================================
echo "📁 Creating directories..."

# Backend Directories
mkdir -p apps/backend/app/api/routes
mkdir -p apps/backend/app/api/dependencies
mkdir -p apps/backend/app/core
mkdir -p apps/backend/app/ai
mkdir -p apps/backend/app/cv
mkdir -p apps/backend/app/speech
mkdir -p apps/backend/app/services
mkdir -p apps/backend/app/models
mkdir -p apps/backend/app/schemas
mkdir -p apps/backend/app/utils
mkdir -p apps/backend/tests/api
mkdir -p apps/backend/tests/services
mkdir -p apps/backend/tests/ai

# Packages Directories
mkdir -p packages/shared
mkdir -p packages/types
mkdir -p packages/prompts

# Docs & Scripts Directories
mkdir -p docs/api
mkdir -p docs/architecture
mkdir -p docs/diagrams
mkdir -p scripts

# ==========================================
# 2. Create Files
# ==========================================
echo "📄 Creating files..."

# Root Level Files
touch .gitignore Makefile README.md LICENSE

# Backend Root Files
touch apps/backend/pyproject.toml apps/backend/uv.lock apps/backend/.python-version apps/backend/.env.example

# Backend App - API
touch apps/backend/app/api/__init__.py

# Backend App - Core
touch apps/backend/app/core/config.py
touch apps/backend/app/core/logging.py
touch apps/backend/app/core/security.py
touch apps/backend/app/core/redis.py
touch apps/backend/app/core/supabase.py
touch apps/backend/app/core/__init__.py

# Backend App - AI
touch apps/backend/app/ai/gemini.py
touch apps/backend/app/ai/prompts.py
touch apps/backend/app/ai/__init__.py

# Backend App - CV
touch apps/backend/app/cv/detector.py
touch apps/backend/app/cv/landmarks.py
touch apps/backend/app/cv/__init__.py

# Backend App - Speech
touch apps/backend/app/speech/stt.py
touch apps/backend/app/speech/tts.py
touch apps/backend/app/speech/__init__.py

# Backend App - Services
touch apps/backend/app/services/meeting.py
touch apps/backend/app/services/transcript.py
touch apps/backend/app/services/avatar.py
touch apps/backend/app/services/gesture.py
touch apps/backend/app/services/__init__.py

# Backend App - Models, Schemas, Utils, Main
touch apps/backend/app/models/__init__.py
touch apps/backend/app/schemas/__init__.py
touch apps/backend/app/utils/helpers.py
touch apps/backend/app/utils/constants.py
touch apps/backend/app/utils/__init__.py
touch apps/backend/app/main.py

# Scripts Files
touch scripts/setup.sh
touch scripts/run_backend.sh
touch scripts/lint.sh
touch scripts/format.sh

# ==========================================
# 3. Set Permissions
# ==========================================
echo "🔧 Setting executable permissions for scripts..."
chmod +x scripts/*.sh

echo "✅ Project structure created successfully in './$PROJECT_ROOT'!"