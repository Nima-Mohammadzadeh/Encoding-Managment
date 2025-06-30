import os
from PySide6.QtCore import QSettings

# --- Application-wide Settings ---
# These are used by QSettings to create a standard location for your config file.
ORGANIZATION_NAME = "WorkflowOptimizer"
APPLICATION_NAME = "WorkflowOptimizerApp"

# Create a QSettings object. This is our interface to the persistent settings file.
settings = QSettings(ORGANIZATION_NAME, APPLICATION_NAME)

# --- Base Path ---
# We define a base path so we can create default directories relative to the app's location.
# This makes the application more portable.
BASE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# --- Directory Settings ---
# For each setting, we do two things:
# 1. Define a key (a string) that will be used to save/load it.
# 2. Use settings.value() to try and load a previously saved value.
# 3. If no value is found, provide a sensible default.

# Directory for archived job data
ARCHIVE_DIR_KEY = "paths/archive"
DEFAULT_ARCHIVE_DIR = os.path.join(BASE_PATH, "archive")
ARCHIVE_DIR = settings.value(ARCHIVE_DIR_KEY, DEFAULT_ARCHIVE_DIR)

# Directory for template files
TEMPLATES_DIR_KEY = "paths/templates"
DEFAULT_TEMPLATES_DIR = os.path.join(BASE_PATH, "templates")
TEMPLATES_DIR = settings.value(TEMPLATES_DIR_KEY, DEFAULT_TEMPLATES_DIR)

# --- TXT File Paths for Combobox Data ---
# These are the .txt files that the job wizard reads from
CUSTOMER_NAMES_FILE = os.path.join(BASE_PATH, "data", "Customer_names.txt")
LABEL_SIZES_FILE = os.path.join(BASE_PATH, "data", "Label_sizes.txt")
INLAY_TYPES_FILE = os.path.join(BASE_PATH, "data", "Inlay_types.txt")


def ensure_dirs_exist():
    """
    A helper function that can be called on startup to make sure all
    our necessary directories actually exist on the filesystem.
    """
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    os.makedirs(TEMPLATES_DIR, exist_ok=True)
    # Also ensure the data directory exists
    os.makedirs(os.path.join(BASE_PATH, "data"), exist_ok=True)


def read_txt_file(file_path):
    """
    Helper function to read a .txt file and return a list of non-empty lines.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            lines = [line.strip() for line in file if line.strip()]
        return lines
    except FileNotFoundError:
        return []


def write_txt_file(file_path, items):
    """
    Helper function to write a list of items to a .txt file.
    Each item goes on its own line.
    """
    try:
        with open(file_path, "w", encoding="utf-8") as file:
            for item in items:
                file.write(f"{item}\n")
        return True
    except Exception as e:
        print(f"Error writing to {file_path}: {e}")
        return False
