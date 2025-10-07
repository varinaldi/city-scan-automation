// JS/slopeChart.js

export async function createSlopeChart(data, config = {}) {
  const Plot = await import("https://esm.sh/@observablehq/plot@0.6");
  
  const {
    // Core mappings
    x = "x",
    y = "y",
    
    // Labels and titles
    title = null,
    subtitle = null,
    xLabel = null,
    yLabel = null,
    
    // Visual options
    lineWidth = 1.5,
    pointRadius = 4,
    colors = "black",
    opacity = 0.8,
    
    // Reference line (e.g., for "balanced" at x=1)
    referenceLine = null,  // {value: 1, label: "Balanced", color: "gray"}
    
    // Dimensions
    height = 600,
    marginTop = 40,
    marginRight = 120,
    marginBottom = 80,
    marginLeft = 120,
    
    // Axes
    xDomain = null,
    yDomain = null,
    xGrid = true,
    yGrid = false,
    xTicks = null,
    xTickFormat = null,
    yTickFormat = null,
    
    // Annotations
    xAnnotations = null  // Array like [{position: 0.5, label: "Potential Sprawl\n(Housing Surplus)"}]
  } = config;

  const marks = [];

  // Get max y value for positioning reference label
  const yValues = data.map(d => d[y]);
  const maxY = Math.max(...yValues);

  // Add reference line if specified
  if (referenceLine) {
    marks.push(
      Plot.ruleX([referenceLine.value], {
        stroke: referenceLine.color || "gray",
        strokeDasharray: "4,4",
        strokeWidth: 2
      })
    );

    if (referenceLine.label) {
      marks.push(
        Plot.text([{val: referenceLine.value, label: referenceLine.label}], {
          x: d => d.val,
          y: maxY + (yValues.length * 0.05),
          text: d => d.label,
          fill: referenceLine.color || "gray",
          fontSize: 11,
          textAnchor: "middle"
        })
      );
    }
  }

  // Add lines connecting points
  marks.push(
    Plot.line(data, {
      x,
      y,
      stroke: colors,
      strokeWidth: lineWidth,
      opacity
    })
  );

  // Add points
  marks.push(
    Plot.dot(data, {
      x,
      y,
      fill: colors,
      r: pointRadius,
      tip: true
    })
  );
  
  // Add x-axis annotations at bottom if provided
  if (xAnnotations) {
    const minY = Math.min(...yValues);

    xAnnotations.forEach(annotation => {
      marks.push(
        Plot.text([annotation], {
          x: annotation.position,
          y: minY,
          text: [annotation.label],
          dy: -5,
          fill: "gray",
          fontSize: 14,
          fontWeight: "bold",
          textAnchor: "middle",
          lineHeight: 1.4
        })
      );
    });
  }
  
  const plotOptions = {
    marks,
    height,
    marginTop,
    marginRight,
    marginBottom,
    marginLeft,
    x: {
      label: xLabel,
      grid: xGrid,
      ...(xDomain && { domain: xDomain }),
      ...(xTicks !== undefined && { ticks: xTicks }),
      ...(xTickFormat && { tickFormat: xTickFormat })
    },
    y: {
      label: yLabel,
      grid: yGrid,
      ...(yDomain && { domain: yDomain }),
      ...(yTickFormat && { tickFormat: yTickFormat })
    }
  };
  
  if (title) plotOptions.title = title;
  if (subtitle) plotOptions.subtitle = subtitle;
  
  return Plot.plot(plotOptions);
}