// JS/treemap.js

export async function createTreeMap(data, config = {}) {
  const d3 = await import("https://esm.sh/d3@7");
  
  const {
    value = "value",
    label = "label",
    title = "Land Cover Types",
    subtitle = "Tunis, Tunisia",
    colors = null,
    width = null,
    height = null
  } = config;

  const plotWidth = width || 1000;
  const plotHeight = height || 600;

  const filtered = data
    .filter(d => d[value] > 0)
    .sort((a, b) => b[value] - a[value]);
    
  const hierarchyData = {
    name: "Land Cover",
    children: filtered.map(d => ({
      name: d[label],
      value: d[value]
    }))
  };
  
  const root = d3.hierarchy(hierarchyData)
    .sum(d => d.value)
    .sort((a, b) => b.value - a.value);
    
  d3.treemap()
    .size([plotWidth, plotHeight])
    .padding(2)
    .round(true)(root);
  
  const container = d3.create("div")
    .style("font-family", "system-ui, sans-serif")
    .style("max-width", "100%")
    .style("margin", "0")
    .style("padding", "0");

  if (title) {
    container.append("div")
      .style("font-size", "19")
      .style("font-weight", "normal")
      .style("margin", "0")
      .style("padding", "0")
      .style("line-height", "1")
      .text(title);
  }

  if (subtitle) {
    container.append("div")
      .style("font-size", "14px")
      .style("font-style", "italic")
      .style("margin", "0")
      .style("padding", "0")
      .style("line-height", "2")
      .text(subtitle);
  }

  // Create tooltip
  const tooltip = d3.select("body").append("div")
    .attr("class", "treemap-tooltip")
    .style("position", "absolute")
    .style("visibility", "hidden")
    .style("background", "white")
    .style("border", "1px solid black")
    .style("padding", "6px 8px")
    .style("font-family", "system-ui, sans-serif")
    .style("font-size", "13px")
    .style("color", "#333")
    .style("pointer-events", "none")
    .style("z-index", "1000");

  const svg = d3.create("svg")
    .attr("width", plotWidth)
    .attr("height", plotHeight)
    .attr("viewBox", `0 0 ${plotWidth} ${plotHeight}`)
    .style("max-width", "100%")
    .style("display", "block")
    .style("margin-top", "-160px")
    .style("padding", "0");
    
  const leaf = svg.selectAll("g")
    .data(root.leaves())
    .join("g")
    .attr("transform", d => `translate(${d.x0},${d.y0})`);
    
  leaf.append("rect")
    .attr("width", d => d.x1 - d.x0)
    .attr("height", d => d.y1 - d.y0)
    .attr("fill", d => colors && colors[d.data.name] ? colors[d.data.name] : "#ccc")
    .attr("fill-opacity", 0.8)
    .attr("stroke", "white")
    .attr("stroke-width", 1)
    .on("mouseover", function(event, d) {
      d3.select(this).attr("fill-opacity", 1);
      tooltip.style("visibility", "visible")
        .text(`${d.data.name}: ${d.data.value.toFixed(1)}%`);
    })
    .on("mousemove", function(event) {
      tooltip.style("top", (event.pageY - 35) + "px")
        .style("left", (event.pageX + 10) + "px");
    })
    .on("mouseout", function() {
      d3.select(this).attr("fill-opacity", 0.8);
      tooltip.style("visibility", "hidden");
    });
    
  leaf.filter(d => (d.x1 - d.x0) > 60 && (d.y1 - d.y0) > 35)
    .append("text")
    .attr("x", 4)
    .attr("y", 16)
    .style("font-family", "system-ui, sans-serif")
    .style("font-weight", "600")
    .style("font-size", "13px")
    .style("fill", "#333")
    .style("pointer-events", "none")
    .text(d => d.data.name);
    
  leaf.filter(d => (d.x1 - d.x0) > 50 && (d.y1 - d.y0) > 50)
    .append("text")
    .attr("x", 4)
    .attr("y", 32)
    .style("font-family", "system-ui, sans-serif")
    .style("font-size", "13px")
    .style("fill", "#141414")
    .style("pointer-events", "none")
    .text(d => `${d.data.value.toFixed(1)}%`);
  
  container.node().appendChild(svg.node());
  return container.node();
}