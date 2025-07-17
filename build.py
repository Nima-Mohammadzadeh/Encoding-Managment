import os
import sys
import shutil
import subprocess
from pathlib import Path

def clean_previous_build():
    """Clean up previous build artifacts"""
    print("Cleaning previous build artifacts...")
    
    # Remove build and dist directories if they exist
    for dir_name in ['build', 'dist']:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"Removed {dir_name} directory")
    
    # Remove spec file if it exists
    spec_file = 'encoding_manager.spec'
    if os.path.exists(spec_file):
        os.remove(spec_file)
        print(f"Removed {spec_file}")

def run_pyinstaller():
    """Run PyInstaller with direct command line arguments"""
    print("Building executable with PyInstaller...")
    
    # Define the PyInstaller command with all necessary options
    cmd = [
        'pyinstaller',
        '--name=encoding_manager',
        '--onefile',
        '--windowed',
        '--icon=src/icons/logo.png',
        '--add-data=src/icons;src/icons',
        '--add-data=src/style.qss;src',
        '--add-data=data;data',
        '--exclude-module=PyQt6',
        '--exclude-module=PyQt6.QtCore',
        '--exclude-module=PyQt6.QtGui',
        '--exclude-module=PyQt6.QtWidgets',
        '--exclude-module=PyQt6.QtSvg',
        '--exclude-module=PyQt6-sip',
        'main.py'
    ]
    
    # Add hidden imports
    hidden_imports = [
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'PySide6.QtSvg',
        'pymupdf',
        'fitz',
        'qt_material',
        'json',
        'datetime',
        'os',
        'sys',
        'shutil',
        'platform',
        'webbrowser',
        'subprocess',
        'logging'
    ]
    
    for imp in hidden_imports:
        cmd.insert(-1, f'--hidden-import={imp}')
    
    # Run the PyInstaller command
    subprocess.run(cmd)

def copy_additional_files():
    """Copy any additional files needed for the application"""
    print("Copying additional files...")
    
    dist_dir = Path('dist')
    
    # Create directories if they don't exist
    os.makedirs(dist_dir, exist_ok=True)
    os.makedirs(dist_dir / 'active_jobs', exist_ok=True)
    os.makedirs(dist_dir / 'active_jobs_source', exist_ok=True)
    os.makedirs(dist_dir / 'archive', exist_ok=True)
    os.makedirs(dist_dir / 'logs', exist_ok=True)
    os.makedirs(dist_dir / 'templates', exist_ok=True)
    os.makedirs(dist_dir / 'serial_numbers', exist_ok=True)
    
    # Copy README and other documentation files
    for doc_file in Path().glob('*.md'):
        shutil.copy(doc_file, dist_dir / doc_file.name)
        print(f"Copied {doc_file.name}")
    
    # Copy settings.json if it exists
    if os.path.exists('settings.json'):
        shutil.copy('settings.json', dist_dir / 'settings.json')
        print("Copied settings.json")

def main():
    """Main build function"""
    print("Starting build process for Encoding Manager...")
    
    # Clean previous build artifacts
    clean_previous_build()
    
    # Run PyInstaller
    run_pyinstaller()
    
    # Copy additional files
    copy_additional_files()
    
    print("\nBuild completed! Executable is in the 'dist' folder.")
    print("You can distribute the entire 'dist' folder to users.")

if __name__ == "__main__":
    main() 