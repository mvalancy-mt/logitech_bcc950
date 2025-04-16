#!/usr/bin/env python3
"""
Logitech BCC950 Camera Control Script

This script controls the pan, tilt, and zoom functions of the Logitech BCC950 ConferenceCam
using v4l2-ctl commands in Linux via Python.

Author: Matthew Valancy
"""

import os
import sys
import time
import argparse
import subprocess
import platform
import re
import glob
from pathlib import Path


class BCC950Controller:
    """Control class for the Logitech BCC950 Camera"""
    
    def __init__(self, device=None):
        self.device = device or "/dev/video0"
        self.config_file = Path.home() / ".bcc950_config"
        self.pan_speed = 1
        self.tilt_speed = 1
        self.zoom_step = 10
        
        # Load config if exists
        self.load_config()
    
    def load_config(self):
        """Load config from file if it exists"""
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                for line in f:
                    if '=' in line:
                        key, value = line.strip().split('=', 1)
                        if key == "DEVICE":
                            self.device = value
                        elif key == "PAN_SPEED":
                            self.pan_speed = int(value)
                        elif key == "TILT_SPEED":
                            self.tilt_speed = int(value)
                        elif key == "ZOOM_STEP":
                            self.zoom_step = int(value)
    
    def save_config(self):
        """Save current configuration to file"""
        with open(self.config_file, 'w') as f:
            f.write(f"DEVICE={self.device}\n")
            f.write(f"PAN_SPEED={self.pan_speed}\n")
            f.write(f"TILT_SPEED={self.tilt_speed}\n")
            f.write(f"ZOOM_STEP={self.zoom_step}\n")
    
    def run_command(self, command, capture_output=False):
        """Run a shell command and return the result"""
        try:
            if capture_output:
                result = subprocess.run(command, shell=True, check=True, 
                                       capture_output=True, text=True)
                return result.stdout
            else:
                subprocess.run(command, shell=True, check=True)
                return True
        except subprocess.CalledProcessError as e:
            print(f"Error running command: {command}")
            print(f"Error details: {e}")
            return False
    
    def detect_os(self):
        """Detect the current operating system"""
        if os.path.exists('/etc/os-release'):
            with open('/etc/os-release', 'r') as f:
                for line in f:
                    if line.startswith('ID='):
                        return line.split('=')[1].strip().strip('"')
        return platform.system().lower()
    
    def install_prerequisites(self):
        """Install required packages based on detected OS"""
        print("Installing prerequisites...")
        
        os_name = self.detect_os()
        print(f"Detected OS: {os_name}")
        
        if os_name in ['ubuntu', 'debian']:
            cmd = "sudo apt-get update && sudo apt-get install -y v4l-utils"
        elif os_name == 'fedora':
            cmd = "sudo dnf install -y v4l-utils"
        elif os_name in ['centos', 'rhel']:
            cmd = "sudo yum install -y v4l-utils"
        elif os_name == 'arch':
            cmd = "sudo pacman -Sy v4l-utils"
        else:
            print(f"Unsupported OS: {os_name}")
            print("Please install v4l-utils manually.")
            return False
        
        return self.run_command(cmd)
    
    def find_camera(self):
        """Find the Logitech BCC950 camera device"""
        print("Looking for Logitech BCC950 camera...")
        
        # List all video devices
        devices_output = self.run_command("v4l2-ctl --list-devices", True)
        print(devices_output)
        
        # Try to find BCC950 in the device list
        if 'BCC950' in devices_output:
            # Find device path
            pattern = r"BCC950.*?\n(.*?/dev/video\d+)"
            match = re.search(pattern, devices_output, re.DOTALL)
            if match:
                dev_path = match.group(1).strip()
                print(f"Found Logitech BCC950 at: {dev_path}")
                self.device = dev_path
                self.save_config()
                return True
        
        # If not found by name, check all video devices for pan/tilt support
        print("Checking all video devices for PTZ support...")
        all_video_devices = glob.glob('/dev/video*')
        
        for dev in all_video_devices:
            print(f"Testing {dev}...")
            # Check if device supports pan_speed control
            output = self.run_command(f"v4l2-ctl -d {dev} --list-ctrls", True)
            if output and 'pan_speed' in output:
                print(f"Found compatible PTZ camera at: {dev}")
                self.device = dev
                self.save_config()
                return True
        
        print(f"No compatible camera found. Using default device: {self.device}")
        return False
    
    def test_camera(self):
        """Test camera connection and controls"""
        print("Testing camera controls...")
        
        if not os.path.exists(self.device):
            print(f"ERROR: Camera device {self.device} does not exist.")
            return False
        
        # Get list of available controls
        print("Available camera controls:")
        controls_output = self.run_command(f"v4l2-ctl -d {self.device} --list-ctrls", True)
        print(controls_output)
        
        # Test controls
        has_pan = 'pan_speed' in controls_output
        has_tilt = 'tilt_speed' in controls_output
        has_zoom = 'zoom_absolute' in controls_output
        
        if has_pan:
            print("Pan control is available.")
        else:
            print("WARNING: Pan control not found for this camera.")
            
        if has_tilt:
            print("Tilt control is available.")
        else:
            print("WARNING: Tilt control not found for this camera.")
            
        if has_zoom:
            print("Zoom control is available.")
        else:
            print("WARNING: Zoom control not found for this camera.")
            
        return has_pan and has_tilt and has_zoom
    
    def setup(self):
        """Install prerequisites, detect camera, and test connection"""
        print("Setting up Logitech BCC950 camera control...")
        
        # Check if v4l2-ctl is installed
        if not self.run_command("which v4l2-ctl", True):
            if not self.install_prerequisites():
                return False
        else:
            print("v4l2-ctl is already installed.")
        
        # Detect camera
        self.find_camera()
        
        # Test camera connection
        self.test_camera()
        
        print("Setup complete.")
        return True
    
    def pan_left(self):
        """Pan camera left"""
        print("Panning left...")
        self.run_command(f"v4l2-ctl -d {self.device} -c pan_speed=-{self.pan_speed}")
        time.sleep(0.1)
        self.run_command(f"v4l2-ctl -d {self.device} -c pan_speed=0")
        
    def pan_right(self):
        """Pan camera right"""
        print("Panning right...")
        self.run_command(f"v4l2-ctl -d {self.device} -c pan_speed={self.pan_speed}")
        time.sleep(0.1)
        self.run_command(f"v4l2-ctl -d {self.device} -c pan_speed=0")
        
    def tilt_up(self):
        """Tilt camera up"""
        print("Tilting up...")
        self.run_command(f"v4l2-ctl -d {self.device} -c tilt_speed={self.tilt_speed}")
        time.sleep(0.1)
        self.run_command(f"v4l2-ctl -d {self.device} -c tilt_speed=0")
        
    def tilt_down(self):
        """Tilt camera down"""
        print("Tilting down...")
        self.run_command(f"v4l2-ctl -d {self.device} -c tilt_speed=-{self.tilt_speed}")
        time.sleep(0.1)
        self.run_command(f"v4l2-ctl -d {self.device} -c tilt_speed=0")
        
    def zoom_in(self):
        """Zoom camera in"""
        print("Zooming in...")
        # Get current zoom value
        zoom_output = self.run_command(f"v4l2-ctl -d {self.device} --get-ctrl=zoom_absolute", True)
        current_zoom = int(zoom_output.split('=')[1].strip())
        
        # Calculate new zoom value
        new_zoom = min(current_zoom + self.zoom_step, 500)
        self.run_command(f"v4l2-ctl -d {self.device} -c zoom_absolute={new_zoom}")
        
    def zoom_out(self):
        """Zoom camera out"""
        print("Zooming out...")
        # Get current zoom value
        zoom_output = self.run_command(f"v4l2-ctl -d {self.device} --get-ctrl=zoom_absolute", True)
        current_zoom = int(zoom_output.split('=')[1].strip())
        
        # Calculate new zoom value
        new_zoom = max(current_zoom - self.zoom_step, 100)
        self.run_command(f"v4l2-ctl -d {self.device} -c zoom_absolute={new_zoom}")
        
    def reset_position(self):
        """Reset camera position"""
        print("Resetting camera position...")
        # For relative controls, we need to center by briefly moving in both directions
        self.run_command(f"v4l2-ctl -d {self.device} -c pan_speed=1")
        time.sleep(0.1)
        self.run_command(f"v4l2-ctl -d {self.device} -c pan_speed=0")
        time.sleep(0.1)
        self.run_command(f"v4l2-ctl -d {self.device} -c pan_speed=-1")
        time.sleep(0.1)
        self.run_command(f"v4l2-ctl -d {self.device} -c pan_speed=0")
        
        self.run_command(f"v4l2-ctl -d {self.device} -c tilt_speed=1")
        time.sleep(0.1)
        self.run_command(f"v4l2-ctl -d {self.device} -c tilt_speed=0")
        time.sleep(0.1)
        self.run_command(f"v4l2-ctl -d {self.device} -c tilt_speed=-1")
        time.sleep(0.1)
        self.run_command(f"v4l2-ctl -d {self.device} -c tilt_speed=0")
        
        # Reset zoom to default/minimum
        self.run_command(f"v4l2-ctl -d {self.device} -c zoom_absolute=100")
        
    def list_devices(self):
        """List available camera devices"""
        print("Available camera devices:")
        self.run_command("v4l2-ctl --list-devices")
        
    def show_info(self):
        """Show camera information and controls"""
        print(f"Camera information for {self.device}:")
        self.run_command(f"v4l2-ctl -d {self.device} --all")
        
    def run_demo(self):
        """Run a demonstration sequence showing camera capabilities"""
        print("Running camera demonstration sequence...")
        
        # Make sure camera exists
        if not os.path.exists(self.device):
            print(f"ERROR: Camera device {self.device} does not exist.")
            return False
        
        print("Starting demo in 3 seconds...")
        time.sleep(3)
        
        # Reset zoom to minimum to start
        self.run_command(f"v4l2-ctl -d {self.device} -c zoom_absolute=100")
        time.sleep(1)
        
        print("Beginning circular sweep pattern with zoom...")
        
        # Start with pan left while zooming in
        print("Panning left while zooming in...")
        self.run_command(f"v4l2-ctl -d {self.device} -c pan_speed=-{self.pan_speed}")
        for zoom in range(100, 301, 20):
            self.run_command(f"v4l2-ctl -d {self.device} -c zoom_absolute={zoom}")
            time.sleep(0.3)
        self.run_command(f"v4l2-ctl -d {self.device} -c pan_speed=0")
        time.sleep(1)
        
        # Tilt up while maintaining zoom
        print("Tilting up...")
        self.run_command(f"v4l2-ctl -d {self.device} -c tilt_speed={self.tilt_speed}")
        time.sleep(3)
        self.run_command(f"v4l2-ctl -d {self.device} -c tilt_speed=0")
        time.sleep(1)
        
        # Pan right while zooming out
        print("Panning right while zooming out...")
        self.run_command(f"v4l2-ctl -d {self.device} -c pan_speed={self.pan_speed}")
        for zoom in range(300, 99, -20):
            self.run_command(f"v4l2-ctl -d {self.device} -c zoom_absolute={zoom}")
            time.sleep(0.3)
        self.run_command(f"v4l2-ctl -d {self.device} -c pan_speed=0")
        time.sleep(1)
        
        # Tilt down to complete the circle
        print("Tilting down...")
        self.run_command(f"v4l2-ctl -d {self.device} -c tilt_speed=-{self.tilt_speed}")
        time.sleep(3)
        self.run_command(f"v4l2-ctl -d {self.device} -c tilt_speed=0")
        time.sleep(1)
        
        # Do a full zoom-in/zoom-out cycle
        print("Demonstrating full zoom range...")
        # Zoom all the way in
        for zoom in range(100, 501, 20):
            self.run_command(f"v4l2-ctl -d {self.device} -c zoom_absolute={zoom}")
            time.sleep(0.1)
        time.sleep(2)
        # Zoom all the way out
        for zoom in range(500, 99, -20):
            self.run_command(f"v4l2-ctl -d {self.device} -c zoom_absolute={zoom}")
            time.sleep(0.1)
        
        # Perform a diagonal pattern
        print("Performing diagonal movement...")
        # Diagonal up-right
        self.run_command(f"v4l2-ctl -d {self.device} -c pan_speed={self.pan_speed}")
        self.run_command(f"v4l2-ctl -d {self.device} -c tilt_speed={self.tilt_speed}")
        time.sleep(2)
        self.run_command(f"v4l2-ctl -d {self.device} -c pan_speed=0")
        self.run_command(f"v4l2-ctl -d {self.device} -c tilt_speed=0")
        time.sleep(1)
        
        # Diagonal down-left
        self.run_command(f"v4l2-ctl -d {self.device} -c pan_speed=-{self.pan_speed}")
        self.run_command(f"v4l2-ctl -d {self.device} -c tilt_speed=-{self.tilt_speed}")
        time.sleep(2)
        self.run_command(f"v4l2-ctl -d {self.device} -c pan_speed=0")
        self.run_command(f"v4l2-ctl -d {self.device} -c tilt_speed=0")
        time.sleep(1)
        
        # Diagonal up-left
        self.run_command(f"v4l2-ctl -d {self.device} -c pan_speed=-{self.pan_speed}")
        self.run_command(f"v4l2-ctl -d {self.device} -c tilt_speed={self.tilt_speed}")
        time.sleep(2)
        self.run_command(f"v4l2-ctl -d {self.device} -c pan_speed=0")
        self.run_command(f"v4l2-ctl -d {self.device} -c tilt_speed=0")
        time.sleep(1)
        
        # Diagonal down-right
        self.run_command(f"v4l2-ctl -d {self.device} -c pan_speed={self.pan_speed}")
        self.run_command(f"v4l2-ctl -d {self.device} -c tilt_speed=-{self.tilt_speed}")
        time.sleep(2)
        self.run_command(f"v4l2-ctl -d {self.device} -c pan_speed=0")
        self.run_command(f"v4l2-ctl -d {self.device} -c tilt_speed=0")
        
        print("Demo sequence completed.")
        
        # Reset camera position
        self.reset_position()
        
        return True


def main():
    """Main function to parse arguments and execute commands"""
    parser = argparse.ArgumentParser(description='Control Logitech BCC950 Camera')
    
    parser.add_argument('--setup', action='store_true', help='Install prerequisites and detect camera')
    parser.add_argument('-d', '--device', help='Specify camera device')
    parser.add_argument('-l', '--list', action='store_true', help='List available camera devices')
    parser.add_argument('--pan-left', action='store_true', help='Pan camera left')
    parser.add_argument('--pan-right', action='store_true', help='Pan camera right')
    parser.add_argument('--tilt-up', action='store_true', help='Tilt camera up')
    parser.add_argument('--tilt-down', action='store_true', help='Tilt camera down')
    parser.add_argument('--zoom-in', action='store_true', help='Zoom camera in')
    parser.add_argument('--zoom-out', action='store_true', help='Zoom camera out')
    parser.add_argument('--reset', action='store_true', help='Reset camera to default position')
    parser.add_argument('--demo', action='store_true', help='Run a demonstration sequence of camera movements')
    parser.add_argument('--info', action='store_true', help='Show camera information and controls')
    
    args = parser.parse_args()
    
    # Create controller
    controller = BCC950Controller(args.device)
    
    # Process commands
    if args.setup:
        controller.setup()
    elif args.list:
        controller.list_devices()
    elif args.pan_left:
        controller.pan_left()
    elif args.pan_right:
        controller.pan_right()
    elif args.tilt_up:
        controller.tilt_up()
    elif args.tilt_down:
        controller.tilt_down()
    elif args.zoom_in:
        controller.zoom_in()
    elif args.zoom_out:
        controller.zoom_out()
    elif args.reset:
        controller.reset_position()
    elif args.demo:
        controller.run_demo()
    elif args.info:
        controller.show_info()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
