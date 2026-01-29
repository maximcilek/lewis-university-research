import sys
import importlib

REQUIRED_PYTHON = (3, 11)  # e.g. Python 3.11.x

REQUIRED_PACKAGES = {
    "pandas": "1.5.0",
    "pyarrow": "11.0.0",
    "matplotlib": "3.8.0",
}

def check_python_version():
    current = sys.version_info
    if current < REQUIRED_PYTHON:
        print(f"WARNING: Python version {REQUIRED_PYTHON[0]}.{REQUIRED_PYTHON[1]} or higher is required.")
        print(f"Current version: {current[0]}.{current[1]}.{current[2]}")
    else:
        print(f"Python version OK: {current[0]}.{current[1]}.{current[2]}")

def check_packages():
    print("Checking required packages and versions:")
    for pkg, ver in REQUIRED_PACKAGES.items():
        try:
            module = importlib.import_module(pkg)
            installed_ver = getattr(module, "__version__", None)
            if installed_ver is None:
                print(f"  - {pkg}: version unknown (module loaded)")
            elif installed_ver < ver:
                print(f"  - {pkg}: version {installed_ver} found, but {ver} required or higher. Please upgrade.")
            else:
                print(f"  - {pkg}: version {installed_ver} OK")
        except ImportError:
            print(f"  - {pkg}: NOT INSTALLED")

if __name__ == "__main__":
    check_python_version()
    check_packages()