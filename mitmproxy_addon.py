"""
Mobile Privacy Leakage Detector - mitmproxy Addon Script

This script intercepts network traffic from a mobile device and analyzes it for privacy leaks.
It then sends the analyzed data to the backend WebSocket endpoint for real-time dashboard updates.

Usage:
1. Connect mobile device via USB and enable ADB
2. Configure device to use proxy (usually 8080)
3. Run: mitmproxy -s mitmproxy_addon.py --set confdir=~/.mitmproxy
4. Access web dashboard to view real-time traffic analysis

The script detects various privacy leak patterns including:
- GPS/Location data transmission
- Device identifiers (IMEI, Android ID, etc.)
- Personal information (contacts, email, phone)
- Third-party tracking (analytics, ads)
"""

import json
import asyncio
import websockets
import logging
from datetime import datetime, timezone
from typing import Optional, Tuple
import re
from urllib.parse import urlparse, parse_qs
from mitmproxy import http, ctx
import threading
import time

# Configuration
BACKEND_WS_URL = "ws://localhost:8001/ws/traffic"  # Backend WebSocket endpoint
RECONNECT_DELAY = 5  # Seconds to wait before reconnecting

class PrivacyLeakDetector:
    """Privacy leak detection logic"""
    
    @staticmethod
    def detect_leak(flow: http.HTTPFlow) -> Tuple[Optional[str], Optional[str]]:
        """
        Analyze HTTP flow for privacy leaks
        Returns (leak_type, leak_detail) or (None, None)
        """
        
        request = flow.request
        url = request.pretty_url.lower()
        host = request.pretty_host.lower()
        path = request.path.lower()
        method = request.method
        
        # GPS/Location data detection
        location_patterns = [
            'location', 'gps', 'latitude', 'longitude', 'coordinates',
            'geolocation', 'position', 'geocode', 'maps', 'directions'
        ]
        if any(pattern in url or pattern in path for pattern in location_patterns):
            return "GPS_DATA", f"Location data detected in {method} request to {host}"
        
        # Device information detection
        device_patterns = [
            'device_id', 'imei', 'udid', 'android_id', 'ios_id', 
            'device_info', 'hardware_id', 'serial', 'mac_address'
        ]
        if any(pattern in url or pattern in path for pattern in device_patterns):
            return "DEVICE_INFO", f"Device identifier detected in request to {host}"
        
        # Personal data detection
        personal_patterns = [
            'email', 'phone', 'contact', 'profile', 'personal',
            'address', 'name', 'birthday', 'social_security'
        ]
        if any(pattern in url or pattern in path for pattern in personal_patterns):
            return "PERSONAL_DATA", f"Personal information detected in request to {host}"
        
        # Third-party tracking detection
        tracking_hosts = [
            'google-analytics', 'googletagmanager', 'doubleclick',
            'facebook.com', 'connect.facebook', 'adsystem',
            'googlesyndication', 'amazon-adsystem', 'scorecardresearch',
            'quantserve', 'outbrain', 'taboola'
        ]
        if any(tracker in host for tracker in tracking_hosts):
            return "TRACKING", f"Third-party tracking detected: {host}"
        
        # Analyze request/response content for sensitive data patterns
        content_leak = PrivacyLeakDetector._analyze_content(flow)
        if content_leak:
            return content_leak
        
        return None, None
    
    @staticmethod
    def _analyze_content(flow: http.HTTPFlow) -> Optional[Tuple[str, str]]:
        """Analyze request/response content for sensitive patterns"""
        
        # Check request content
        if flow.request.content:
            try:
                content = flow.request.content.decode('utf-8', errors='ignore').lower()
                
                # Look for email patterns
                if re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', content):
                    return "PERSONAL_DATA", f"Email address detected in request content to {flow.request.pretty_host}"
                
                # Look for phone patterns
                if re.search(r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', content):
                    return "PERSONAL_DATA", f"Phone number detected in request content to {flow.request.pretty_host}"
                
                # Look for location coordinates
                if re.search(r'[-+]?([1-8]?\d(\.\d+)?|90(\.0+)?),\s*[-+]?(180(\.0+)?|((1[0-7]\d)|([1-9]?\d))(\.\d+)?)', content):
                    return "GPS_DATA", f"GPS coordinates detected in request content to {flow.request.pretty_host}"
                
            except Exception:
                pass  # Ignore decoding errors
        
        return None

class WebSocketClient:
    """WebSocket client to send data to backend"""
    
    def __init__(self, backend_url: str):
        self.backend_url = backend_url
        self.websocket = None
        self.running = False
        self.connection_thread = None
        self.send_queue = []
        
    def start(self):
        """Start WebSocket connection in background thread"""
        self.running = True
        self.connection_thread = threading.Thread(target=self._connection_loop, daemon=True)
        self.connection_thread.start()
        ctx.log.info("WebSocket client started")
    
    def stop(self):
        """Stop WebSocket connection"""
        self.running = False
        if self.connection_thread:
            self.connection_thread.join(timeout=5)
        ctx.log.info("WebSocket client stopped")
    
    def send_traffic_data(self, flow_data: dict):
        """Queue traffic data to be sent to backend"""
        self.send_queue.append(flow_data)
    
    def _connection_loop(self):
        """Main connection loop (runs in background thread)"""
        while self.running:
            try:
                asyncio.run(self._connect_and_send())
            except Exception as e:
                ctx.log.error(f"WebSocket connection error: {e}")
                if self.running:
                    time.sleep(RECONNECT_DELAY)
    
    async def _connect_and_send(self):
        """Connect to backend and send queued data"""
        try:
            async with websockets.connect(self.backend_url) as websocket:
                self.websocket = websocket
                ctx.log.info(f"Connected to backend at {self.backend_url}")
                
                while self.running:
                    # Send any queued data
                    while self.send_queue:
                        flow_data = self.send_queue.pop(0)
                        try:
                            await websocket.send(json.dumps(flow_data))
                            ctx.log.info(f"Sent traffic data: {flow_data.get('method')} {flow_data.get('host')}{flow_data.get('path')}")
                        except Exception as e:
                            ctx.log.error(f"Error sending data: {e}")
                            # Re-queue the data
                            self.send_queue.insert(0, flow_data)
                            raise
                    
                    await asyncio.sleep(0.1)  # Small delay to prevent busy loop
                    
        except websockets.exceptions.ConnectionClosedError:
            ctx.log.warning("WebSocket connection closed")
            raise
        except Exception as e:
            ctx.log.error(f"WebSocket error: {e}")
            raise

# Global WebSocket client instance
ws_client = WebSocketClient(BACKEND_WS_URL)

class MobilePrivacyAddon:
    """mitmproxy addon for mobile privacy leak detection"""
    
    def __init__(self):
        self.detector = PrivacyLeakDetector()
    
    def load(self, loader):
        """Called when addon is loaded"""
        ctx.log.info("Mobile Privacy Leakage Detector addon loaded")
        ws_client.start()
    
    def running(self):
        """Called when mitmproxy is fully started"""
        ctx.log.info("mitmproxy started - Ready to intercept mobile traffic")
        ctx.log.info(f"Backend WebSocket URL: {BACKEND_WS_URL}")
    
    def done(self):
        """Called when mitmproxy is shutting down"""
        ctx.log.info("Shutting down Mobile Privacy Detector")
        ws_client.stop()
    
    def request(self, flow: http.HTTPFlow):
        """Called when a request is received"""
        # Log the request
        ctx.log.info(f"Intercepted: {flow.request.method} {flow.request.pretty_host}{flow.request.path}")
    
    def response(self, flow: http.HTTPFlow):
        """Called when a response is received - main analysis happens here"""
        
        try:
            # Perform privacy leak detection
            leak_type, leak_detail = self.detector.detect_leak(flow)
            
            # Create flow data structure
            flow_data = {
                "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S"),
                "flowId": f"flow_{int(time.time() * 1000000)}_{hash(flow.request.pretty_url) % 10000}",
                "type": "HTTPS" if flow.request.scheme == "https" else "HTTP",
                "method": flow.request.method,
                "host": flow.request.pretty_host,
                "url": flow.request.path,
                "status": str(flow.response.status_code) if flow.response else "0",
                "leakType": leak_type,
                "leakDetail": leak_detail
            }
            
            # Send to backend via WebSocket
            ws_client.send_traffic_data(flow_data)
            
            # Log privacy leaks
            if leak_type:
                ctx.log.warn(f"PRIVACY LEAK: {leak_type} - {leak_detail}")
            
        except Exception as e:
            ctx.log.error(f"Error processing flow: {e}")

# Create addon instance
addons = [MobilePrivacyAddon()]