#!/bin/bash
set -e

export PROJECT_ID="atomic-sled-477620-c2"
export REGION="us-central1"
export SERVICE_NAME="demo-rag-frontend"

echo "🔨 Building Docker image..."
docker build -t gcr.io/$PROJECT_ID/$SERVICE_NAME .

echo "📤 Pushing to Google Container Registry..."
docker push gcr.io/$PROJECT_ID/$SERVICE_NAME

echo "🚀 Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/$SERVICE_NAME:latest \
  --region=$REGION \
  --allow-unauthenticated \
  --cpu=1 \
  --memory=512Mi \
  --timeout=300 \
  --min-instances=0 \
  --max-instances=2 \
  --port=8080

echo "✅ Deployment complete!"
echo "🌐 Frontend URL:"
gcloud run services describe $SERVICE_NAME --region=$REGION --format="value(status.url)"