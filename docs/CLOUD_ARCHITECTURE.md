# Cloud Architecture Overview

This document explains how the City Scan backend runs in Google Cloud.

## The Complete Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│ 1. LOCAL: Build Docker Container                           │
│    - Includes all Python scripts (main.py, elevation.py...) │
│    - Includes dependencies (rasterio, geopandas...)        │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. UPLOAD: Push to Google Artifact Registry                │
│    - Docker image stored in registry                        │
│    - NOT in GCS - different service!                        │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. TRIGGER: Run in Google Cloud Run                        │
│    - Spins up containers from the image                     │
│    - Serverless - only runs when triggered                  │
│    - Can run multiple parallel tasks                        │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. EXECUTE: Container runs main.py                         │
│    ├─ Downloads inputs from GCS                             │
│    ├─ Downloads global datasets from GCS/public APIs        │
│    ├─ Processes data (creates TIFs, GPKGs)                  │
│    └─ Uploads outputs to GCS                                │
└─────────────────────────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. OUTPUT: Results in GCS                                  │
│    gs://crp-city-scan/02-process-output/city_name/*.tif    │
└─────────────────────────────────────────────────────────────┘
```

## Key Components

### Scripts Location
- **Development**: Your local machine / GitHub repo
- **Production**: Inside Docker image → Google Artifact Registry → Cloud Run containers
- **NOT in GCS buckets** (only data is in GCS)

### Data Location
- **Always in GCS buckets** (inputs and outputs)
- Input bucket: `gs://crp-city-scan/01-user-input/`
- Output bucket: `gs://crp-city-scan/02-process-output/`
- Global data bucket: `gs://city-scan-global-data/`

## What Goes Where?

| Component | Storage Location | Purpose |
|-----------|-----------------|---------|
| Python Scripts (`.py` files) | Docker Image → Artifact Registry | The code that runs the processing |
| Dependencies (`requirements.txt`) | Docker Image → Artifact Registry | Python packages needed |
| User Inputs (`.yml`, AOI shapefile) | GCS Bucket | City-specific configuration |
| Global Datasets (DEMs, climate data, etc.) | GCS Bucket / Public APIs | Reference data for all cities |
| Processed Outputs (`.tif`, `.gpkg`, `.csv`) | GCS Bucket | Results of the processing |

## Why This Architecture?

✅ **Docker container = code + environment** (uploaded to Artifact Registry)
✅ **Google Cloud Run = serverless compute** (runs the container)
✅ **GCS = data storage** (inputs go in, outputs come out)

### Benefits:
- **Scalable**: Can process multiple cities in parallel
- **Reproducible**: Same environment every time
- **Cost-effective**: Only pay when running (serverless)
- **No server management**: Google handles infrastructure

## Build & Deploy Workflow (One-Time Setup)

```bash
# 1. Build Docker image WITH all Python scripts inside
docker build --platform linux/amd64 \
  -t us-docker.pkg.dev/city-scan/city-scan-backend/csb:latest .

# 2. Push Docker image to Google Artifact Registry (not GCS!)
docker push us-docker.pkg.dev/city-scan/city-scan-backend/csb:latest

# 3. Deploy to Cloud Run Job
gcloud run jobs create csb \
  --image us-docker.pkg.dev/city-scan/city-scan-backend/csb:latest \
  --region us-central1 \
  --max-retries 1 \
  --tasks 21 \
  --task-timeout 24h \
  --cpu 8 \
  --memory 32Gi
```

## Execution Workflow (Each City Processing)

```bash
# 1. Upload inputs to GCS
gcloud storage cp gcs-user-input/city_inputs.yml \
  gs://crp-city-scan/01-user-input/
gcloud storage cp gcs-user-input/menu.yml \
  gs://crp-city-scan/01-user-input/
gcloud storage cp gcs-user-input/AOI/* \
  gs://crp-city-scan/01-user-input/AOI/

# 2. Trigger Cloud Run Job
gcloud run jobs execute csb --region us-central1

# What happens next (automatically):
# - Cloud Run spins up 21 parallel containers from your Docker image
# - Each container has all Python scripts inside
# - Scripts download data from GCS and public APIs
# - Scripts process data (elevation, flood, population, etc.)
# - Scripts upload results back to GCS
# - Containers shut down when done
```

## Local vs Cloud Execution

### Local Execution
```bash
# Run on your machine
conda activate city-scan
cd backend
python main.py
```
- Processes locally
- Outputs to local `output/` directory
- Good for testing/development

### Cloud Execution
```bash
# Run in Google Cloud
bash scripts/backend.sh
```
- Processes in Cloud Run containers
- Outputs to GCS buckets
- Good for production/large-scale processing

## Google Cloud Services Used

| Service | Purpose | What It Stores |
|---------|---------|----------------|
| **Artifact Registry** | Container image storage | Docker images with code |
| **Cloud Run Jobs** | Serverless compute | Nothing (ephemeral containers) |
| **Cloud Storage (GCS)** | Data storage | User inputs, global datasets, outputs |
| **Firestore** | Job coordination | Task completion tracking |
| **Earth Engine** | Satellite data processing | Nothing (API only) |

## Cost Structure

- **Artifact Registry**: Storage of Docker images (~1GB)
- **Cloud Run**: Per-second billing when containers are running
  - 21 tasks × 8 CPU × 32GB RAM × ~2 hours = main cost
- **Cloud Storage**: Data storage + download/upload
- **Earth Engine**: Free for research use

## Summary

**You upload the Docker container once, then trigger it to run whenever you need to process a city!**

The container:
- ✅ Contains all Python scripts
- ✅ Contains all dependencies
- ✅ Downloads data from GCS/APIs when running
- ✅ Processes data in ephemeral storage
- ✅ Uploads results to GCS
- ✅ Shuts down automatically when done
