/**
 * Creates a flexible line chart with extensive customization options
 * @param {Array} data - Array of data objects
 * @param {Object} config - Configuration object
 */

export async function createLineChart(data, config = {}) {

  const Plot = await import("https://esm.sh/@observablehq/plot@0.6");
  const d3 = await import("https://esm.sh/d3@7");

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

    // Line styles
    strokeDasharray = null, // Array of dash patterns for each group

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
    xType = null,
    xTicks = null,
    xTickFormat = null,
    yTickFormat = null,

    // Interactivity
    tooltip = null,  // null = auto-detect (on if group exists), true = force on, false = force off
    tooltipXLabel = null,
    tooltipXField = null,  // Field to use for x value in tooltip (defaults to x)
    tooltipYLabel = null,  // Custom label for y in tooltip (e.g., "Solar Energy")
    tooltipYFormat = null
  } = config;

  // Auto-enable tooltip - always on unless explicitly disabled
  const showTooltip = tooltip === false ? false : true;

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

  // Helper function to format x label for tooltip title
  const formatXLabel = () => {
    if (x === 'yearName') return 'Year';
    if (tooltipXLabel) return tooltipXLabel;
    if (xLabel) return xLabel;
    return x.charAt(0).toUpperCase() + x.slice(1);
  };

  // Helper function to format x value for tooltip
  const formatXValue = (d) => {
    const xValue = tooltipXField ? d[tooltipXField] : d[x];
    const val = typeof xValue === 'number' ? Math.round(xValue) : xValue;
    return String(val).replace(/,/g, '');
  };

  // Helper function to capitalize group values
  const formatGroupValue = (groupValue) => {
    const str = String(groupValue);
    return str.charAt(0).toUpperCase() + str.slice(1);
  };

  if (group) {
    // Get unique groups in order they appear in data
    const uniqueGroups = [...new Set(data.map(d => d[group]))];
    const colorArray = Array.isArray(colors) ? colors : [];
    const dashArray = Array.isArray(strokeDasharray) ? strokeDasharray : [];

    uniqueGroups.forEach((groupValue, i) => {
      const groupData = data.filter(d => d[group] === groupValue);
      const color = colorArray[i] || "black";
      const dashPattern = dashArray[i] || null;

      const groupLineConfig = {
        x,
        y,
        stroke: color,
        strokeWidth: lineWidth,
        opacity,
        ...(dashPattern && { strokeDasharray: dashPattern })
      };

      marks.push(Plot.line(groupData, groupLineConfig));

      if (showPoints) {
        marks.push(Plot.dot(groupData, {
          x,
          y,
          fill: color,
          r: pointRadius,
          opacity
        }));
      }
    });

    // Add tooltip for grouped chart
    if (showTooltip) {
      const xLabelKey = formatXLabel();

      marks.push(
        Plot.dot(data, Plot.pointer({
          x,
          y,
          fill: "transparent",
          stroke: "transparent",
          r: 0,
          title: d => {
            const xValue = formatXValue(d);
            const groupValue = formatGroupValue(d[group]);
            const value = d[y];
            const formattedValue = (value != null && tooltipYFormat) ? tooltipYFormat(value) : value;
            return `${xLabelKey}: ${xValue}\n${"─".repeat(15)}\n${groupValue}: ${formattedValue}`;
          },
          tip: true
        }))
      );
    }
  } else {
    // Single line case
    const lineConfig = {
      x,
      y,
      stroke: colors || "black",
      strokeWidth: lineWidth,
      opacity
    };

    marks.push(Plot.line(data, lineConfig));

    if (showPoints) {
      marks.push(Plot.dot(data, {
        x,
        y,
        fill: colors || "black",
        r: pointRadius,
        opacity
      }));
    }

    // Add tooltip for single line
    if (showTooltip) {
      const xLabelKey = formatXLabel();

      marks.push(
        Plot.dot(data, Plot.pointer({
          x,
          y,
          fill: "transparent",
          stroke: "transparent",
          r: 0,
          title: d => {
            const xValue = formatXValue(d);
            const value = d[y];
            const formattedValue = (value != null && tooltipYFormat) ? tooltipYFormat(value) : value;
            const yLabel = tooltipYLabel || "Value";
            return `${xLabelKey}: ${xValue}\n${"─".repeat(15)}\n${yLabel}: ${formattedValue}`;
          },
          tip: true
        }))
      );
    }
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
      ...(xTicks && { ticks: xTicks }),
      ...(xTickFormat && { tickFormat: xTickFormat })
    },
    y: {
      label: yLabel,
      grid: yGrid,
      ...(yDomain && { domain: yDomain }),
      ...(yTickFormat && { tickFormat: yTickFormat })

    }
  };

  // Add title with date range and subtitle
  if (title) {
    let titleWithRange = title;

    // Auto-detect date range from data
    const xValues = data.map(d => d[x]).filter(v => v != null);
    if (xValues.length > 0) {
      const minX = Math.min(...xValues);
      const maxX = Math.max(...xValues);

      // Check if x is year-based
      if (x === 'yearName' || x === 'year' || (minX >= 1900 && maxX <= 2100)) {
        titleWithRange = `${title}, ${minX}-${maxX}`;
      }
      // Check if x is month-based
      else if (x === 'month' && minX >= 1 && maxX <= 12) {
        titleWithRange = `${title}, January - December`;
      }
      // Check if x is week-based and we have monthName field
      else if (x === 'week' && data[0]?.monthName) {
        const months = [...new Set(data.map(d => d.monthName))];
        if (months.length > 0) {
          const firstMonth = months[0];
          const lastMonth = months[months.length - 1];
          titleWithRange = `${title}, ${firstMonth} - ${lastMonth}`;
        }
      }
    }

    plotOptions.title = titleWithRange;
  }
  if (subtitle) {
    plotOptions.subtitle = subtitle;
  }

  // Add color configuration for groups
  if (group) {
    const uniqueGroups = [...new Set(data.map(d => d[group]))];
    const colorArray = Array.isArray(colors) ? colors : [];

    plotOptions.color = {
      legend: true,
      domain: uniqueGroups,
      range: colorArray.length > 0 ? colorArray : undefined,
      ...(colorArray.length === 0 && { scheme: colorScheme })
    };
  }

  return Plot.plot(plotOptions);
}
