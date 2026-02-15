#!/bin/bash
set -e

# Configuration
export PROJECT_ID="atomic-sled-477620-c2"
export REGION="us-central1"
export SERVICE_NAME="demo-rag"
export INSTANCE_NAME="rag-postgres-db"

# Get Cloud SQL connection name
CONNECTION_NAME=$(gcloud sql instances describe $INSTANCE_NAME --format="value(connectionName)")
echo "📡 Cloud SQL Connection: $CONNECTION_NAME"

# Prompt for passwords (don't hardcode them!)
read -sp "Enter app_user password: " APP_PASSWORD
echo
read -sp "Enter JWT secret key: " JWT_SECRET
echo
read -sp "Enter Gemini API key: " GEMINI_API_KEY
echo

# Build image
echo "🔨 Building Docker image..."
gcloud builds submit --tag gcr.io/$PROJECT_ID/$SERVICE_NAME

# Deploy to Cloud Run
echo "🚀 Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/$SERVICE_NAME:latest \
  --region=$REGION \
  --platform=managed \
  --allow-unauthenticated \
  --memory=2Gi \
  --cpu=2 \
  --timeout=300 \
  --max-instances=10 \
  --add-cloudsql-instances=$CONNECTION_NAME \
  --set-env-vars="CLOUD_SQL_CONNECTION_NAME=$CONNECTION_NAME,POSTGRES_USER=app_user,POSTGRES_PASSWORD=$APP_PASSWORD,POSTGRES_DB=notes_db,JWT_SECRET_KEY=$JWT_SECRET,AUTH_USERNAME_1=tkaran2311,AUTH_PASSWORD_1=Indiathegreat@12,AUTH_USERNAME_2=ameetsonalkar,AUTH_PASSWORD_2=WisdomOverInfo@12345,AUTH_USERNAME_3=Foreman,AUTH_PASSWORD_3=ForemanPass123,AUTH_USERNAME_4=Worker,AUTH_PASSWORD_4=WorkerPass123,GEMINI_API_KEY=$GEMINI_API_KEY"

echo "✅ Deployment complete!"
echo "🌐 Service URL:"
gcloud run services describe $SERVICE_NAME --region=$REGION --format="value(status.url)"