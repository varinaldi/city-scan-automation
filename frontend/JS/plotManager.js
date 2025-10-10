// JS/plotManager.js

import { createLineChart } from './lineChart.js';
import { createScatterPlot } from './scatterPlot.js';
import { createTreeMap } from './treeMap.js';
import { createDonutChart } from './donutChart.js';
import { createBarChart } from './barChart.js';
import { createSlopeChart } from './slopeChart.js';
import { embedImage } from './embedImage.js';

const plotTypes = {
  lineChart: createLineChart,
  scatterPlot: createScatterPlot,
  treeMap: createTreeMap,
  donutChart: createDonutChart,
  barChart: createBarChart,
  slopeChart: createSlopeChart,
  image: embedImage
};

export async function addPlot(plotConfig) {
  const plotFunction = plotTypes[plotConfig.type];

  if (!plotFunction) {
    throw new Error(`Unknown plot type: ${plotConfig.type}`);
  }

  // Skip data loading for embedImage type
  let data = null;
  if (plotConfig.type !== 'embedImage') {
    // Load data from the source(s) specified in config
    if (Array.isArray(plotConfig.data_source)) {
      // Multiple data sources - load all
      const dataSources = await Promise.all(
        plotConfig.data_source.map(source => loadData(source))
      );

      // Apply data transformation if provided
      if (plotConfig.data_transform) {
        const transformFn = eval(`(${plotConfig.data_transform})`);
        data = transformFn(dataSources);
      } else {
        // If no transform, just use the first data source
        data = dataSources[0];
      }
    } else {
      // Single data source
      data = await loadData(plotConfig.data_source);
    }
  }

  // Parse config (convert string functions to actual functions)
  const config = parseConfig(plotConfig.config);

  return plotFunction(data, config);
}

async function loadData(dataSource) {
  // Read city directory from city-dir.txt (first line only)
  const cityDirResponse = await fetch('../city-dir.txt');
  const cityDirText = await cityDirResponse.text();
  const cityDir = cityDirText.split('\n')[0].trim();

  // Construct full path: {cityDir}/02-process-output/chart-data/{dataSource}
  const fullPath = `${cityDir}/02-process-output/chart-data/${dataSource}`;

  // Use FileAttachment to load the data
  const response = await fetch(fullPath);
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
  if (typeof parsed.tooltipYFormat === 'string') {
    parsed.tooltipYFormat = eval(`(${parsed.tooltipYFormat})`);
  }
  if (typeof parsed.valueFormat === 'string') {
    parsed.valueFormat = eval(`(${parsed.valueFormat})`);
  }

  return parsed;
}