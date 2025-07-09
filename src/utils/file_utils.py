import os
import sys

def resource_path(relative_path):
    """
    Get the absolute path to a resource, whether running from source or as a
    PyInstaller bundled application. This is the standard solution for
    locating data files, icons, etc., in a bundled executable.
    
    Args:
        relative_path (str): The relative path to the resource from the project root
                             (e.g., 'src/icons/logo.png').
    
    Returns:
        str: The absolute path to the resource.
    """
    try:
        # PyInstaller creates a temporary folder and stores its path in _MEIPASS.
        # This is the base path to use for bundled applications.
        base_path = sys._MEIPASS
    except Exception:
        # If _MEIPASS is not defined, the application is running from source.
        # In this case, the base path is the project's root directory.
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path) 