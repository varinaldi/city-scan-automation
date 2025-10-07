// JS/scatterPlot.js

export async function createScatterPlot(data, config = {}) {
  const Plot = await import("https://esm.sh/@observablehq/plot@0.6");
  
  const {
    x = "x",
    y = "y",
    r = null,
    fill = null,
    
    title = null,
    subtitle = null,
    xLabel = null,
    yLabel = null,
    
    pointRadius = 5,
    radiusRange = null,
    radiusDomain = null,
    opacity = 0.7,
    stroke = "black",
    strokeWidth = 0.5,
    
    colors = null,
    
    height = null,
    marginTop = 40,
    marginRight = 20,
    marginBottom = 60,
    marginLeft = 60,
    
    xDomain = null,
    yDomain = null,
    xGrid = true,
    yGrid = true,
    xTickFormat = null,
    yTickFormat = null,
    
    tooltip = true,
    tooltipColumns = null,  // Array of column names to show, e.g., ["locationName", "year", "magnitude", "deaths"]
    tooltipContent = null
  } = config;

  // Calculate radius domain from data if not provided
  let rDomain = radiusDomain;
  let rRange = radiusRange;
  
  if (r && !rDomain) {
    const values = data.map(d => d[r]).filter(v => v != null);
    rDomain = [Math.min(...values), Math.max(...values)];
  }
  
  if (r && !rRange) {
    const width = 500;
    rRange = [Math.max(2, Math.min(5, width / 200)), Math.max(12, Math.min(25, width / 40))];
  }

  const dotConfig = {
    x,
    y,
    opacity,
    stroke,
    strokeWidth
  };
  
  // Add radius
  if (r) {
    dotConfig.r = r;
  } else {
    dotConfig.r = pointRadius;
  }
  
  // Add fill
  if (fill) {
    dotConfig.fill = fill;
  } else if (colors && !fill) {
    dotConfig.fill = colors;
  }
  
  // Add tooltip
  if (tooltip) {
    dotConfig.tip = true;

    // Custom tooltip based on specified columns
    if (tooltipColumns && !tooltipContent) {
      dotConfig.title = d => {
        return tooltipColumns
          .map(col => d[col])
          .join('\n');
      };
    } else if (tooltipContent) {
      dotConfig.title = tooltipContent;
    }
  }
  
  const marks = [Plot.dot(data, dotConfig)];
  
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
  
  if (r) {
    plotOptions.r = {
      ...(rDomain && { domain: rDomain }),
      ...(rRange && { range: rRange }),
      legend: true
    };
  }
  
  if (title) plotOptions.title = title;
  if (subtitle) plotOptions.subtitle = subtitle;
  
  if (fill && colors) {
    plotOptions.color = {
      legend: true,
      domain: Object.keys(colors),
      range: Object.values(colors)
    };
  }
  
  return Plot.plot(plotOptions);
}