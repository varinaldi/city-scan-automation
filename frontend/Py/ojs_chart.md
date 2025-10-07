# OJS Chart Integration 

### Prerequisites

- Some tabular data are missing, so we need to create them. To do so, update source/files.yml to include local data.
  

- The data cleaning for OJS plots are in python, so we need to set the python environment and update source/pyconfig.yml to point to the correct python executable.

- Rendering index.qmd should run the python cleaning (Maybe better to move the whole data cleaning to backend?).

### JS charts

Individual interactive Observable JS chart helper functions are in JS folder.

To generate chart, update source/plots.yml (will need to write the paramater configs)


in the .qmd, load the plot.yml and plotManager.js, then use addPlot to add the chart to the right section.

