# OJS Chart Integration

### Prerequisites

- We need to create missing tabular data. Update [source/files.yml](source/files.yml) to include local data for cleaning.
  
- The data cleaning for OJS plots are in python, update the *python environment* in [source/pyconfig.yml](source/pyconfig.yml) to point to the correct python executable.
  
- Rendering  [`index.qmd`](index.qmd) will run the data cleaning from **02-process-output spatial & tabular** and create a new **chart-data** directory (Maybe better to move the whole data cleaning to backend?).

### JS charts

Individual interactive Observable JS chart helper functions are in JS folder.

The charts in [`index.qmd`](index.qmd) will read the plot names in [source/plots.yml](source/plots.yml). To add the plot, use addPlot from [JS/plotManager.js](JS/plotManager.js).

```
    // load the plot configuration from source/plots.yml
    yaml = import("https://esm.sh/js-yaml@4")
    plotConfig = FileAttachment("source/plots.yml").text()
    plots = yaml.load(await plotConfig)
```

 To add the plot, use addPlot from [JS/plotManager.js](JS/plotManager.js).

```
    // import addPlot from plotManager to add the chart
    import {addPlot} from "./JS/plotManager.js"
    chart_pas = addPlot(plots.population_demographics)
```

To generate individual chart, update [source/plots.yml](source/plots.yml) with the configuration parameters below.

---

## Chart Configuration Parameters

### lineChart
**Core mappings:**
- `x` (default: "x") - Column name for x-axis
- `y` (default: "y") - Column name for y-axis
- `group` (default: null) - Column name for grouping multiple lines

**Labels and titles:**
- `title`, `subtitle`, `xLabel`, `yLabel`

**Visual options:**
- `showPoints` (default: true), `pointRadius` (default: 4)
- `lineWidth` (default: 2), `opacity` (default: 1)
- `curve` (default: null) - Line smoothing/interpolation method
  - Options: `"basis"`, `"cardinal"`, `"catmull-rom"`, `"linear"`, `"step"`, `"step-after"`, `"step-before"`
  - `null` = no smoothing (straight lines between points)

**Colors:**
- `colors` - Single color string or array for groups
- `colorScheme` (default: "tableau10")
- `strokeDasharray` - Array of dash patterns for each group

**Reference lines:**
- `referenceLines` - Array of `{value, label, color, strokeDasharray}`

**Dimensions:**
- `width`, `height` (default: 400)
- `marginTop/Right/Bottom/Left` (defaults: 40/20/40/50)

**Axes:**
- `xDomain`, `yDomain`, `xGrid` (default: false), `yGrid` (default: true)
- `xType`, `xTicks`, `xTickFormat`, `yTickFormat`

**Interactivity:**
- `tooltip` (default: auto-on), `tooltipXLabel`, `tooltipXField`
- `tooltipYLabel`, `tooltipYFormat`

---

### barChart
**Core mappings:**
- `x`, `y`, `fill` (for grouping/coloring)

**Labels and titles:**
- `title`, `subtitle`, `xLabel`, `yLabel`

**Layout:**
- `stacked` (default: false), `grouped` (default: true), `horizontal` (default: false)

**Visual:**
- `opacity` (default: 1)
- `colors` - Object mapping fill values to colors
- `colorScheme` (default: "tableau10")

**Dimensions:**
- `height` (default: 400)
- `marginTop/Right/Bottom/Left` (defaults: 40/20/60/60)

**Axes:**
- `xDomain`, `yDomain`, `xGrid` (default: false), `yGrid` (default: true)
- `xTickFormat`, `yTickFormat`, `xRotate` (default: 0)

**Interactivity:**
- `tooltip` (default: true)
- `tooltipColumns` - Array of column names to show in tooltip

---

### scatterPlot
**Core mappings:**
- `x`, `y`, `r` (radius), `fill`

**Labels and titles:**
- `title`, `subtitle`, `xLabel`, `yLabel`

**Visual:**
- `pointRadius` (default: 5)
- `radiusRange`, `radiusDomain`
- `opacity` (default: 0.7)
- `stroke` (default: "black"), `strokeWidth` (default: 0.5)
- `colors`
- `symbol` - String or array of symbols for groups (e.g., "circle", "square", "diamond", "triangle", "star")
  - Single string: applies same shape to all points
  - Array: applies different shapes to each group (requires `fill` to be specified)

**Dimensions:**
- `height`, `marginTop/Right/Bottom/Left` (defaults: 40/20/60/60)

**Axes:**
- `xDomain`, `yDomain`, `xGrid` (default: true), `yGrid` (default: true)
- `xTickFormat`, `yTickFormat`

**Interactivity:**
- `tooltip` (default: true)
- `tooltipColumns` - Array of column names
- `tooltipContent` - Custom tooltip function

---

### treeMap
**Core mappings:**
- `value` (default: "value")
- `label` (default: "label")

**Labels:**
- `title`, `subtitle`

**Visual:**
- `colors` - Object mapping labels to colors

**Dimensions:**
- `width`, `height`
- `fontSize` (default: 13)
- `valueFormat` - Function to format values

---

### donutChart
**Core mappings:**
- `value` (default: "value")
- `label` (default: "label")

**Labels:**
- `title`, `subtitle`

**Visual:**
- `innerRadius` (default: 0.5)
- `colors` - Object mapping labels to colors
- `colorScheme` (default: "tableau10")

**Legend:**
- `showLegend` (default: true)
- `legendTitle`

**Dimensions:**
- `width`, `height`
- `valueFormat` - Function to format values

---

### slopeChart
**Core mappings:**
- `x`, `y`

**Labels and titles:**
- `title`, `subtitle`, `xLabel`, `yLabel`

**Visual:**
- `lineWidth` (default: 1.5)
- `pointRadius` (default: 4)
- `colors` (default: "black")
- `opacity` (default: 0.8)

**Reference line:**
- `referenceLine` - Object `{value, label, color}`

**Dimensions:**
- `height` (default: 600)
- `marginTop/Right/Bottom/Left` (defaults: 40/120/80/120)

**Axes:**
- `xDomain`, `yDomain`
- `xGrid` (default: true), `yGrid` (default: false)
- `xTicks`, `xTickFormat`, `yTickFormat`

**Annotations:**
- `xAnnotations` - Array like `[{position, label}]`

---

### embedImage
**Core mappings:**
- `url` (required) - URL or path to the image

**Dimensions:**
- `widthPercent` (default: 100) - Width as percentage of canvas (clamped to 100%)
- `heightPercent` (default: null) - Height as percentage of canvas (clamped to 100%)

**Attribution:**
- `attribution` (default: null) - Attribution text displayed at bottom-right

**Notes:**
- Images are sized as percentages and automatically constrained to canvas boundaries
- `maxWidth` and `maxHeight` are set to 100% to prevent overflow
- Attribution appears at bottom-right corner with semi-transparent white background


