# City Scan Automation

This repository provides automation tools for city scanning and analysis. These instructions are designed for first-time users and will set up a fully reproducible environment on any machine.

## Prerequisites

- Git (for cloning the repository)
- Basic command-line knowledge

## Installation & Setup

### Option 1: Via Conda (Recommended for Mac, Windows, Linux)

#### Step 1: Install Anaconda

If you don't have Anaconda installed, download and install it from the [official Anaconda website](https://www.anaconda.com/download). 

**General steps:** 
- Visit https://www.anaconda.com/download and select your operating system
- Follow the installation wizard and accept the default settings
- Restart your terminal after installation completes
- Verify installation by running: `conda --version`

#### Step 2: Clone the Repository

```bash
git clone https://github.com/rosemaryturtle/city-scan-automation.git
cd city-scan-automation
git checkout new_structure
```

#### Step 3: Create and Activate the Environment

```bash
conda create -n cityscan python=3.11.8 -y
conda activate cityscan
```

#### Step 4: Install Dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

#### Step 5: Register Jupyter Kernel (Optional, for notebook use)

```bash
python -m ipykernel install --user --name cityscan --display-name "Cityscan"
```

---

### Option 2: Via Bootstrap Script (Alternative Setup -- only for Mac, Linux)

If you prefer automated system setup or Python is not installed, use the bootstrap approach:

#### Step 1: Clone the Repository

```bash
git clone https://github.com/rosemaryturtle/city-scan-automation.git
cd city-scan-automation
git checkout new_structure
```

#### Step 2: Run Bootstrap Script

This script prepares your system and installs Python 3.11.8 via pyenv:

```bash
bash bootstrap.sh
```

**Note:** Review the `bootstrap.sh` script first to ensure it meets your system requirements. It will:
- Install system dependencies
- Install and configure pyenv
- Install Python 3.11.8
- Update your shell configuration

If pyenv is installed for the first time, restart your terminal and run the script again.

#### Step 3: Run Setup Script

This script creates the virtual environment, installs dependencies, and registers the Jupyter kernel:

```bash
bash orchestrator.sh
```

When setup is successful, you should see:
- Python 3.11.8 ready via pyenv
- A new virtual environment created
- A Jupyter kernel registered: "Cityscan (Python 3.11)"

---

### Configure Inputs

Adjust the files in the `inputs/` folder for your specific project:
- Create a new folder `AOI/` and store your AOI boundary file there
- Modify `city_inputs.yml` and `menu.yml` with your analysis parameters

## Running the Analysis

Execute the main task to run all sequences:

```bash
python -m tasks --all
```

### Alternative Commands for Specific Use Cases

```bash
# New city (reads from inputs/)
python -m tasks wsf

# Existing city (reads from mnt/)
python -m tasks wsf --scan-id 2026-02-malta-malta

# Multiple tasks
python -m tasks wsf population forest

# Collect step only
python -m tasks wsf --collect

# Analyze step only
python -m tasks wsf --analyze

# Visualize step only
python -m tasks wsf --visualize

# All tasks enabled in menu.yml
python -m tasks --all

# All tasks for existing city
python -m tasks --all --scan-id 2026-02-malta-malta

# Show available tasks
python -m tasks --list
```

Tasks will process in sequence using your configured environment. If you need to manually activate the environment later, use:

```bash
source venv/bin/activate
```

## Additional Notes

- The project requires Python 3.11 specifically
- Check `logs/` folder if you encounter issues
- Use the "Cityscan" Jupyter kernel for notebook development

## Troubleshooting

**Conda-related issues:**
- Ensure Anaconda/Miniconda is properly installed: `conda --version`
- Try updating conda: `conda update -n base -c defaults conda`

**Bootstrap-related issues:**
- If pyenv is not found, check that it was installed: `pyenv --version`
- On macOS, ensure Homebrew is installed; on Linux, check apt package manager
- If Python 3.11 is not available, re-run `bash bootstrap.sh`

**General troubleshooting:**
- Check terminal output for specific error messages
- Verify all prerequisites are met before running setup scripts
- For any remaining issues, consult the logs in `logs/` folder
