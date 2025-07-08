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

# Directory for job documents
JOB_DIR_KEY = "paths/jobs"
DEFAULT_JOB_DIR = os.path.join(BASE_PATH, "jobs")
JOB_DIR = settings.value(JOB_DIR_KEY, DEFAULT_JOB_DIR)

# Directory for active job source files
ACTIVE_JOBS_SOURCE_DIR_KEY = "paths/active_jobs_source"
DEFAULT_ACTIVE_JOBS_SOURCE_DIR = os.path.join(BASE_PATH, "active_jobs_source")
ACTIVE_JOBS_SOURCE_DIR = settings.value(ACTIVE_JOBS_SOURCE_DIR_KEY, DEFAULT_ACTIVE_JOBS_SOURCE_DIR)

# Template base path for EPC conversion functionality (from EPC script)
TEMPLATE_BASE_PATH_KEY = "paths/template_base"
DEFAULT_TEMPLATE_BASE_PATH = r'Z:\3 Encoding and Printing Files\Templates'
TEMPLATE_BASE_PATH = settings.value(TEMPLATE_BASE_PATH_KEY, DEFAULT_TEMPLATE_BASE_PATH)

# Serial numbers base path for centralized serial number management
SERIAL_NUMBERS_PATH_KEY = "paths/serial_numbers"
DEFAULT_SERIAL_NUMBERS_PATH = os.path.join(BASE_PATH, "serial_numbers")  # Local directory for now
SERIAL_NUMBERS_PATH = settings.value(SERIAL_NUMBERS_PATH_KEY, DEFAULT_SERIAL_NUMBERS_PATH)

# --- Monitoring Performance Settings ---
# These settings control how aggressively the application monitors directories for changes
# Useful for optimizing performance in multi-user environments or with network drives

# Enable/disable real-time file system monitoring
ENABLE_FILE_MONITORING_KEY = "monitoring/enable_file_monitoring"
DEFAULT_ENABLE_FILE_MONITORING = True
ENABLE_FILE_MONITORING = settings.value(ENABLE_FILE_MONITORING_KEY, DEFAULT_ENABLE_FILE_MONITORING, type=bool)

# Maximum number of directories to monitor simultaneously
MAX_MONITORED_DIRECTORIES_KEY = "monitoring/max_directories"
DEFAULT_MAX_MONITORED_DIRECTORIES = 50
MAX_MONITORED_DIRECTORIES = settings.value(MAX_MONITORED_DIRECTORIES_KEY, DEFAULT_MAX_MONITORED_DIRECTORIES, type=int)

# Maximum depth to monitor subdirectories
MAX_MONITORING_DEPTH_KEY = "monitoring/max_depth"
DEFAULT_MAX_MONITORING_DEPTH = 3
MAX_MONITORING_DEPTH = settings.value(MAX_MONITORING_DEPTH_KEY, DEFAULT_MAX_MONITORING_DEPTH, type=int)

# Refresh debounce timer (milliseconds) - how long to wait after changes before refreshing
REFRESH_DEBOUNCE_MS_KEY = "monitoring/refresh_debounce_ms"
DEFAULT_REFRESH_DEBOUNCE_MS = 500
REFRESH_DEBOUNCE_MS = settings.value(REFRESH_DEBOUNCE_MS_KEY, DEFAULT_REFRESH_DEBOUNCE_MS, type=int)

# Periodic refresh interval for network drives (milliseconds)
PERIODIC_REFRESH_INTERVAL_KEY = "monitoring/periodic_refresh_interval"
DEFAULT_PERIODIC_REFRESH_INTERVAL = 30000  # 30 seconds
PERIODIC_REFRESH_INTERVAL = settings.value(PERIODIC_REFRESH_INTERVAL_KEY, DEFAULT_PERIODIC_REFRESH_INTERVAL, type=int)

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
    os.makedirs(ACTIVE_JOBS_SOURCE_DIR, exist_ok=True)
    os.makedirs(SERIAL_NUMBERS_PATH, exist_ok=True)  # Ensure serial numbers directory exists
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


def save_template_base_path(path):
    """Save the template base path to settings."""
    settings.setValue(TEMPLATE_BASE_PATH_KEY, path)
    global TEMPLATE_BASE_PATH
    TEMPLATE_BASE_PATH = path


def get_template_base_path():
    """Get the current template base path."""
    return TEMPLATE_BASE_PATH


def save_serial_numbers_path(path):
    """Save the serial numbers path to settings."""
    settings.setValue(SERIAL_NUMBERS_PATH_KEY, path)
    global SERIAL_NUMBERS_PATH
    SERIAL_NUMBERS_PATH = path


def get_serial_numbers_path():
    """Get the current serial numbers path."""
    return SERIAL_NUMBERS_PATH


def save_monitoring_settings(enable_monitoring=None, max_directories=None, max_depth=None, 
                            debounce_ms=None, periodic_interval=None):
    """Save monitoring performance settings."""
    global ENABLE_FILE_MONITORING, MAX_MONITORED_DIRECTORIES, MAX_MONITORING_DEPTH
    global REFRESH_DEBOUNCE_MS, PERIODIC_REFRESH_INTERVAL
    
    if enable_monitoring is not None:
        settings.setValue(ENABLE_FILE_MONITORING_KEY, enable_monitoring)
        ENABLE_FILE_MONITORING = enable_monitoring
        
    if max_directories is not None:
        settings.setValue(MAX_MONITORED_DIRECTORIES_KEY, max_directories)
        MAX_MONITORED_DIRECTORIES = max_directories
        
    if max_depth is not None:
        settings.setValue(MAX_MONITORING_DEPTH_KEY, max_depth)
        MAX_MONITORING_DEPTH = max_depth
        
    if debounce_ms is not None:
        settings.setValue(REFRESH_DEBOUNCE_MS_KEY, debounce_ms)
        REFRESH_DEBOUNCE_MS = debounce_ms
        
    if periodic_interval is not None:
        settings.setValue(PERIODIC_REFRESH_INTERVAL_KEY, periodic_interval)
        PERIODIC_REFRESH_INTERVAL = periodic_interval


def get_monitoring_settings():
    """Get current monitoring settings as a dictionary."""
    return {
        'enable_monitoring': ENABLE_FILE_MONITORING,
        'max_directories': MAX_MONITORED_DIRECTORIES,
        'max_depth': MAX_MONITORING_DEPTH,
        'debounce_ms': REFRESH_DEBOUNCE_MS,
        'periodic_interval': PERIODIC_REFRESH_INTERVAL
    }
