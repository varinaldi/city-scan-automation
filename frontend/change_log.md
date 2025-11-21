## STREAMING MODE IMPLEMENTATION (--stream flag)

Internal notes only. For reference when updating codebase and documnentation.


## Changes to frontend.sh (scripts/frontend.sh):

**Line 18:** Added STREAM_MODE flag
```bash
STREAM_MODE=0
```

**Lines 28-30:** Added --stream parser
```bash
--stream)
  STREAM_MODE=1
  ;;
```

**Lines 46-74:** File copying logic for streaming mode
```bash
# If directory does not exist, clone the repository OR copy from local frontend/
if [ ! -d "$CITY_DIR" ]; then
  mkdir -p "$CITY_DIR"

  # In streaming mode, prefer local frontend/ if it exists, otherwise clone
  if [[ $STREAM_MODE -eq 1 ]]; then
    if [ -d "frontend" ]; then
      echo "Streaming mode: Copying files from local frontend/ directory..."
      for item in R scripts source index.qmd pdf.qmd; do
        if [ -e "frontend/$item" ]; then
          cp -r "frontend/$item" "$CITY_DIR/"
        fi
      done
    else
      echo "Streaming mode: Local frontend/ not found, cloning from repository..."
      git clone -b "$BRANCH" --filter=blob:none "$REPO" "$CITY_DIR/temp-repo"
      echo "Copying files from the cloned repository to the city directory..."
      for item in R scripts source index.qmd pdf.qmd; do
        cp -r "$CITY_DIR/temp-repo/frontend/$item" "$CITY_DIR"
      done
    fi
  else
    # Non-streaming: always clone from GitHub
    git clone -b "$BRANCH" --filter=blob:none "$REPO" "$CITY_DIR/temp-repo"
    for item in R scripts source index.qmd pdf.qmd; do
      cp -r "$CITY_DIR/temp-repo/frontend/$item" "$CITY_DIR"
    done
  fi
else
  # If directory exists and streaming mode: don't overwrite R files
  if [[ $STREAM_MODE -eq 1 ]]; then
    echo "Streaming mode: Using existing R code files, not overwriting from repo."
  else
    # Non-streaming: ask user if they want to overwrite
    read -p "Do you want to clone and possibly overwrite? (y/n): " choice
    if [[ "$choice" = "y" ]]; then
      # Clone and copy...
    fi
  fi
fi
```

**Logic explanation:**
- **Streaming + local frontend/ exists:** Use local files (for dev with custom changes)
- **Streaming + no local frontend/:** Clone from GitHub (after merge, or different machine)
- **Not streaming:** Always clone from GitHub
- **Directory exists + streaming:** Don't overwrite (preserve local changes)
- **Directory exists + not streaming:** Ask user if they want to overwrite

**Lines 77-84:** Skip download when streaming
```bash
if [[ $STREAM_MODE -eq 0 ]]; then
  shopt -u dotglob nullglob
  rm -rf $CITY_DIR/temp-repo

  # Download the city data from Google Cloud Storage
  if ! gcloud storage ls "gs://crp-city-scan/$GCS_CITY_DIR" > /dev/null 2>&1; then
    echo "Error: gs://crp-city-scan/$GCS_CITY_DIR does not exist or you do not have permission. (Try `gcloud auth login`?) Exiting."
    exit 1
  fi
  gcloud storage ls gs://crp-city-scan/$GCS_CITY_DIR | grep '^gs://' | grep -v '/00-reproduction-code/' | xargs -I {} gcloud storage cp -R {} "$CITY_DIR"
fi
```

**Lines 114-124:** Pass env vars for native streaming - maps-static.R (inside RUN_NATIVE block)
```bash
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
```

**Lines 128-142:** Added scan-calculations.Rmd rendering (inside RUN_NATIVE block)
```bash
# Generate scan-calculations
echo "Generating scan-calculations..."
if [[ $STREAM_MODE -eq 1 ]]; then
  USE_GCS=true SCAN_ID="$GCS_CITY_DIR" Rscript -e "rmarkdown::render('scan-calculations.Rmd', output_file='03-render-output/scan-calculations.html')" || {
    echo "Error: Failed to render scan-calculations in streaming mode."
    exit 1
  }
else
  Rscript -e "rmarkdown::render('scan-calculations.Rmd', output_file='03-render-output/scan-calculations.html')" || {
    echo "Error: Failed to render scan-calculations."
    exit 1
  }
fi
echo "Scan-calculations generated successfully."
```



---



## Changes to run.sh (frontend/run.sh):


### Problem
When running `run.sh` directly from `frontend/` directory, the script failed because:
1. `MNT_DIR` environment variable was undefined (only set in Dockerfile)
2. Working directory was not created before use
3. Paths used `$MNT_DIR/` prefix after already cd'ing into it (double pathing)
4. Missing files in copy commands: `scan-calculations.Rmd`, `_pre-render.R`, `_post-render.R`


### Changes to run.sh (frontend/run.sh):

**Lines 214-226:** Added MNT_DIR auto-detection logic
```bash
# Set MNT_DIR default if not already set (Dockerfile sets it to /home/mnt)
if [ -z "${MNT_DIR:-}" ]; then
    if [ -n "${CLOUD_RUN_EXECUTION:-}" ]; then
        # Running in Cloud Run
        MNT_DIR="mnt"
    elif [ -f "run.sh" ] && [ -n "${GCS_CITY_DIR:-}" ]; then
        # Running from frontend/ directory locally
        MNT_DIR="../mnt/${GCS_CITY_DIR}"
    else
        # Fallback to current directory
        MNT_DIR="."
    fi
fi
```

**Line 255:** Create working directory before use
```bash
mkdir -p "$MNT_DIR"
```

**Line 258:** Added missing files to main copy command
```bash
# Before:
cp -r R scripts source run.sh index.qmd pdf.qmd "$MNT_DIR"

# After:
cp -r R scripts source run.sh index.qmd pdf.qmd scan-calculations.Rmd _pre-render.R _post-render.R "$MNT_DIR"
```

**Lines 267-271:** Added missing files to reproduction code copy
```bash
# Before:
rm -rf 00-reproduction-code/R 00-reproduction-code/scripts \
    00-reproduction-code/source 00-reproduction-code/index.qmd \
    00-reproduction-code/pdf.qmd
cp -r R scripts source index.qmd pdf.qmd 00-reproduction-code

# After:
rm -rf 00-reproduction-code/R 00-reproduction-code/scripts \
    00-reproduction-code/source 00-reproduction-code/index.qmd \
    00-reproduction-code/pdf.qmd 00-reproduction-code/scan-calculations.Rmd \
    00-reproduction-code/_pre-render.R 00-reproduction-code/_post-render.R
cp -r R scripts source index.qmd pdf.qmd scan-calculations.Rmd _pre-render.R _post-render.R 00-reproduction-code
```

**Lines 262, 266-325:** Fixed all paths after `cd "$MNT_DIR"` to use relative paths
```bash
# Changed from $MNT_DIR/03-render-output/... to 03-render-output/...
# Examples:
mkdir -p 01-user-input 02-process-output 03-render-output  # Line 262
mkdir -p 00-reproduction-code  # Line 266
gcloud storage cp -R 03-render-output/maps/** gs://...  # Line 283
vivliostyle build pdf.html -o 03-render-output/print.pdf  # Line 307
```

### Result
Users can now run directly from frontend/ without manually setting MNT_DIR:
```bash
cd frontend/
GCS_CITY_DIR=2025-11-senegal-kolda ./run.sh --stream
```


---

**Line 31:** Added STREAM flag
```bash
STREAM=false
```

**Lines 97-100:** Added --stream parser
```bash
--stream)
    STREAM=true
    shift
    ;;
```

**Line 187:** Updated GCS check to include STREAM
```bash
if [ "$DOWNLOAD" = true ] || [ "$UPLOAD" = true ] || [ "$STREAM" = true ]; then
    check_gcs_object_variable
fi
```

**Lines 230-233:** Export env vars for R when streaming
```bash
if [ "$DOWNLOAD" = true ] || [ "$UPLOAD" = true ] || [ "$STREAM" = true ]; then
    export USE_GCS="true"
    export SCAN_ID="$GCS_CITY_DIR"
fi
```

**Lines 267-274:** Replaced FUTURELOG with scan-calculations.Rmd rendering
```bash
if [ "$CHARTS" = true ]; then
    log "Generating charts..."
    Rscript -e "rmarkdown::render('scan-calculations.Rmd', output_file ='03-render-output/scan-calculations.html')"
    if [ "$UPLOAD" = true ]; then
          gcloud storage cp $MNT_DIR/03-render-output/scan-calculations.html gs://crp-city-scan/$GCS_CITY_DIR/03-render-output/
    fi
fi
```

**Lines 200-211:** Skip mount checks when streaming (allows local execution without Docker)
```bash
# If not uploading and not streaming, definitely need mountpoint
if [ "$UPLOAD" = false ] && [ "$STREAM" = false ]; then
    check_mount /home/mnt
elif [ "$UPLOAD" = true ] && [[ $- == *i* ]]; then
    if ! mountpoint -q /home/mnt; then
        read -p "/home/mnt is not mounted. Do you want to proceed anyway? (y/n): " proceed
        if [ "$proceed" != "y" ]; then
            echo "Exiting as per user request."
            exit 1
        fi
    fi
fi
```
**Explanation:** Mount checks are only needed when actually downloading/uploading data to local directories. When streaming (`STREAM=true`), data is accessed directly from GCS, so Docker mounts are not required. This allows run.sh to work in local execution mode.

