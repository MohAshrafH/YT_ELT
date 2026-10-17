# Python Virtual Environment Guide

This guide explains your existing virtual environment and how to activate it in Visual Studio Code (VS Code) on Windows.

Your project already contains a `venv` folder. Its configuration records **Python 3.13.5**. You do not need to recreate it each time you work.

## 1. What is a virtual environment?

A virtual environment is a separate Python workspace for a project's installed packages.

For example, this YouTube project might need `requests`, while another project might need a different version of the same package. Each project can have its own environment so their dependencies stay separate.

A virtual environment isolates Python packages. It is not a separate computer or a Docker container.

Your existing environment has this structure:

```text
YT_ELT
└── venv
    ├── Include
    ├── Lib
    ├── Scripts
    │   ├── Activate.ps1
    │   ├── activate.bat
    │   ├── python.exe
    │   └── pip.exe
    └── pyvenv.cfg
```

| Item | Purpose |
|---|---|
| `Lib` | Holds installed packages, mainly under `site-packages`. |
| `Scripts\python.exe` | The Python executable for this environment. |
| `Scripts\pip.exe` | The package installer for this environment. |
| Activation scripts | Tell the terminal to use this environment. |
| `pyvenv.cfg` | Records the environment's configuration. |

## 2. Open the terminal in VS Code

Select **Terminal → New Terminal**. A terminal panel opens at the bottom.

The following steps assume **PowerShell**. A PowerShell prompt normally looks similar to:

```text
PS F:\...\YT_ELT>
```

The prompt is information displayed by the terminal. **Type only the commands shown below**, then press **Enter** after each command.

## 3. Confirm the current folder

```powershell
Get-Location
```

This displays the terminal's current folder. It should end with:

```text
\Project Directory\YT_ELT
```

If you are somewhere else, enter:

```powershell
Set-Location "F:\Data Engineering\Training\Data Engineering Automation\Data Engineering Project SQL, Python, Airflow, Docker, CICD - Udemy\Project Directory\YT_ELT"
```

`Set-Location` changes the terminal's working folder. The quotation marks keep the path together because it contains spaces.

## 4. Activate the existing environment

```powershell
.\venv\Scripts\Activate.ps1
```

| Part | Meaning |
|---|---|
| `.\` | Start from the current folder. |
| `venv` | Enter your existing environment folder. |
| `Scripts` | Find the environment's commands. |
| `Activate.ps1` | Run the PowerShell activation script. |

After activation, the prompt will usually look like:

```text
(venv) PS F:\...\YT_ELT>
```

**`(venv)` indicates that this terminal has activated the environment.**

Activation changes the current terminal's settings so that commands such as `python` use your environment's executable first. It does not create or reinstall the environment.

Your `venv` already exists, so you do **not** need to run `python -m venv venv` again. That command is for creating an environment.

## 5. Verify which Python is being used

```powershell
python -c "import sys; print(sys.executable)"
```

This asks Python to print the location of its running executable:

- `-c` tells Python to execute the code inside the quotation marks.
- `import sys` loads Python's built-in system information module.
- `print(sys.executable)` displays the executable's path.

The result should end with:

```text
\YT_ELT\venv\Scripts\python.exe
```

This is a stronger confirmation than the `(venv)` prefix alone.

Check the Python version:

```powershell
python --version
```

Based on your environment's configuration, the expected version is:

```text
Python 3.13.5
```

Check which package installer belongs to this Python:

```powershell
python -m pip --version
```

The displayed package path should be inside your project's `venv`.

`python -m pip` means “run the `pip` module using this Python.” This helps keep Python and the package installer matched.

## 6. View installed packages

```powershell
python -m pip list
```

This lists the packages and versions available in the environment. It does not install anything.

For context, the following command would install a package into the active environment and change its contents:

```powershell
python -m pip install requests
```

**Installing packages is not required to activate the environment.** The installation command above is an explanation, not a required step.

## 7. Select the same interpreter in VS Code

VS Code also has a Python interpreter selection used by its Python features, including running and debugging code.

1. Press **Ctrl + Shift + P**.
2. Type **Python: Select Interpreter**.
3. Select the interpreter whose path ends with `YT_ELT\venv\Scripts\python.exe`.
4. If it is missing from the list, choose **Enter interpreter path** and browse to that executable.

The full interpreter path for this project is:

```text
F:\Data Engineering\Training\Data Engineering Automation\Data Engineering Project SQL, Python, Airflow, Docker, CICD - Udemy\Project Directory\YT_ELT\venv\Scripts\python.exe
```

If **Python: Select Interpreter** is unavailable, check that Microsoft's Python extension is installed and enabled in VS Code.

Interpreter selection and terminal activation are related but separate:

- **Interpreter selection** chooses Python for VS Code's Python features.
- **Terminal activation** chooses Python for commands in that terminal.

Keeping both pointed at `venv` avoids confusion.

## 8. Deactivate when finished

In the activated terminal, enter:

```powershell
deactivate
```

The `(venv)` prefix should disappear. This restores the terminal's previous settings.

**The environment and its installed packages remain on disk.** You can activate it again later with the same activation command.

Activation applies to each terminal session. A newly opened terminal may need activation again, although VS Code may activate the selected interpreter automatically.

## 9. If PowerShell blocks activation

Only if you receive an error saying scripts cannot run because script execution is disabled, enter:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
```

This changes the script execution policy for the **current PowerShell session only**:

- `-Scope Process` limits the change to this session.
- `RemoteSigned` generally permits local scripts while requiring downloaded scripts to be signed, unless they are unblocked.

An organization's enforced policy can still override it.

Then retry activation:

```powershell
.\venv\Scripts\Activate.ps1
```

## 10. If the terminal is Command Prompt

If your terminal uses **Command Prompt (`cmd`)** instead of PowerShell, activate with:

```bat
venv\Scripts\activate.bat
```

The different activation files exist because different terminal shells use different script formats.

## 11. `venv` and `.env` are different

| Item | Purpose |
|---|---|
| `venv` folder | Holds the Python environment and installed packages. |
| `.env` file | Typically holds configuration values such as API keys. |

**Activating `venv` does not automatically load `.env`.** Your application needs to load those configuration values separately.

## Quick reference

Run these commands from the `YT_ELT` folder in PowerShell:

```powershell
# Activate the existing environment
.\venv\Scripts\Activate.ps1

# Confirm the Python executable
python -c "import sys; print(sys.executable)"

# Check the Python version
python --version

# View installed packages
python -m pip list

# Leave the environment when finished
deactivate
```
