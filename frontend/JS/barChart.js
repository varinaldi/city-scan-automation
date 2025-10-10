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

    tooltip = true,
    tooltipColumns = null  // Array of column names to show in tooltip
  } = config;

  const marks = [];
  
  if (stacked) {
    marks.push(Plot.barY(data, Plot.stackY({
      x, y, fill, opacity, tip: tooltip
    })));
  } else if (grouped && fill) {
    // Get unique groups and x values
    const groups = [...new Set(data.map(d => d[fill]))];
    const xValues = [...new Set(data.map(d => d[x]))];
    const groupCount = groups.length;

    // Calculate bar width and spacing
    const barWidth = 6; // Thin bar width in pixels
    const gapPx = 6; // Gap between bars in pixels

    // Create a bar mark for each group with dx offset (no individual tooltips)
    groups.forEach((group, groupIndex) => {
      const groupData = data.filter(d => d[fill] === group);
      // Center the bars: first bar gets negative offset, last gets positive
      const offset = (groupIndex - (groupCount - 1) / 2) * (barWidth + gapPx);

      marks.push(
        Plot.barY(groupData, {
          x,
          y,
          dx: offset,
          fill: colors && colors[group] ? colors[group] : group,
          opacity,
          inset: (20 - barWidth) / 2  // Control bar width by insetting
        })
      );
    });

    // Add unified tooltip for grouped bars using title
    if (tooltip) {
      // Create tooltip data with all groups for each x value
      const tooltipData = xValues.map(xVal => {
        const result = { [x]: xVal };
        let maxY = 0;

        // For each group, filter data by x and group to get the percentage
        groups.forEach(group => {
          const row = data.find(d => d[x] === xVal && d[fill] === group);
          if (row) {
            result[group] = row[y];
            maxY = Math.max(maxY, row[y]);

            // Add any additional tooltip columns from the data
            if (tooltipColumns) {
              tooltipColumns.forEach(col => {
                if (row[col] !== undefined) {
                  result[`${group}_${col}`] = row[col];
                }
              });
            }
          }
        });

        // Set max y for positioning the rule
        result.yMax = maxY * 1.15;
        return result;
      });

      marks.push(
        Plot.ruleX(tooltipData, {
          x,
          y1: 0,
          y2: d => d.yMax,
          stroke: "transparent",
          strokeWidth: 40,
          title: d => {
            const xLabelFormatted = xLabel ? xLabel.charAt(0).toUpperCase() + xLabel.slice(1) : x.charAt(0).toUpperCase() + x.slice(1);
            let tooltip = `${xLabelFormatted}: ${d[x]}\n${"─".repeat(20)}\n`;

            groups.forEach(g => {
              const value = d[g];
              if (value != null) {
                const formatted = yTickFormat ? yTickFormat(value) : value.toFixed(2);
                const groupCapitalized = g.charAt(0).toUpperCase() + g.slice(1);
                tooltip += `${groupCapitalized}: ${formatted}%`;

                // Add additional columns if specified
                if (tooltipColumns) {
                  tooltipColumns.forEach(col => {
                    const colValue = d[`${g}_${col}`];
                    if (colValue != null) {
                      tooltip += ` (${colValue} ${g}s)`;
                    }
                  });
                }
                tooltip += '\n';
              }
            });

            return tooltip.trim();
          },
          tip: true
        })
      );
    }
  } else {
    marks.push(Plot.barY(data, {
      x, y, fill, opacity, tip: tooltip
    }));
  }
  
  // Build x-axis configuration
  const xAxisConfig = {
    label: xLabel,
    grid: xGrid,
    ...(xTickFormat && { tickFormat: xTickFormat }),
    ...(xRotate !== 0 && { tickRotate: xRotate })
  };

  // For grouped bars, set domain to unique x values
  if (grouped && fill && !stacked) {
    const xValues = [...new Set(data.map(d => d[x]))];
    xAxisConfig.domain = xValues;
  }

  // Calculate y domain if not provided
  let finalYDomain = yDomain;
  if (!yDomain) {
    const yValues = data.map(d => d[y]).filter(v => v != null && !isNaN(v));
    if (yValues.length > 0) {
      const maxY = Math.max(...yValues);
      const minY = Math.min(...yValues);
      finalYDomain = [minY, maxY * 1.075];
    }
  }

  const plotOptions = {
    marks,
    height,
    marginTop,
    marginRight,
    marginBottom,
    marginLeft,
    x: xAxisConfig,
    y: {
      label: yLabel,
      grid: yGrid,
      ...(finalYDomain && { domain: finalYDomain }),
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