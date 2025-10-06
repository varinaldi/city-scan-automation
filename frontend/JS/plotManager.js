// JS/plotManager.js

import { createLineChart } from './lineChart.js';
import { createScatterPlot } from './scatterPlot.js';
import { createTreemap } from './treemap.js';
import { createDonutChart } from './donutChart.js';
import { createBarChart } from './barChart.js';

const plotTypes = {
  lineChart: createLineChart,
  scatterPlot: createScatterPlot,
  treemap: createTreemap,
  donutChart: createDonutChart,
  barChart: createBarChart
};

export async function createPlotFromConfig(plotConfig) {
  const plotFunction = plotTypes[plotConfig.type];
  
  if (!plotFunction) {
    throw new Error(`Unknown plot type: ${plotConfig.type}`);
  }
  
  // Load data from the source specified in config
  const data = await loadData(plotConfig.data_source);
  
  // Parse config (convert string functions to actual functions)
  const config = parseConfig(plotConfig.config);
  
  return plotFunction(data, config);
}

async function loadData(dataSource) {
  // Use FileAttachment to load the data
  const response = await fetch(dataSource);
  const text = await response.text();
  
  // Parse CSV
  const d3 = await import("https://esm.sh/d3@7");
  return d3.csvParse(text, d3.autoType);
}

function parseConfig(config) {
  const parsed = { ...config };
  
  // Convert string functions to actual functions
  if (typeof parsed.xTickFormat === 'string') {
    parsed.xTickFormat = eval(`(${parsed.xTickFormat})`);
  }
  if (typeof parsed.yTickFormat === 'string') {
    parsed.yTickFormat = eval(`(${parsed.yTickFormat})`);
  }
  if (typeof parsed.tooltipContent === 'string') {
    parsed.tooltipContent = eval(`(${parsed.tooltipContent})`);
  }
  
  return parsed;
}