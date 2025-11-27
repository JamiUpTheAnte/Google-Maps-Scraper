"""
Helper script to download and install the correct ChromeDriver for your system
"""

import requests
import zipfile
import os
import platform
import subprocess
import shutil

def get_chrome_version():
    """Get installed Chrome version"""
    try:
        if platform.system() == 'Windows':
            # Try to get Chrome version on Windows
            result = subprocess.run(
                ['reg', 'query', 'HKEY_CURRENT_USER\\Software\\Google\\Chrome\\BLBeacon', '/v', 'version'],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'version' in line.lower():
                        version = line.split()[-1]
                        return version.split('.')[0]  # Return major version
        return None
    except Exception as e:
        print(f"Could not detect Chrome version: {e}")
        return None

def download_chromedriver():
    """Download the correct ChromeDriver"""
    print("Detecting system architecture...")

    is_64bit = platform.machine().endswith('64')
    system = platform.system()

    print(f"System: {system}, 64-bit: {is_64bit}")

    # Get Chrome version
    chrome_version = get_chrome_version()
    if not chrome_version:
        chrome_version = "142"  # Default to recent version
        print(f"Using default Chrome version: {chrome_version}")
    else:
        print(f"Detected Chrome version: {chrome_version}")

    # Determine correct download URL
    if system == 'Windows':
        if is_64bit:
            platform_str = 'win64'
        else:
            platform_str = 'win32'
    elif system == 'Darwin':
        platform_str = 'mac-x64'
    else:
        platform_str = 'linux64'

    # Find latest ChromeDriver version for this Chrome version
    print(f"Fetching ChromeDriver for platform: {platform_str}")

    try:
        # Get latest version info
        version_url = f"https://googlechromelabs.github.io/chrome-for-testing/LATEST_RELEASE_{chrome_version}"
        response = requests.get(version_url)
        if response.status_code == 200:
            version = response.text.strip()
        else:
            version = f"{chrome_version}.0.0.0"

        print(f"ChromeDriver version: {version}")

        # Download URL
        download_url = f"https://storage.googleapis.com/chrome-for-testing-public/{version}/{platform_str}/chromedriver-{platform_str}.zip"
        print(f"Downloading from: {download_url}")

        # Download
        response = requests.get(download_url)
        if response.status_code != 200:
            print(f"Failed to download. Status code: {response.status_code}")
            return False

        # Save zip file
        zip_path = "chromedriver.zip"
        with open(zip_path, 'wb') as f:
            f.write(response.content)

        print("Extracting ChromeDriver...")

        # Extract
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(".")

        # Move to correct location
        extracted_dir = f"chromedriver-{platform_str}"
        if system == 'Windows':
            exe_name = 'chromedriver.exe'
        else:
            exe_name = 'chromedriver'

        source = os.path.join(extracted_dir, exe_name)
        dest = exe_name

        if os.path.exists(source):
            if os.path.exists(dest):
                os.remove(dest)
            shutil.move(source, dest)
            print(f"✓ ChromeDriver installed: {os.path.abspath(dest)}")

            # Make executable on Unix systems
            if system != 'Windows':
                os.chmod(dest, 0o755)

            # Cleanup
            os.remove(zip_path)
            shutil.rmtree(extracted_dir)

            return True
        else:
            print(f"Could not find {exe_name} in extracted files")
            return False

    except Exception as e:
        print(f"Error downloading ChromeDriver: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("ChromeDriver Setup")
    print("=" * 60)
    success = download_chromedriver()
    if success:
        print("\n✓ Setup complete! You can now run the scraper.")
    else:
        print("\n✗ Setup failed. Please download ChromeDriver manually.")
        print("Visit: https://googlechromelabs.github.io/chrome-for-testing/")
