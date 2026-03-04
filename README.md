# City Scan Automation

This repository provides automation tools for city scanning and analysis.
The project is currently transitioning toward a fully reproducible local setup on any machine by following the sequence below.
These instructions are written for first-time users.

## Prerequisites

- Git (for cloning the repository)
- Basic command-line knowledge
- macOS or Linux operating system (Windows is not supported)

For Windows Users
Native Windows is not supported.
Please install WSL2 with Ubuntu 22.04, open the Ubuntu terminal, and follow the same instructions below.

## Setup Overview
You will run two scripts:
1. bootstrap.sh → prepares your system & Python runtime
2. orchestrator.sh → sets up the project environment
This separation ensures a clean and reproducible setup.

## Setup Instructions

### 1. Clone the Repository

Clone the repository from GitHub and ensure you are on the `new_structure` branch:

```bash
git clone https://github.com/rosemaryturtle/city-scan-automation.git
cd city-scan-automation
git checkout new_structure
```

### 2. Install Python (if not installed)

If Python is not installed on your system, run the bootstrap script to install it via pyenv. This script will install Python 3.11.8 and necessary dependencies.

The bootstrap script will:
- Install system dependencies
- Install and configure pyenv
- Install Python 3.11.8
- Configure your local Python version for this project

- **On macOS**: It uses Homebrew to install pyenv and system libraries.
- **On Linux**: It uses apt to install required packages.

Run the following command:

```bash
bash bootstrap.sh
```

**Note**: Review the `bootstrap.sh` script to ensure it meets your system's requirements before running.
The bootstrap script will modify your system by installing system packages,
pyenv, and Python 3.11, and may update your shell configuration.
Review the script before running if you are unfamiliar with these tools.

If the script installs pyenv for the first time, restart your terminal and run the command again.

### 3. Set Up Virtual Environment and Dependencies

Run the orchestrator script to create a virtual environment, install dependencies, and set up the Jupyter kernel.

This script:
- Enforces Python 3.11 via pyenv
- Creates a new virtual environment
- Installs packages from `requirements.txt`
- Registers a Jupyter kernel named "Cityscan (Python 3.11)"

Execute:

```bash
bash orchestrator.sh
```

When setup is successful, you should see:
- Python 3.11.8 installed via pyenv
- A new virtual environment created
- A Jupyter kernel named: Cityscan (Python 3.11)

### 4. Configure Inputs

Adjust the files in the `inputs/` folder as necessary for your specific project. In this folder, you will need to create a new folder in your local called `AOI/`, where you will store your AOI boundary. The inputs folder is also where city_inputs.yml and menu.yml live, which you will need to modify as input parameters according to your analysis needs. 

### 5. Run the Main Task

Execute the main task to run all sequences defined in `tasks/main.py`:

```bash
python -m tasks --all
```

This will process the tasks in sequence. Ensure the virtual environment is activated if running manually (though the orchestrator script sets it up).

you can do so by:
```bash
source venv/bin/activate
```


## Additional Notes

- The project uses Python 3.11 specifically. The scripts enforce this version.
- If you encounter issues, check the logs in the `logs/` folder.
- For development, use the registered Jupyter kernel "Cityscan (Python 3.11)" in notebooks.


## Troubleshooting

- If pyenv is not found, ensure it's installed via Homebrew (macOS) or apt (Linux).
- If Python 3.11 is not available, the bootstrap script will install it.
- For any errors during setup, check the terminal output and ensure all prerequisites are met.

## Contributing

Please refer to the repository's contribution guidelines if you plan to contribute.
