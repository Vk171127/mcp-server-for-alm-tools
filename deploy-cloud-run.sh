#!/bin/bash

# Deploy ALM Traceability MCP Server to Google Cloud Run
# Note: MCP servers typically run as services that AI agents connect to

set -e

# Configuration
PROJECT_ID="${PROJECT_ID:celtic-origin-472009-n5}"
REGION="${REGION:-us-central1}"
SERVICE_NAME="mcp-main"
IMAGE_NAME="gcr.io/celtic-origin-472009-n5/${SERVICE_NAME}"

echo "🚀 Deploying ALM Traceability MCP Server to Cloud Run"
echo "Project: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo "Service: ${SERVICE_NAME}"

# Check if gcloud is installed and authenticated
if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud CLI not found. Please install and authenticate first."
    exit 1
fi

# Set the project
gcloud config set project celtic-origin-472009-n5

# Enable required APIs
echo "📦 Enabling required Google Cloud APIs..."
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com

# Build the Docker image using Cloud Build
echo "🔨 Building Docker image with Cloud Build..."
gcloud builds submit --tag "${IMAGE_NAME}" .

# Deploy to Cloud Run
echo "🚀 Deploying to Cloud Run..."
gcloud run deploy "${SERVICE_NAME}" \
    --image="${IMAGE_NAME}" \
    --region="${REGION}" \
    --platform=managed \
    --allow-unauthenticated \
    --memory=1Gi \
    --cpu=1 \
    --timeout=300 \
    --max-instances=10 \
    --set-env-vars="ADO_ORG=${ADO_ORG:-}" \
    --set-env-vars="ADO_PROJECT=${ADO_PROJECT:-}" \
    --set-env-vars="ADO_PAT=${ADO_PAT:-}" \
    --set-env-vars="JIRA_URL=${JIRA_URL:-}" \
    --set-env-vars="JIRA_EMAIL=${JIRA_EMAIL:-}" \
    --set-env-vars="JIRA_TOKEN=${JIRA_TOKEN:-}"

# Get the service URL
SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" --region="${REGION}" --format="value(status.url)")

echo "✅ Deployment completed!"
echo "🌐 Service URL: ${SERVICE_URL}"
echo ""
echo "📋 Next steps:"
echo "1. Configure your AI agents to use this MCP server"
echo "2. Set environment variables for ADO/Jira credentials"
echo "3. Test the MCP tools with your agents"
echo ""
echo "🔧 MCP Server Configuration for AI Agents:"
echo "URL: ${SERVICE_URL}"
echo "Protocol: HTTP (MCP over HTTP)"
echo "Available Tools: MCP tools"
echo ""
echo "📄 Example agent configuration:"
echo "{"
echo "  \"mcpServers\": {"
echo "    \"mcp-main\": {"
echo "      \"url\": \"${SERVICE_URL}\","
echo "      \"type\": \"http\""
echo "    }"
echo "  }"
echo "}"
