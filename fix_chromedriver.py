"""Script to manually download correct ChromeDriver version"""
import os
import shutil
import requests
import zipfile
import platform
from pathlib import Path

def fix_chromedriver():
    """Download correct 64-bit ChromeDriver"""
    print("Fixing ChromeDriver architecture issue...")
    
    # Get Chrome version (simplified - you may need to adjust)
    chrome_version = "142.0.7444.175"  # Latest as of now
    
    # Determine architecture
    if platform.machine() == 'AMD64':
        arch = "win64"
        print(f"Detected 64-bit system, downloading {arch} version...")
    else:
        arch = "win32"
        print(f"Detected 32-bit system, downloading {arch} version...")
    
    # Download URL
    url = f"https://storage.googleapis.com/chrome-for-testing-public/{chrome_version}/{arch}/chromedriver-{arch}.zip"
    
    # Cache directory
    cache_dir = Path.home() / '.wdm' / 'drivers' / 'chromedriver' / 'win64' / chrome_version
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    zip_path = cache_dir / 'chromedriver.zip'
    exe_path = cache_dir / 'chromedriver.exe'
    
    # Download if not exists
    if not exe_path.exists():
        print(f"Downloading from {url}...")
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        with open(zip_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        # Extract
        print("Extracting...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(cache_dir)
        
        # Find chromedriver.exe in extracted files
        for file in cache_dir.rglob('chromedriver.exe'):
            if file != exe_path:
                file.rename(exe_path)
                break
        
        # Clean up zip
        zip_path.unlink()
        
        print(f"ChromeDriver installed at: {exe_path}")
    else:
        print(f"ChromeDriver already exists at: {exe_path}")
    
    return str(exe_path)

if __name__ == "__main__":
    try:
        path = fix_chromedriver()
        print(f"\n✓ Success! ChromeDriver path: {path}")
    except Exception as e:
        print(f"\n✗ Error: {e}")

