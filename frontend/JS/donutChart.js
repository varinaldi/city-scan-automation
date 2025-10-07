// JS/donutChart.js

export async function createDonutChart(data, config = {}) {
  const d3 = await import("https://esm.sh/d3@7");
  const Plot = await import("https://esm.sh/@observablehq/plot@0.6");

  const {
    value = "value",
    label = "label",

    title = null,
    subtitle = null,

    innerRadius = 0.5,

    colors = null,
    colorScheme = "tableau10",

    showLegend = true,
    legendTitle = null,

    width = null,
    height = null,
    valueFormat = null
  } = config;

  const plotWidth = width || 600;
  const plotHeight = height || 400;
  const radius = Math.min(plotWidth * 0.4, plotHeight) / 2;

  // Create pie generator
  const pieGenerator = d3.pie()
    .value(d => d[value])
    .sort(null);

  // Create arc generator
  const arcGenerator = d3.arc()
    .innerRadius(radius * innerRadius)
    .outerRadius(radius);

  // Create color scale
  const colorScale = d3.scaleOrdinal()
    .domain(data.map(d => d[label]))
    .range(colors ? Object.values(colors) : d3.schemeTableau10);

  // Create container
  const container = d3.create("div")
    .style("display", "flex")
    .style("flex-direction", "column")
    .style("padding", "20px");

  // Add title and subtitle using Observable Plot styling
  if (title) {
    container.append("div")
      .style("font-family", "system-ui, sans-serif")
      .style("font-size", "18")
      .style("margin-bottom", subtitle ? "4px" : "12px")
      .text(title);
  }

  if (subtitle) {
    container.append("div")
      .style("font-family", "system-ui, sans-serif")
      .style("font-size", "14px")
      .style("font-style", "italic")
      .style("color", "#666")
      .style("margin-bottom", "12px")
      .text(subtitle);
  }

  // Add legend if requested (before chart)
  if (showLegend) {
    if (legendTitle) {
      container.append("div")
        .style("font-family", "system-ui, sans-serif")
        .style("font-size", "12px")
        .style("font-weight", "bold")
        .style("margin-bottom", "8px")
        .style("color", "#333")
        .text(legendTitle);
    }

    const legend = container.append("div")
      .style("display", "flex")
      .style("flex-wrap", "wrap")
      .style("gap", "8px")
      .style("margin-bottom", "15px");

    data.forEach(d => {
      const item = legend.append("div")
        .style("display", "flex")
        .style("align-items", "center")
        .style("gap", "6px");

      item.append("div")
        .style("width", "12px")
        .style("height", "12px")
        .style("background-color", colors && colors[d[label]] ? colors[d[label]] : colorScale(d[label]))
        .style("flex-shrink", "0");

      item.append("span")
        .style("font-size", "12px")
        .style("font-family", "system-ui, sans-serif")
        .text(d[label]);
    });
  }

  // Create container for chart
  const chartContainer = container.append("div")
    .style("display", "flex")
    .style("justify-content", "center");

  // Create SVG for donut
  const svg = chartContainer.append("svg")
    .attr("width", plotWidth * 0.6)
    .attr("height", plotHeight)
    .attr("viewBox", [-plotWidth * 0.3, -plotHeight / 2, plotWidth * 0.6, plotHeight]);

  // Create tooltip
  const tooltip = d3.select("body").append("div")
    .style("position", "absolute")
    .style("background-color", "white")
    .style("border", "1px solid #ddd")
    .style("border-radius", "4px")
    .style("padding", "8px")
    .style("font-size", "12px")
    .style("pointer-events", "none")
    .style("opacity", 0)
    .style("box-shadow", "0 2px 4px rgba(0,0,0,0.1)");

  // Create arcs
  const arcs = svg.append("g")
    .selectAll("path")
    .data(pieGenerator(data))
    .join("path")
    .attr("fill", d => colors && colors[d.data[label]] ? colors[d.data[label]] : colorScale(d.data[label]))
    .attr("stroke", "white")
    .attr("stroke-width", "2px")
    .attr("d", arcGenerator)
    .on("mouseover", function(event, d) {
      d3.select(this)
        .transition()
        .duration(200)
        .attr("opacity", 0.8);

      tooltip
        .transition()
        .duration(200)
        .style("opacity", 1);

      const formattedValue = valueFormat ? valueFormat(d.data[value]) : `${d.data[value].toFixed(2)}%`;
      tooltip
        .html(`<strong>${d.data[label]}</strong><br/>${formattedValue}`)
        .style("left", (event.pageX + 10) + "px")
        .style("top", (event.pageY - 10) + "px");
    })
    .on("mousemove", function(event) {
      tooltip
        .style("left", (event.pageX + 10) + "px")
        .style("top", (event.pageY - 10) + "px");
    })
    .on("mouseout", function() {
      d3.select(this)
        .transition()
        .duration(200)
        .attr("opacity", 1);

      tooltip
        .transition()
        .duration(200)
        .style("opacity", 0);
    });

  // Add percentage labels on the donut
  svg.append("g")
    .selectAll("text")
    .data(pieGenerator(data))
    .join("text")
    .attr("transform", d => `translate(${arcGenerator.centroid(d)})`)
    .attr("dy", "0.35em")
    .attr("text-anchor", "middle")
    .style("font-size", "14px")
    .style("font-weight", "600")
    .style("fill", "black")
    .text(d => {
      if (d.data[value] > 3) {
        return valueFormat ? valueFormat(d.data[value]) : `${d.data[value].toFixed(2)}%`;
      }
      return "";
    });

  return container.node();
}