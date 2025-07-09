import os
import shutil
import subprocess
import sys
from pathlib import Path

def ensure_required_directories():
    """
    Ensures that directories required for the build exist. If a directory
    is found to be empty, a 'placeholder.txt' file is added to it
    to prevent PyInstaller's glob pattern matching from failing.
    """
    print("--- Checking Required Directories ---")
    dirs_to_check = ['data', 'templates', 'src/icons']
    
    for dir_path in dirs_to_check:
        try:
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)
                print(f"SUCCESS: Created missing directory: {dir_path}")
            
            # Add a placeholder to any empty directory
            if not os.listdir(dir_path):
                placeholder_path = os.path.join(dir_path, 'placeholder.txt')
                with open(placeholder_path, 'w') as f:
                    f.write('This file ensures the directory is not empty for PyInstaller builds.')
                print(f"WARNING: Directory '{dir_path}' was empty. Added 'placeholder.txt' to ensure it's included in the build.")
            else:
                print(f"OK: Directory '{dir_path}' exists and contains files.")
        except Exception as e:
            print(f"FATAL: Failed to check or create directory {dir_path}: {e}")
            sys.exit(1)
    print("--- Directory Check Complete ---")

def cleanup_placeholders():
    """Removes any placeholder files that were created during the build setup."""
    print("\n--- Cleaning Up Placeholder Files ---")
    dirs_to_check = ['data', 'templates', 'src/icons']
    for dir_path in dirs_to_check:
        placeholder_path = os.path.join(dir_path, 'placeholder.txt')
        if os.path.exists(placeholder_path):
            try:
                # Check if the file content indicates it's our placeholder
                with open(placeholder_path, 'r') as f:
                    content = f.read()
                if 'This file ensures the directory is not empty' in content:
                    os.remove(placeholder_path)
                    print(f"SUCCESS: Removed placeholder file from: {dir_path}")
            except Exception as e:
                print(f"WARNING: Could not remove placeholder file from {dir_path}: {e}")
    print("--- Placeholder Cleanup Complete ---")

def clean_build_dirs():
    """Clean up previous build artifacts to ensure a fresh build."""
    print("\n--- Cleaning Previous Build Artifacts ---")
    dirs_to_clean = ['build', 'dist']
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            try:
                shutil.rmtree(dir_name)
                print(f"SUCCESS: Removed directory: {dir_name}/")
            except Exception as e:
                print(f"WARNING: Could not remove {dir_name}/: {e}")
    spec_lock = 'encoding_manager.spec.lock'
    if os.path.exists(spec_lock):
        try:
            os.remove(spec_lock)
            print(f"SUCCESS: Removed spec lock file.")
        except Exception as e:
            print(f"WARNING: Could not remove spec lock file: {e}")
    print("--- Cleanup Complete ---")

def install_requirements():
    """Install all required packages from requirements.txt."""
    print("\n--- Installing Requirements ---")
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
        print("SUCCESS: Requirements are installed.")
    except subprocess.CalledProcessError as e:
        print(f"FATAL: Failed to install requirements: {e}")
        sys.exit(1)
    print("--- Installation Complete ---")

def build_executable():
    """Build the executable using PyInstaller with the spec file."""
    print("\n--- Building Executable with PyInstaller (This may take a few minutes) ---")
    try:
        subprocess.check_call(['pyinstaller', '--noconfirm', 'encoding_manager.spec'])
        print("SUCCESS: PyInstaller finished successfully.")
    except subprocess.CalledProcessError as e:
        print("\n" + "="*60)
        print("FATAL: PyInstaller build failed.")
        print("Please review the output above for specific error messages.")
        print("="*60)
        sys.exit(1)
    print("--- Build Complete ---")

def verify_build():
    """Verify that the executable was created in the expected location."""
    print("\n--- Verifying Build ---")
    exe_path = Path('dist/Encoding Manager/Encoding Manager.exe')
    if exe_path.exists():
        print(f"\nSUCCESS! Executable created at: {exe_path.absolute()}")
        print("Please test the executable thoroughly before distribution.")
    else:
        print("\nFATAL: Build verification failed! Executable not found.")
        sys.exit(1)

def main():
    """Main build process orchestrator."""
    try:
        ensure_required_directories()
        clean_build_dirs()
        install_requirements()
        build_executable()
        verify_build()
    except SystemExit as e:
        if e.code != 0:
            print(f"\nBuild process stopped with exit code {e.code}.")
    except Exception as e:
        print(f"\nFATAL UNEXPECTED ERROR: {e}")
        sys.exit(1)
    finally:
        cleanup_placeholders()

if __name__ == '__main__':
    main() 