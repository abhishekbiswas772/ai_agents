"""
Windows PATH Setup Script for BYOM AI Agents

Automatically adds Python Scripts directory to Windows PATH.
Run this after: pip install byom-ai-agents
"""
import os
import sys
import site
from pathlib import Path


def get_scripts_directory() -> Path | None:
    """
    Find the Scripts directory where byom.exe is installed.
    Checks multiple locations in order of preference.
    """
    possible_locations = []
    
    # 1. Virtual environment (if active)
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        venv_scripts = Path(sys.prefix) / "Scripts"
        possible_locations.append(("Virtual Environment", venv_scripts))
    
    # 2. User site-packages Scripts (pip install --user)
    if hasattr(site, 'USER_BASE') and site.USER_BASE:
        user_scripts = Path(site.USER_BASE) / "Scripts"
        possible_locations.append(("User Installation", user_scripts))
    
    # 3. System Python Scripts
    system_scripts = Path(sys.prefix) / "Scripts"
    possible_locations.append(("System Installation", system_scripts))
    
    # 4. Check %APPDATA%\Python\PythonXX\Scripts (common for Windows Store Python)
    appdata = os.environ.get('APPDATA')
    if appdata:
        python_version = f"Python{sys.version_info.major}{sys.version_info.minor}"
        appdata_scripts = Path(appdata) / "Python" / python_version / "Scripts"
        possible_locations.append(("AppData Installation", appdata_scripts))
    
    # Check each location for byom.exe
    print("Searching for BYOM installation...\n")
    for location_name, scripts_path in possible_locations:
        print(f"Checking {location_name}: {scripts_path}")
        if scripts_path.exists():
            byom_exe = scripts_path / "byom.exe"
            if byom_exe.exists():
                print(f"  ✓ Found byom.exe\n")
                return scripts_path
            else:
                print(f"  ✗ Directory exists but byom.exe not found")
        else:
            print(f"  ✗ Directory does not exist")
    
    return None


def add_to_path_windows(directory: str) -> bool:
    """Add directory to Windows user PATH via registry."""
    try:
        import winreg
        
        # Open user environment variables
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r'Environment',
            0,
            winreg.KEY_ALL_ACCESS
        )
        
        # Get current PATH
        try:
            current_path, _ = winreg.QueryValueEx(key, 'Path')
        except FileNotFoundError:
            current_path = ''
        
        # Check if already in PATH
        paths = [p.strip() for p in current_path.split(';') if p.strip()]
        if directory in paths:
            print(f"✓ {directory} is already in PATH")
            winreg.CloseKey(key)
            return True
        
        # Add to PATH
        new_path = current_path + ';' + directory if current_path else directory
        winreg.SetValueEx(key, 'Path', 0, winreg.REG_EXPAND_SZ, new_path)
        winreg.CloseKey(key)
        
        print(f"✓ Added to PATH: {directory}")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    """Main setup function."""
    print("BYOM AI Agents - Windows PATH Setup\n")
    
    if sys.platform != 'win32':
        print("⚠️  This script is only for Windows")
        print("On Linux/Mac, pip install should work directly.\n")
        return
    
    # Find Scripts directory
    scripts_dir = get_scripts_directory()
    
    if not scripts_dir:
        print("\n❌ Could not find BYOM installation!")
        print("\nPossible reasons:")
        print("1. BYOM is not installed - run: pip install byom-ai-agents")
        print("2. You're in a virtual environment - activate it or install globally")
        print("\nIf you just installed BYOM, try running:")
        print("  pip install --user byom-ai-agents")
        print("  python -m byom.setup_path\n")
        return
    
    print(f"Found BYOM at: {scripts_dir}\n")
    
    # Check if running from venv
    in_venv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)

    
    # Add to PATH
    if add_to_path_windows(str(scripts_dir)):
        print("\n✨ Setup complete!")
        print("\n⚠️  IMPORTANT: Restart your terminal for changes to take effect")
        print("\nThen verify installation:")
        print("  byom --version\n")
    else:
        print("\n⚠️  Automatic setup failed.")
        print("\nManual setup instructions:")
        print("1. Press Win + X → System → Advanced system settings")
        print("2. Click 'Environment Variables'")
        print("3. Under 'User variables', select 'Path' → Edit")
        print("4. Click 'New' and add:")
        print(f"   {scripts_dir}")
        print("5. Click OK and restart your terminal\n")


if __name__ == '__main__':
    main()
