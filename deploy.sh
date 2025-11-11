#!/bin/bash
set -e

# Configuration
PROJECT_ID="celtic-origin-472009-n5"
REGION="us-central1"
SERVICE_NAME="alm-traceability-server"

echo "🚀 Deploying ALM Traceability Server"
echo "===================================="
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "Service: $SERVICE_NAME"
echo ""

# 1. Set Google Cloud project
echo "📡 Setting Google Cloud project..."
gcloud config set project $PROJECT_ID

# 2. Enable required APIs
echo "🔧 Enabling required APIs..."
gcloud services enable cloudbuild.googleapis.com || true
gcloud services enable run.googleapis.com || true

# 3. Build and deploy in one step
echo "🏗️ Building and deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
    --source . \
    --region $REGION \
    --platform managed \
    --allow-unauthenticated \
    --memory 512Mi \
    --cpu 1 \
    --timeout 3600 \
    --max-instances 10 \
    --min-instances 0 \
    --port 8080

# 4. Get service URL
echo "🔍 Getting service URL..."
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region=$REGION --format="value(status.url)")

echo ""
echo "✅ Deployment complete!"
echo "======================================"
echo "Service URL: $SERVICE_URL"
echo ""
echo "Test endpoints:"
echo "  Health: $SERVICE_URL/health"
echo "  Docs: $SERVICE_URL/docs"
echo "  Root: $SERVICE_URL/"
echo ""
echo "🧪 Testing deployment..."
curl -f "$SERVICE_URL/health" && echo " ✅ Health check passed" || echo " ❌ Health check failed"
echo ""
echo "Your ADK agent can now connect to: $SERVICE_URL"
echo "======================================"