/**
 * Creates a flexible line chart with extensive customization options
 * @param {Array} data - Array of data objects
 * @param {Object} config - Configuration object
 */

export async function createLineChart(data, config = {}) {

  const Plot = await import("https://esm.sh/@observablehq/plot@0.6");

  const {
    // Core mappings
    x = "x",
    y = "y",
    group = null, // Column name for grouping multiple lines
    
    // Labels and titles
    title = null,
    subtitle = null,
    xLabel = null,
    yLabel = null,
    
    // Visual options
    showPoints = true,
    pointRadius = 4,
    lineWidth = 2,
    opacity = 1,
    
    // Colors
    colors = null, // Single color string or array for groups
    colorScheme = "tableau10", // D3 color scheme if groups exist
    
    // Reference lines
    referenceLines = [], // Array of {value, label, color, strokeDasharray}
    
    // Dimensions
    width = null,
    height = 400,
    marginTop = 40,
    marginRight = 20,
    marginBottom = 40,
    marginLeft = 50,
    
    // Axes
    xDomain = null,
    yDomain = null,
    xGrid = false,
    yGrid = true,

    // Axes formatting
    xType = null,  // Add this: "time", "linear", "band", etc.
    xTickFormat = null,
    yTickFormat = null,  // Add this
    
    // Interactivity
    tooltip = true
  } = config;

  const marks = [];
  
  // Add reference lines first (so they're behind data)
  referenceLines.forEach(line => {
    marks.push(
      Plot.ruleY([line.value], {
        stroke: line.color || "gray",
        strokeDasharray: line.strokeDasharray || "4,4",
        strokeWidth: line.strokeWidth || 1,
        opacity: line.opacity || 0.5
      })
    );
    
    // Add label if provided
    if (line.label) {
      marks.push(
        Plot.text([line], {
          x: xDomain ? xDomain[1] : d3.max(data, d => d[x]),
          y: line.value,
          text: [line.label],
          textAnchor: "end",
          dy: -5,
          fill: line.color || "gray",
          fontSize: 11
        })
      );
    }
  });
  
  // Base line configuration
  const lineConfig = {
    x,
    y,
    strokeWidth: lineWidth,
    opacity
  };
  
  // Point configuration
  const pointConfig = {
    x,
    y,
    r: pointRadius,
    opacity
  };
  
  // Handle grouping
  if (group) {
    lineConfig.stroke = group;
    pointConfig.fill = group;
    if (tooltip) {
      pointConfig.tip = true;
      pointConfig.title = d => `${d[group]}\n${xLabel || x}: ${d[x]}\n${yLabel || y}: ${d[y]}`;
    }
  } else {
    lineConfig.stroke = colors || "black";
    pointConfig.fill = colors || "black";
    if (tooltip) {
      pointConfig.tip = true;
    }
  }
  
  // Add line
  marks.push(Plot.line(data, lineConfig));
  
  // Add points if requested
  if (showPoints) {
    marks.push(Plot.dot(data, pointConfig));
  }
  
  // Build plot options
  const plotOptions = {
    marks,
    ...(width && { width }), 
    height,
    marginTop,
    marginRight,
    marginBottom,
    marginLeft,
    x: {
      label: xLabel,
      grid: xGrid,
      ...(xDomain && { domain: xDomain }),
      ...(xType && { type: xType }),
      ...(xTickFormat && { tickFormat: xTickFormat })
    },
    y: {
      label: yLabel,
      grid: yGrid,
      ...(yDomain && { domain: yDomain }),
      ...(yTickFormat && { tickFormat: yTickFormat })

    }
  };
  
  // Add title and subtitle
  if (title) {
    plotOptions.title = title;
  }
  if (subtitle) {
    plotOptions.subtitle = subtitle;
  }
  
  // Add color configuration for groups
  if (group) {
    plotOptions.color = {
      legend: true,
      ...(colors ? { range: colors } : { scheme: colorScheme })
    };
  }
  
  return Plot.plot(plotOptions);
}