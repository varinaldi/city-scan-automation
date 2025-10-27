# Alternative Cloud Architectures

This document explores alternative architectures to address redundancies in the current Cloud Run implementation.

## Current Architecture Issues

### Identified Redundancies:
1. ❌ **21 parallel tasks** download the same global datasets repeatedly
2. ❌ **No caching** - every run downloads everything fresh from GCS
3. ❌ **Ephemeral storage** - intermediate files lost between tasks
4. ❌ **High network costs** - constant GCS download/upload
5. ❌ **Large container** (~1GB+) must be in Artifact Registry

## Proposed Alternative: Event-Driven VM with Caching

### Architecture Flow

```
┌─────────────────────────────────────────────────────────────┐
│ 1. USER: Upload AOI to GCS                                 │
│    gs://crp-city-scan/01-user-input/AOI/city.shp           │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. TRIGGER: GCS event notification                         │
│    - Cloud Function/Eventarc detects new file              │
│    - Starts VM or wakes existing VM                        │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. VM PROCESSING (Persistent Disk)                         │
│    ├─ Global datasets cached on 500GB persistent disk      │
│    ├─ Code updated via `git pull` (not container rebuild)  │
│    ├─ Process data with multiprocessing                    │
│    └─ Stream results to GCS as generated                   │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. OUTPUT: Stream to GCS                                   │
│    - Each output uploaded immediately after generation      │
│    - VM auto-shuts down after completion                   │
└─────────────────────────────────────────────────────────────┘
```

### VM Configuration

```yaml
# Compute Engine VM Spec
machine_type: n1-highmem-16  # 16 vCPUs, 104GB RAM
boot_disk: 50GB SSD
data_disk: 500GB persistent disk (for cached datasets)
preemptible: false  # Need reliability for long jobs
region: us-central1
```

### Event Trigger Setup

```bash
# Cloud Function to start VM when AOI uploaded
gcloud functions deploy trigger-city-scan \
  --runtime python310 \
  --trigger-resource crp-city-scan \
  --trigger-event google.storage.object.finalize \
  --entry-point start_processing_vm
```

### Streaming Output Implementation

```python
# backend/stream_output.py

from google.cloud import storage
import rasterio
import os

class StreamingProcessor:
    """Process and stream outputs to GCS immediately"""

    def __init__(self, bucket_name, city_name):
        self.client = storage.Client()
        self.bucket = self.client.bucket(bucket_name)
        self.city_name = city_name
        self.temp_dir = '/tmp/city-scan'
        os.makedirs(self.temp_dir, exist_ok=True)

    def process_and_upload(self, process_func, output_name, *args, **kwargs):
        """
        Generic function to process data and stream to GCS

        Args:
            process_func: Function that returns (data, metadata)
            output_name: Name of output file
            *args, **kwargs: Arguments for process_func
        """
        # 1. Process data
        print(f"Processing {output_name}...")
        data, meta = process_func(*args, **kwargs)

        # 2. Write to temp file
        temp_path = f'{self.temp_dir}/{output_name}'
        with rasterio.open(temp_path, 'w', **meta) as dst:
            dst.write(data)

        # 3. Upload to GCS immediately
        print(f"Uploading {output_name} to GCS...")
        blob = self.bucket.blob(f'outputs/{self.city_name}/{output_name}')
        blob.upload_from_filename(temp_path)

        # 4. Clean up temp file
        os.remove(temp_path)
        print(f"✓ {output_name} completed and uploaded")

        # 5. Return data for downstream processing
        return data, meta

# Usage example:
# processor = StreamingProcessor('crp-city-scan', 'tunis')
# elev_data, elev_meta = processor.process_and_upload(
#     process_elevation,
#     'tunis_elevation.tif',
#     aoi_file, global_data_dir
# )
```

### Global Data Caching Strategy

```python
# backend/cache_manager.py

import os
from google.cloud import storage
from pathlib import Path

class GlobalDataCache:
    """Manage cached global datasets on persistent disk"""

    def __init__(self, cache_dir='/mnt/global-data'):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.client = storage.Client()

    def get_dataset(self, bucket_name, blob_path):
        """
        Get dataset from cache or download if missing

        Returns: Local path to cached file
        """
        # Create local cache path
        cache_path = self.cache_dir / blob_path.replace('/', '_')

        # Return if already cached
        if cache_path.exists():
            print(f"✓ Using cached: {blob_path}")
            return str(cache_path)

        # Download and cache
        print(f"↓ Downloading to cache: {blob_path}")
        bucket = self.client.bucket(bucket_name)
        blob = bucket.blob(blob_path)
        blob.download_to_filename(str(cache_path))

        return str(cache_path)

    def cache_size_gb(self):
        """Get total size of cached data in GB"""
        total = sum(f.stat().st_size for f in self.cache_dir.rglob('*') if f.is_file())
        return total / (1024**3)

# Usage:
# cache = GlobalDataCache()
# dem_path = cache.get_dataset('city-scan-global-data', 'DEM/fabdem.tif')
# # First run: downloads
# # Subsequent runs: instant (cached)
```

## Architecture Comparison

| Aspect | Current (Cloud Run) | Event-Driven VM | Hybrid (Recommended) |
|--------|---------------------|-----------------|----------------------|
| **Initial Setup** | Complex (Docker) | Medium (VM + scripts) | Medium |
| **Code Updates** | Rebuild container | `git pull` | `git pull` + optional container |
| **Data Caching** | None | Persistent disk | Persistent disk + GCS |
| **Parallelization** | Automatic (21 tasks) | Manual (multiprocessing) | Both (VM pools) |
| **Streaming Outputs** | Hard | Easy | Easy |
| **Cost (single run)** | $5-10 | $2-4 | $2-4 |
| **Cost (idle)** | $0 | $0 (auto-shutdown) | $0 |
| **Maintenance** | Low | Medium | Medium |
| **Scalability** | Excellent | Good (VM pools) | Excellent |
| **Network Costs** | High | Low | Low |

## Recommended: Hybrid Architecture

### Best of Both Worlds

1. **Compute Engine VM** for processing
   - Persistent disk for cached global datasets
   - Auto-shutdown when idle
   - Code updates via git

2. **Cloud Storage** for data
   - User inputs
   - Outputs (streamed as generated)

3. **Cloud Functions** for orchestration
   - Trigger VM on new AOI upload
   - Shutdown VM after completion

4. **Optional: Cloud Run** for frontend rendering
   - Keep frontend as serverless
   - Only backend moves to VM

### Migration Path

#### Phase 1: Test VM Approach (on `local` branch)
- [ ] Create Compute Engine VM
- [ ] Set up persistent disk with cached global data
- [ ] Modify scripts to use local cache
- [ ] Implement streaming upload functions
- [ ] Test with one city

#### Phase 2: Add Event Triggers
- [ ] Create Cloud Function to start VM
- [ ] Test GCS event → VM trigger
- [ ] Add auto-shutdown logic

#### Phase 3: Optimize
- [ ] Implement multiprocessing for parallel tasks
- [ ] Add cache warming script
- [ ] Monitor costs vs Cloud Run

#### Phase 4: Production (if successful)
- [ ] Migrate production to VM approach
- [ ] Keep Cloud Run as backup/legacy
- [ ] Document new workflow

## Implementation Code Structure

```
backend/
├── main.py                    # Entry point
├── stream_output.py          # NEW: Streaming upload utilities
├── cache_manager.py          # NEW: Global data caching
├── vm_startup.sh             # NEW: VM initialization script
├── requirements.txt          # Existing dependencies
├── elevation.py              # Modified to use cache + stream
├── fathom.py                 # Modified to use cache + stream
└── ...

scripts/
├── backend.sh                # Existing: Cloud Run trigger
├── vm_backend.sh             # NEW: VM-based trigger
└── cache_warmup.sh           # NEW: Pre-download global data

cloud-functions/
└── trigger-city-scan/        # NEW: Event trigger function
    ├── main.py
    └── requirements.txt
```

## Cost Analysis

### Current Cloud Run (per city processing)
```
21 tasks × 8 vCPU × 32GB RAM × 2 hours = ~$8-12
+ Network egress: ~$2-3
+ Storage: ~$1
Total: ~$11-16 per city
```

### Proposed VM Approach (per city processing)
```
1 VM × 16 vCPU × 104GB RAM × 2 hours = ~$3-4
+ Persistent disk (500GB): ~$0.17/day (only when running)
+ Network egress (reduced due to caching): ~$0.50
Total: ~$4-5 per city (60% savings)
```

### Persistent Disk Annual Cost
```
500GB persistent disk: ~$20/month = $240/year
Amortized over 100 cities: $2.40 per city

Net savings: Still ~50% cheaper than Cloud Run
```

## Conclusion

**The VM approach with caching and streaming is more efficient for this use case** because:

1. ✅ Global datasets downloaded once, cached forever
2. ✅ No container rebuild for code changes
3. ✅ Lower network costs (cached data)
4. ✅ Streaming outputs reduces storage needs
5. ✅ ~50-60% cost reduction
6. ✅ Faster processing (no repeated downloads)

**Recommendation**: Implement and test on the `local` branch before production migration.
