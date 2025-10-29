# Quick Start Guide - Refactored Workflow

## Test the New scan-calculations.Rmd

### Option 1: Using RStudio

```r
# 1. Open RStudio
# 2. Navigate to:
setwd("~/Documents/Work/city-scan-automation/mnt/2025-10-senegal-dakar/04-analysis")

# 3. Open scan-calculations.Rmd
# 4. Click "Knit" button

# 5. Output will be: scan-calculations.html
```

### Option 2: Command Line

```bash
cd ~/Documents/Work/city-scan-automation/mnt/2025-10-senegal-dakar/04-analysis
Rscript -e "rmarkdown::render('scan-calculations.Rmd')"
open scan-calculations.html
```

### Option 3: Run for All Cities

```bash
cd ~/Documents/Work/city-scan-automation

for city in 2025-10-senegal-dakar 2025-10-senegal-matam 2025-10-senegal-diourbel 2025-10-senegal-tambacounda 2025-10-indonesia-sofifi; do
  echo "==============================================="
  echo "Rendering analysis for $city..."
  echo "==============================================="
  cd mnt/$city/04-analysis
  Rscript -e "rmarkdown::render('scan-calculations.Rmd')"
  cd ../../..
  echo "✓ Done: mnt/$city/04-analysis/scan-calculations.html"
  echo ""
done
```

---

## Compare Old vs New

### Old Version (01-current-scans)
```bash
open ~/Documents/Work/01-current-scans/2025-10-senegal-dakar/scan-calculations.html
```

### New Version (mnt/04-analysis)
```bash
open ~/Documents/Work/city-scan-automation/mnt/2025-10-senegal-dakar/04-analysis/scan-calculations.html
```

---

## Adding Custom Analysis

### Example: Port Analysis for Dakar

```bash
# 1. Create custom analysis folder
mkdir ~/Documents/Work/city-scan-automation/mnt/2025-10-senegal-dakar/04-analysis/custom-analysis

# 2. Create custom Rmd file
nano ~/Documents/Work/city-scan-automation/mnt/2025-10-senegal-dakar/04-analysis/custom-analysis/port-analysis.Rmd
```

**Content of port-analysis.Rmd:**
````markdown
## Port Infrastructure Analysis

Analysis specific to Dakar's port.

```{r port-stats, echo=FALSE}
library(ggplot2)

# Your custom code here
port_data <- data.frame(
  year = 2010:2024,
  throughput = rnorm(15, 1000, 100)
)

ggplot(port_data, aes(x = year, y = throughput)) +
  geom_line() +
  labs(title = "Port Container Throughput")
```
````

**Re-render to see custom section:**
```bash
cd ~/Documents/Work/city-scan-automation/mnt/2025-10-senegal-dakar/04-analysis
Rscript -e "rmarkdown::render('scan-calculations.Rmd')"
```

---

## File Locations

### All Created Files

```
city-scan-automation/
├── REFACTORING-SUMMARY.md       ← Full details
├── QUICK-START.md               ← This file
│
└── mnt/
    ├── 2025-10-senegal-dakar/04-analysis/
    │   ├── scan-calculations.Rmd
    │   ├── user-inputs.R
    │   └── README.md
    │
    ├── 2025-10-senegal-matam/04-analysis/
    │   ├── scan-calculations.Rmd
    │   ├── user-inputs.R
    │   └── README.md
    │
    ├── 2025-10-senegal-diourbel/04-analysis/
    │   ├── scan-calculations.Rmd
    │   ├── user-inputs.R
    │   └── README.md
    │
    ├── 2025-10-senegal-tambacounda/04-analysis/
    │   ├── scan-calculations.Rmd
    │   ├── user-inputs.R
    │   └── README.md
    │
    └── 2025-10-indonesia-sofifi/04-analysis/
        ├── scan-calculations.Rmd
        ├── user-inputs.R
        └── README.md
```

---

## Troubleshooting

### "AOI directory not found"
Make sure backend has run:
```bash
cd city-scan-automation
bash scripts/frontend.sh 2025-10-senegal-dakar
```

### "Package not found"
Install missing R packages:
```r
install.packages("librarian")
librarian::shelf(tidyr, ggplot2, sf, dplyr, readr, ...)
```

### Want to use old version?
Old files are untouched in:
```
~/Documents/Work/01-current-scans/
```

---

## What's Different?

| Feature | Old (01-current-scans) | New (mnt/04-analysis) |
|---------|----------------------|----------------------|
| Location | Separate folder | Inside city folder |
| Data access | Manual copy | Automatic |
| Customization | Edit entire Rmd | Add custom/*.Rmd |
| Maintenance | 5+ copies | 1 master template |

---

## Need Help?

1. Read `REFACTORING-SUMMARY.md` for full details
2. Read `mnt/{city}/04-analysis/README.md` for per-city info
3. Compare output with old version to verify correctness
