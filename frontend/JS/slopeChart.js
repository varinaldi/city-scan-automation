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
    xTickFormat = null,
    yTickFormat = null,
    
    // Annotations
    xAnnotations = null  // Array like [{position: 0.5, label: "Potential Sprawl\n(Housing Surplus)"}]
  } = config;

  const marks = [];
  
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
        Plot.text([referenceLine], {
          x: referenceLine.value,
          y: yDomain ? yDomain[0] : 0,
          text: [referenceLine.label],
          dy: -10,
          fill: referenceLine.color || "gray",
          fontSize: 11
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
  
  // Add x-axis annotations if provided
  if (xAnnotations) {
    xAnnotations.forEach(annotation => {
      marks.push(
        Plot.text([annotation], {
          x: annotation.position,
          y: yDomain ? yDomain[1] : data[data.length - 1][y],
          text: [annotation.label],
          dy: 40,
          fill: "gray",
          fontSize: 10,
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