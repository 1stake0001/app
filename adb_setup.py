"""
ADB Setup Script for Mobile Privacy Leakage Detector

This script helps users set up their Android device for traffic monitoring:
1. Check ADB connection
2. Configure device proxy settings
3. Verify connectivity
4. Guide user through the setup process

Usage: python adb_setup.py
"""

import subprocess
import sys
import time
import json
from typing import Optional, List

class ADBSetup:
    """ADB setup and configuration manager"""
    
    def __init__(self):
        self.proxy_host = "localhost"
        self.proxy_port = 8080
        
    def check_adb_available(self) -> bool:
        """Check if ADB is available and working"""
        try:
            result = subprocess.run(['adb', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print(f"✅ ADB is available: {result.stdout.strip().split()[0]} {result.stdout.strip().split()[4]}")
                return True
            else:
                print("❌ ADB is installed but not working properly")
                return False
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
            print("❌ ADB command failed")
            return False
        except FileNotFoundError:
            print("❌ ADB is not installed or not in PATH")
            return False
    
    def get_connected_devices(self) -> List[str]:
        """Get list of connected Android devices"""
        try:
            result = subprocess.run(['adb', 'devices'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')[1:]  # Skip header
                devices = [line.split()[0] for line in lines 
                          if line.strip() and 'device' in line]
                return devices
            return []
        except Exception as e:
            print(f"Error getting devices: {e}")
            return []
    
    def check_device_connection(self) -> bool:
        """Check if at least one device is connected"""
        devices = self.get_connected_devices()
        if devices:
            print(f"✅ Found {len(devices)} connected device(s):")
            for i, device in enumerate(devices, 1):
                print(f"   {i}. {device}")
            return True
        else:
            print("❌ No Android devices found")
            return False
    
    def enable_developer_options_guide(self):
        """Guide user through enabling developer options"""
        print("\n📱 ENABLE DEVELOPER OPTIONS:")
        print("1. Open Settings on your Android device")
        print("2. Go to 'About phone' or 'About device'")
        print("3. Find 'Build number' and tap it 7 times")
        print("4. You should see 'You are now a developer!' message")
        print("5. Go back to Settings and look for 'Developer options'")
        print("6. Enable 'USB debugging'")
        print("7. Connect your device via USB cable")
        
        input("\nPress Enter when you have completed these steps...")
    
    def setup_proxy_guide(self):
        """Guide user through proxy setup"""
        print(f"\n🔧 CONFIGURE DEVICE PROXY:")
        print("1. On your Android device, go to Settings > Wi-Fi")
        print("2. Long press on your current Wi-Fi network")
        print("3. Select 'Modify network' or 'Advanced options'")
        print("4. Set Proxy to 'Manual'")
        print(f"5. Enter Proxy hostname: {self.proxy_host}")
        print(f"6. Enter Proxy port: {self.proxy_port}")
        print("7. Save the settings")
        print("\n⚠️  Note: Your device and computer must be on the same network!")
        
        input("\nPress Enter when you have configured the proxy...")
    
    def check_proxy_connectivity(self) -> bool:
        """Test if device can connect through proxy"""
        print(f"\n🔍 Testing proxy connectivity...")
        print("Please open a web browser on your Android device and visit any website")
        print("You should see traffic appearing in the mitmproxy console")
        
        response = input("\nDo you see traffic in mitmproxy? (y/n): ").lower().strip()
        return response == 'y' or response == 'yes'
    
    def get_device_info(self) -> Optional[dict]:
        """Get basic device information"""
        try:
            # Get device model
            model_result = subprocess.run(['adb', 'shell', 'getprop', 'ro.product.model'], 
                                        capture_output=True, text=True, timeout=10)
            
            # Get Android version
            version_result = subprocess.run(['adb', 'shell', 'getprop', 'ro.build.version.release'], 
                                         capture_output=True, text=True, timeout=10)
            
            if model_result.returncode == 0 and version_result.returncode == 0:
                return {
                    "model": model_result.stdout.strip(),
                    "android_version": version_result.stdout.strip()
                }
        except Exception as e:
            print(f"Could not get device info: {e}")
        
        return None
    
    def run_setup_wizard(self):
        """Run the complete setup wizard"""
        print("🚀 MOBILE PRIVACY LEAKAGE DETECTOR - SETUP WIZARD")
        print("=" * 60)
        
        # Step 1: Check ADB
        print("\n1️⃣  CHECKING ADB INSTALLATION...")
        if not self.check_adb_available():
            print("\n📥 Please install ADB:")
            print("- Windows: Download Android SDK Platform Tools")
            print("- macOS: brew install android-platform-tools")
            print("- Linux: sudo apt-get install android-tools-adb")
            return False
        
        # Step 2: Check device connection
        print("\n2️⃣  CHECKING DEVICE CONNECTION...")
        if not self.check_device_connection():
            self.enable_developer_options_guide()
            
            # Check again after user setup
            print("\n🔄 Re-checking device connection...")
            if not self.check_device_connection():
                print("❌ Still no devices found. Please check your connection and try again.")
                return False
        
        # Step 3: Get device info
        print("\n3️⃣  GETTING DEVICE INFORMATION...")
        device_info = self.get_device_info()
        if device_info:
            print(f"✅ Device: {device_info['model']} (Android {device_info['android_version']})")
        else:
            print("⚠️  Could not retrieve device information, but continuing...")
        
        # Step 4: Proxy setup guide
        print("\n4️⃣  PROXY CONFIGURATION...")
        self.setup_proxy_guide()
        
        # Step 5: Final instructions
        print("\n5️⃣  FINAL STEPS:")
        print("1. Start mitmproxy in another terminal:")
        print(f"   mitmproxy -s /app/mitmproxy_addon.py --listen-port {self.proxy_port}")
        print("2. Start the backend server (if not already running)")
        print("3. Open the web dashboard in your browser")
        print("4. Use your mobile device normally - traffic will appear in real-time!")
        
        print("\n✅ Setup complete! You're ready to monitor mobile privacy leaks.")
        return True

def main():
    """Main entry point"""
    setup = ADBSetup()
    
    try:
        success = setup.run_setup_wizard()
        if success:
            print("\n🎉 Setup completed successfully!")
            print("You can now start monitoring mobile traffic for privacy leaks.")
        else:
            print("\n❌ Setup failed. Please resolve the issues above and try again.")
            return 1
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Setup cancelled by user.")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error during setup: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())