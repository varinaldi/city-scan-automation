// JS/barChart.js

export async function createBarChart(data, config = {}) {
  const Plot = await import("https://esm.sh/@observablehq/plot@0.6");
  
  const {
    x = "x",
    y = "y",
    fill = null,
    
    title = null,
    subtitle = null,
    xLabel = null,
    yLabel = null,
    
    stacked = false,
    grouped = true,
    horizontal = false,
    
    opacity = 1,
    
    colors = null,
    colorScheme = "tableau10",
    
    height = 400,
    marginTop = 40,
    marginRight = 20,
    marginBottom = 60,
    marginLeft = 60,
    
    xDomain = null,
    yDomain = null,
    xGrid = false,
    yGrid = true,
    xTickFormat = null,
    yTickFormat = null,
    xRotate = 0,
    
    tooltip = true
  } = config;

  const marks = [];
  
  if (stacked) {
    marks.push(Plot.barY(data, Plot.stackY({
      x, y, fill, opacity, tip: tooltip
    })));
  } else if (grouped && fill) {
    // Simpler approach: modify data to add position offset
    const groups = [...new Set(data.map(d => d[fill]))];
    const groupCount = groups.length;
    
    // Create modified data with x positions adjusted
    const modifiedData = data.map(d => {
      const groupIndex = groups.indexOf(d[fill]);
      const offset = (groupIndex - (groupCount - 1) / 2) * 0.3; // 0.3 is spacing
      
      return {
        ...d,
        xPos: d[x] + offset,
        groupColor: colors && colors[d[fill]] ? colors[d[fill]] : d[fill]
      };
    });
    
    marks.push(
      Plot.barY(modifiedData, {
        x: "xPos",
        y,
        fill: "groupColor",
        inset: 0.5,
        opacity,
        tip: tooltip
      })
    );
  } else {
    marks.push(Plot.barY(data, {
      x, y, fill, opacity, tip: tooltip
    }));
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
      ...(xTickFormat && { tickFormat: xTickFormat }),
      ...(xRotate !== 0 && { tickRotate: xRotate })
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
  
  if (fill && colors) {
    plotOptions.color = {
      legend: true,
      domain: Object.keys(colors),
      range: Object.values(colors)
    };
  }
  
  return Plot.plot(plotOptions);
}