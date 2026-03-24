# Changelog

## 2026-03-24

### New
- Demographics charts task (age-sex distribution, demographic indicators)
- Scan.py prompts before overwriting city source files (c/o/a)

### Fixed
- Oxford Economics case-insensitive city lookup
- Elevation column name mismatch (Elevation_Band → Bin)
- GEE elevation fallback now masks to AOI, not just bbox
- Elevation static map crops to AOI boundary
- Fathom flood analysis uses nested return period bands instead of max probability bins

### Changed
- Setup docs: clone single branch only
- Demographics added to scan-calculations sections
