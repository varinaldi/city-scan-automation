#!/bin/bash

# Parse arguments --------------------------------------------------------------
if [ $# -lt 1 ] || [[ "$1" == -* ]]; then
  read -p "Enter the name of the city directory as it appears on Google Cloud (e.g., 2025-04-colombia-cartagena): " GCS_CITY_DIR
  if [ -z "$GCS_CITY_DIR" ]; then
    echo "City directory is required. Exiting."
    exit 1
  fi
else
  GCS_CITY_DIR="$1"
  shift
fi

# Check for --docker, --native, --stream, --local flags
RUN_DOCKER=0
RUN_NATIVE=0
STREAM_MODE=0
USE_LOCAL=0
DOCKER_FLAGS=()
for arg in "$@"; do
  case "$arg" in
    --no-gcs)
      DOWNLOAD_GCS=0
      ;;
    --branch=*)
      BRANCH="${arg#*=}"
      ;;
    --docker)
      RUN_DOCKER=1
      ;;
    --native)
      RUN_NATIVE=1
      ;;
    --stream)
      STREAM_MODE=1
      ;;
    --local)
      USE_LOCAL=1
      ;;
    *)
      DOCKER_FLAGS+=("$arg")
      ;;
  esac
done

# Local directory for the city (will be created if it doesn't exist)
CITY_DIR="$(pwd)/mnt/${GCS_CITY_DIR}"

# Repository for City Scan code
REPO="https://github.com/rosemaryturtle/city-scan-automation.git"
BRANCH="main"

# Shallow clone the repository and download city data --------------------------

# # If directory does not exist, clone the repository OR copy from local frontend/
shopt -s dotglob nullglob
if [ ! -d "$CITY_DIR" ]; then
  mkdir -p "$CITY_DIR"

  # Determine frontend source
  if [[ $USE_LOCAL -eq 1 ]]; then
    if [ -d "frontend" ]; then
      FRONTEND_SOURCE="local"
    else
      echo "Error: --local specified but frontend/ directory not found."
      exit 1
    fi
  elif [ -d "frontend" ]; then
    # No flag, local exists - prompt
    read -p "local frontend/ folder exists, use local frontend/? (y/n): " use_local
    if [[ "$use_local" == "y" ]]; then
      FRONTEND_SOURCE="local"
    else
      FRONTEND_SOURCE="upstream"
    fi
  else
    # No local frontend, use upstream
    FRONTEND_SOURCE="upstream"
  fi

  # Copy frontend files
  if [[ "$FRONTEND_SOURCE" == "local" ]]; then
    echo "Copying files from local frontend/ directory..."
    for item in R scripts source index.qmd pdf.qmd scan-calculations.Rmd; do
      if [ -e "frontend/$item" ]; then
        cp -r "frontend/$item" "$CITY_DIR/"
      fi
    done
  else
    echo "Cloning frontend from upstream repository..."
    git clone -b "$BRANCH" --filter=blob:none "$REPO" "$CITY_DIR/temp-repo"
    for item in R scripts source index.qmd pdf.qmd scan-calculations.Rmd; do
      if [ -e "$CITY_DIR/temp-repo/frontend/$item" ]; then
        cp -r "$CITY_DIR/temp-repo/frontend/$item" "$CITY_DIR/"
      fi
    done
  fi
else
  # City directory already exists
  echo "City directory already exists: $CITY_DIR"

  # Determine frontend source first (same logic as new dir)
  if [[ $USE_LOCAL -eq 1 ]]; then
    if [ -d "frontend" ]; then
      FRONTEND_SOURCE="local"
    else
      echo "Error: --local specified but frontend/ directory not found."
      exit 1
    fi
  elif [ -d "frontend" ]; then
    read -p "local frontend/ folder exists, use local frontend/? (y/n): " use_local
    if [[ "$use_local" == "y" ]]; then
      FRONTEND_SOURCE="local"
    else
      FRONTEND_SOURCE="upstream"
    fi
  else
    FRONTEND_SOURCE="upstream"
  fi

  # Ask if want to update
  read -p "Update R code from $FRONTEND_SOURCE? (y/n): " update_choice
  if [[ "$update_choice" == "y" ]]; then
    if [[ "$FRONTEND_SOURCE" == "local" ]]; then
      echo "Copying R code from local frontend/..."
      for item in R scripts source index.qmd pdf.qmd scan-calculations.Rmd; do
        if [ -e "frontend/$item" ]; then
          cp -r "frontend/$item" "$CITY_DIR/"
        fi
      done
    else
      echo "Cloning frontend from upstream..."
      rm -rf "$CITY_DIR/temp-repo"
      git clone -b "$BRANCH" --filter=blob:none "$REPO" "$CITY_DIR/temp-repo"
      for item in R scripts source index.qmd pdf.qmd scan-calculations.Rmd; do
        if [ -e "$CITY_DIR/temp-repo/frontend/$item" ]; then
          cp -r "$CITY_DIR/temp-repo/frontend/$item" "$CITY_DIR/"
        fi
      done
      rm -rf "$CITY_DIR/temp-repo"
    fi
  else
    echo "Using existing R code in $CITY_DIR."
  fi
fi

if [[ $STREAM_MODE -eq 0 ]]; then

  shopt -u dotglob nullglob
  rm -rf $CITY_DIR/temp-repo

# Download the city data from Google Cloud Storage
if [[ $DOWNLOAD_GCS -eq 0 ]]; then
  echo "--no-gcs flag detected. Skipping download of city data from Google Cloud Storage."
else
  echo "Downloading city data from gs://crp-city-scan/$GCS_CITY_DIR to $CITY_DIR ..."
  if ! gcloud storage ls "gs://crp-city-scan/$GCS_CITY_DIR" > /dev/null 2>&1; then
    echo "Error: gs://crp-city-scan/$GCS_CITY_DIR does not exist or you do not have permission. (Try `gcloud auth login`?) Exiting."
    exit 1
  fi
  gcloud storage ls gs://crp-city-scan/$GCS_CITY_DIR | grep '^gs://' | grep -v '/00-reproduction-code/' | xargs -I {} gcloud storage cp -R {} "$CITY_DIR"

else
  # Streaming mode: Download only config files (01-user-input)
  shopt -u dotglob nullglob
  rm -rf $CITY_DIR/temp-repo

  echo "Streaming mode: Downloading config files (01-user-input/)..."
  if ! gcloud storage ls "gs://crp-city-scan/$GCS_CITY_DIR" > /dev/null 2>&1; then
    echo "Error: gs://crp-city-scan/$GCS_CITY_DIR does not exist or you do not have permission. (Try `gcloud auth login`?) Exiting."
    exit 1
  fi
  gcloud storage cp -R "gs://crp-city-scan/$GCS_CITY_DIR/01-user-input" "$CITY_DIR/" 2>/dev/null || echo "Warning: Could not download 01-user-input directory"

  # Also download images from 02-process-output (static files needed for rendering)
  mkdir -p "$CITY_DIR/02-process-output"
  gcloud storage cp -R "gs://crp-city-scan/$GCS_CITY_DIR/02-process-output/images" "$CITY_DIR/02-process-output/" 2>/dev/null || echo "Warning: Could not download images directory"

fi

# Write city-dir.txt to tell the R scripts where to work from ------------------
echo "." > "$CITY_DIR/city-dir.txt"

# Create maps ------------------------------------------------------------------

if [[ $RUN_DOCKER -eq 1 && $RUN_NATIVE -eq 1 ]]; then
  echo "Warning: Both --docker and --native flags are set. Please choose one."
  select choice in "Docker" "Native"; do
    case $choice in
      Docker)
        RUN_NATIVE=0
        break
        ;;
      Native)
        RUN_DOCKER=0
        break
        ;;
      *)
        echo "Please select 1 (Docker) or 2 (Native)."
        ;;
    esac
  done
fi

if [[ $RUN_NATIVE -eq 1 ]]; then
  ORIGINAL_DIR=$(pwd)
  cd "$CITY_DIR"
  trap 'cd "$ORIGINAL_DIR"' EXIT

  if [[ $STREAM_MODE -eq 1 ]]; then
    USE_GCS=true SCAN_ID="$GCS_CITY_DIR" Rscript R/maps-static.R || {
      echo "Error: Failed to run R script for static maps in streaming mode."
      exit 1
    }
  else
    Rscript R/maps-static.R || {
      echo "Error: Failed to run R script for static maps."
      exit 1
    }
  fi

  echo "Static maps generated successfully."

  # Generate scan-calculations
  echo "Generating scan-calculations..."
  if [[ $STREAM_MODE -eq 1 ]]; then
    USE_GCS=true SCAN_ID="$GCS_CITY_DIR" Rscript -e "rmarkdown::render('scan-calculations.Rmd', output_file='03-render-output/scan-calculations.html')" || {
      echo "Error: Failed to render scan-calculations."
      exit 1
    }
  else
    Rscript -e "rmarkdown::render('scan-calculations.Rmd', output_file='03-render-output/scan-calculations.html')" || {
      echo "Error: Failed to render scan-calculations."
      exit 1
    }
  fi
  echo "Scan-calculations generated successfully."
  # trap - EXIT
fi

if [[ $RUN_DOCKER -eq 1 ]]; then
# Open Docker if it's not running
  if ! pgrep -x "docker" > /dev/null; then
    open -a docker
    sleep 4
  fi

  # Run the Docker container with the city directory mounted
  echo "Running Docker container..."
  docker run -it --rm \
    -v "$CITY_DIR:/home/mnt" \
    -e GCS_CITY_DIR="$GCS_CITY_DIR" \
    notkin/nalgene run.sh --no-code-copy ${DOCKER_FLAGS:---no-pdf --no-html}
fi
