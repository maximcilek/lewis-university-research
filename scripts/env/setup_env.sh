#!/bin/bash

# Abort on any error
set -e

readonly ENV_DIRECTORY="env"
readonly VENV_DIRECTORY_PATH=".venv"

validate_python_version() {
  local required_version="$1"
  local active
  active="$(python3 - << 'EOF'
import sys
print(f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
EOF
)"

  if [[ "${active}" != "${required_version}" ]]; then
    echo "ERROR: Python version mismatch"
    echo "Required: ${required_version}"
    echo "Active:   ${active}"
    echo
    echo "Install and activate the correct version using ONE of:"
    echo "  pyenv install ${required_version} && pyenv local ${required_version}"
    echo "  asdf install python ${required_version} && asdf local python ${required_version}"
    echo "  mise install python@${required_version} && mise use python@${required_version}"
    exit 1
  fi
}

main() {

  # Safety check: ensure we are at the root of the repository
  if [ ! -f "${ENV_DIRECTORY}/.python-version" ]; then
    echo "ERROR: Run this script from the repository root."
    exit 1
  fi


  # Validate python version
  local required_python_version
  required_python_version="$(cat ${ENV_DIRECTORY}/.python-version)"
  validate_python_version "${required_python_version}"


  # Check if .venv already exists
  if [ -d "${VENV_DIRECTORY_PATH}" ]; then
    echo "Virtual environment '${VENV_DIRECTORY_PATH}' already exists."
    echo "To recreate, delete it first: rm -rf ${VENV_DIRECTORY_PATH}"
    exit 1
  fi


  echo "Creating Python virtual environment in ${VENV_DIRECTORY_PATH}"
  python3 -m venv "${VENV_DIRECTORY_PATH}"

  echo "Activating virtual environment"
  source "${VENV_DIRECTORY_PATH}/bin/activate"

  echo "Upgrading pip"
  pip install --upgrade pip

  echo "Installing dependencies from ${ENV_DIRECTORY}/requirements.txt"
  pip install -r "${ENV_DIRECTORY}/requirements.txt"

  echo "Environment setup successfully completed."
}

main "$@"

















ACTIVE="$(python3 - << 'EOF'
import sys
print(f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
EOF
)"

if [[ "$ACTIVE" != "$REQUIRED" ]]; then
  echo "ERROR: Python version mismatch"
  echo "Required: $REQUIRED"
  echo "Active:   $ACTIVE"
  echo
  echo "Install and activate the correct version using ONE of:"
  echo "  pyenv install $REQUIRED && pyenv local $REQUIRED"
  echo "  asdf install python $REQUIRED && asdf local python $REQUIRED"
  echo "  mise install python@$REQUIRED && mise use python@$REQUIRED"
  exit 1
fi

if [ -d ".venv" ]; then
  echo ".venv already exists — delete it to recreate."
  exit 1
fi

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r env/requirements.txt

echo "Environment ready."
