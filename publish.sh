#!/bin/bash

# Publishing script for ALM Traceability MCP Server

set -e

echo "📦 Publishing ALM Traceability MCP Server..."

# Clean previous builds
echo "🧹 Cleaning previous builds..."
rm -rf build/ dist/ *.egg-info

# Build package
echo "🔨 Building package..."
python -m build

# Check package
echo "✓ Checking package..."
python -m twine check dist/*

# Upload to PyPI (uncomment when ready)
# read -p "Upload to PyPI? (y/n) " -n 1 -r
# echo
# if [[ $REPLY =~ ^[Yy]$ ]]
# then
#     echo "⬆️  Uploading to PyPI..."
#     python -m twine upload dist/*
# fi

# Upload to Test PyPI
read -p "Upload to Test PyPI? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then
    echo "⬆️  Uploading to Test PyPI..."
    python -m twine upload --repository testpypi dist/*
fi

echo ""
echo "✅ Build complete!"
echo ""
echo "Test installation:"
echo "pip install -i https://test.pypi.org/simple/ alm-traceability-mcp"
echo ""