```
 Flow:
  frontend.sh $SCAN_ID --native
    ├─ Clone repo → mnt/$SCAN_ID/
    ├─ Download data from GCS → mnt/$SCAN_ID/
    └─ cd mnt/$SCAN_ID/
       └─ Rscript R/maps-static.R  ← Runs directly on your
  
  Mac/Linux
  Pros: Fast, easy debugging
  Cons: Need R + all packages installed locally

  ---
  2. DOCKER (frontend.sh --docker)

  Where code runs: Docker container on your local machine

  Flow:
  frontend.sh $SCAN_ID --docker
    ├─ Clone repo → mnt/$SCAN_ID/
    ├─ Download data from GCS → mnt/$SCAN_ID/
    └─ docker run -v mnt/$SCAN_ID:/home/mnt ...
         └─ run.sh (inside container)
              └─ Rscript R/maps-static.R  ← Runs in isolated container
  
  Pros: Consistent environment, no local R setup needed
  Cons: Slower than native

  ---
  3. DIRECT RUN (direct run.sh, no frontend.sh)

  Where code runs: Google Cloud (serverless container) / LOCAL

  Flow:
  Cloud Run triggers pre-built container
    └─ run.sh --download --upload
         ├─ Download from GCS (inside cloud container)
         ├─ Process
         └─ Upload back to GCS


  cd frontend/
    ./run.sh --download --upload
        ├─ Downloads data
        ├─ Processes
        └─ Uploads results


  Pros: No local machine needed, scalable
  Cons: Costs money, harder to debug

  to direct run.sh for specific scan-id: 

  Method 1: Set env var inline
  cd frontend/
  GCS_CITY_DIR=2025-11-mauritania-nouakchott ./run.sh --download --upload

  Method 2: Interactive prompt (if --download or --upload used)
  cd frontend/
  ./run.sh --download

  Method 3: Export first
  cd frontend/
  export GCS_CITY_DIR=2025-11-mauritania-nouakchott
  ./run.sh --download --upload

```



## STREAMING MODE IMPLEMENTATION (--stream flag)

### Changes to run.sh (frontend/run.sh):

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

### Changes to frontend.sh (scripts/frontend.sh):

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

### Usage:

**1. Native streaming (via frontend.sh):**
```bash
./scripts/frontend.sh 2025-11-mauritania-nouakchott --native --stream
```
Generates: Maps + scan-calculations only

**2. Direct run.sh - All outputs:**
```bash
cd frontend
env GCS_CITY_DIR=2025-11-mauritania-nouakchott ./run.sh --stream
```
Generates: Maps, charts, PDF, HTML (all outputs)

**3. Direct run.sh - Specific outputs:**
```bash
# Only scan-calculations:
env GCS_CITY_DIR=2025-11-mauritania-nouakchott ./run.sh --stream --no-static-maps --no-pdf --no-html

# Only maps:
env GCS_CITY_DIR=2025-11-mauritania-nouakchott ./run.sh --stream --no-charts --no-pdf --no-html

# Only PDF + HTML (no maps/charts):
env GCS_CITY_DIR=2025-11-mauritania-nouakchott ./run.sh --stream --no-static-maps --no-charts
```

**4. Docker streaming:**
```bash
docker run -v "$CITY_DIR:/home/mnt" -e GCS_CITY_DIR="$SCAN_ID" notkin/nalgene run.sh --stream
```

---

## CODE SOURCE: Local vs GitHub

**IMPORTANT: Where does the code come from?**

### `--native` (without --stream):
- ❌ **Clones from GitHub** (rosemaryturtle/city-scan-automation main branch)
- ❌ Downloads **ALL data** from GCS to local disk
- ✅ Use when: Testing with latest merged code from main branch
- ⚠️ **Will NOT include your uncommitted local changes!**

### `--native --stream`:
- ✅ **Copies from LOCAL** `frontend/` directory (your working code)
- ✅ Falls back to GitHub clone if `frontend/` directory not found
- ✅ Downloads **only** 01-user-input/ (config files, ~MBs)
- ✅ Streams large data from GCS (avoids downloading GBs)
- ✅ Use when: Local development with uncommitted changes

**Rule of thumb:**
- **Before pushing to GitHub:** Use `--native --stream` (uses your local code)
- **After merged to main:** Can use `--native` alone (uses GitHub code)
- **Testing others' PRs:** Change REPO/BRANCH in frontend.sh, then use `--native`

---

## STREAMING MODE SCENARIOS

### Scenario 1: Local Development (Before Merging to GitHub)
**Situation:** You have custom changes in local `frontend/` directory that aren't pushed to GitHub yet.

**Command:** `./scripts/frontend.sh 2025-11-mauritania-nouakchott --native --stream`

**What happens:**
1. Checks if mnt directory exists
2. Finds local `frontend/` directory exists
3. Copies R files from local `frontend/` → mnt directory
4. Skips data download from GCS
5. Runs with `USE_GCS=true SCAN_ID=2025-11-mauritania-nouakchott`
6. GCS overrides fetch files directly from GCS buckets

**Result:** ✅ Uses your custom local changes, streams data from GCS

---

### Scenario 2: After Merging to GitHub (Same Machine)
**Situation:** You merged your changes to GitHub, still have local `frontend/` directory.

**Command:** `./scripts/frontend.sh 2025-11-mauritania-nouakchott --native --stream`

**What happens:**
1. Checks if mnt directory exists
2. Finds local `frontend/` directory exists
3. Copies from local `frontend/` (which has your merged changes)
4. Everything else same as Scenario 1

**Result:** ✅ Uses your local files, streams from GCS

---

### Scenario 3: Fresh Clone of Repo (Different Machine)
**Situation:** Someone else (or you on new machine) clones the repo after your changes are merged.

**Command:**
```bash
git clone https://github.com/rosemaryturtle/city-scan-automation.git
cd city-scan-automation
./scripts/frontend.sh 2025-11-mauritania-nouakchott --native --stream
```

**What happens:**
1. The clone includes the `frontend/` directory with merged changes
2. Script finds `frontend/` directory exists
3. Copies from `frontend/` → mnt directory
4. Streams data from GCS

**Result:** ✅ Uses code from GitHub (with your merged changes), streams from GCS

---

### Scenario 4: No Local Frontend Directory (Edge Case)
**Situation:** Running from a location without `frontend/` directory.

**Command:** `./scripts/frontend.sh 2025-11-mauritania-nouakchott --native --stream`

**What happens:**
1. Script doesn't find local `frontend/` directory
2. Falls back to cloning from GitHub
3. Copies from cloned repo → mnt directory
4. Streams data from GCS

**Result:** ✅ Uses code from GitHub, streams from GCS

---

### Scenario 5: Non-Streaming Mode (Standard Workflow)
**Situation:** Normal workflow with data download.

**Command:** `./scripts/frontend.sh 2025-11-mauritania-nouakchott --native`

**What happens:**
1. Always clones from GitHub (ignores local `frontend/`)
2. Downloads all data from GCS to local mnt directory
3. Runs R scripts using local data files
4. No GCS streaming

**Result:** ✅ Standard workflow, all data local

---

### Key Takeaway
- **Streaming mode is smart:** Uses local changes if available, GitHub code if not
- **After merging:** Works seamlessly whether using local or cloned code
- **Non-streaming:** Always uses GitHub code for consistency

