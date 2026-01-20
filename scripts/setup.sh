#!/bin/bash
# Development startup script

set -e

echo "🚀 Starting RMS Development Setup..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "📝 Creating .env from .env.development..."
    cp .env.development .env
fi

# Create logs directory
mkdir -p logs

echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Install dependencies: pip install -e .[dev]"
echo "2. Run migrations: alembic upgrade head"
echo "3. Start server: python -m app.main"
echo "4. View API docs: http://localhost:8000/docs"
