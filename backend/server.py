from fastapi import FastAPI, WebSocket, WebSocketDisconnect, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Set
import json
import asyncio
import uuid
from datetime import datetime, timezone
import random
import os
import logging

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Create the main app
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# In-memory storage for traffic data
traffic_flows: List[Dict] = []
active_dashboard_connections: Set[WebSocket] = set()

# Data Models
class TrafficFlow(BaseModel):
    timestamp: str
    flowId: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: str  # "HTTP" or "HTTPS"
    method: str  # "GET", "POST", etc.
    host: str
    url: str
    status: str
    leakType: Optional[str] = None  # "GPS_DATA", "DEVICE_INFO", "PERSONAL_DATA", etc.
    leakDetail: Optional[str] = None

class DashboardStats(BaseModel):
    totalFlows: int
    totalLeaks: int
    recentFlows: List[TrafficFlow]
    privacyLeaks: List[TrafficFlow]

# Mock Privacy Leak Detection Logic
def detect_privacy_leak(flow_data: Dict) -> tuple[Optional[str], Optional[str]]:
    """Mock privacy leak detection - returns (leak_type, leak_detail) or (None, None)"""
    
    # Mock detection patterns based on URL patterns and hosts
    url = flow_data.get("url", "").lower()
    host = flow_data.get("host", "").lower()
    method = flow_data.get("method", "")
    
    # GPS/Location data patterns
    if any(keyword in url for keyword in ["location", "gps", "coordinates", "latitude", "longitude", "geolocation"]):
        return "GPS_DATA", f"Detected GPS/location data transmission to {host}"
    
    # Device information patterns
    if any(keyword in url for keyword in ["device", "imei", "udid", "android_id", "ios_id", "device_info"]):
        return "DEVICE_INFO", f"Device identifier transmitted to {host}"
    
    # Personal data patterns
    if any(keyword in url for keyword in ["email", "phone", "contact", "profile", "personal"]):
        return "PERSONAL_DATA", f"Personal information detected in request to {host}"
    
    # Social media tracking
    if any(domain in host for domain in ["facebook", "google-analytics", "doubleclick", "adsystem"]):
        return "TRACKING", f"Third-party tracking detected: {host}"
    
    # Random leak detection for demo (10% chance)
    if random.random() < 0.1:
        leak_types = ["GPS_DATA", "DEVICE_INFO", "PERSONAL_DATA", "TRACKING"]
        leak_type = random.choice(leak_types)
        return leak_type, f"Suspicious data pattern detected in {method} request to {host}"
    
    return None, None

# WebSocket Connection Manager
class ConnectionManager:
    def __init__(self):
        self.dashboard_connections: Set[WebSocket] = set()
    
    async def connect_dashboard(self, websocket: WebSocket):
        await websocket.accept()
        self.dashboard_connections.add(websocket)
        logging.info(f"Dashboard client connected. Total connections: {len(self.dashboard_connections)}")
    
    def disconnect_dashboard(self, websocket: WebSocket):
        self.dashboard_connections.discard(websocket)
        logging.info(f"Dashboard client disconnected. Total connections: {len(self.dashboard_connections)}")
    
    async def broadcast_to_dashboards(self, data: dict):
        if self.dashboard_connections:
            message = json.dumps(data)
            disconnected = []
            for connection in self.dashboard_connections:
                try:
                    await connection.send_text(message)
                except:
                    disconnected.append(connection)
            
            # Remove disconnected clients
            for conn in disconnected:
                self.dashboard_connections.discard(conn)

manager = ConnectionManager()

# WebSocket Endpoints
@app.websocket("/ws/dashboard")
async def websocket_dashboard_endpoint(websocket: WebSocket):
    await manager.connect_dashboard(websocket)
    try:
        while True:
            # Send current stats periodically
            stats = DashboardStats(
                totalFlows=len(traffic_flows),
                totalLeaks=len([f for f in traffic_flows if f.get("leakType")]),
                recentFlows=[TrafficFlow(**f) for f in traffic_flows[-10:]],
                privacyLeaks=[TrafficFlow(**f) for f in traffic_flows if f.get("leakType")]
            )
            await websocket.send_text(json.dumps({
                "type": "stats_update",
                "data": stats.dict()
            }))
            await asyncio.sleep(5)  # Send updates every 5 seconds
    except WebSocketDisconnect:
        manager.disconnect_dashboard(websocket)

@app.websocket("/ws/traffic")
async def websocket_traffic_endpoint(websocket: WebSocket):
    await websocket.accept()
    logging.info("Traffic source connected")
    
    try:
        while True:
            data = await websocket.receive_text()
            try:
                flow_data = json.loads(data)
                
                # Apply privacy leak detection
                leak_type, leak_detail = detect_privacy_leak(flow_data)
                if leak_type:
                    flow_data["leakType"] = leak_type
                    flow_data["leakDetail"] = leak_detail
                
                # Ensure flowId exists
                if "flowId" not in flow_data:
                    flow_data["flowId"] = str(uuid.uuid4())
                
                # Store in memory (keep last 1000 flows)
                traffic_flows.append(flow_data)
                if len(traffic_flows) > 1000:
                    traffic_flows.pop(0)
                
                # Broadcast to all dashboard clients
                await manager.broadcast_to_dashboards({
                    "type": "new_traffic",
                    "data": flow_data
                })
                
                logging.info(f"Processed traffic flow: {flow_data.get('method')} {flow_data.get('host')}{flow_data.get('url')}")
                
            except json.JSONDecodeError as e:
                logging.error(f"Invalid JSON received: {e}")
                
    except WebSocketDisconnect:
        logging.info("Traffic source disconnected")

# API Routes for dashboard data
@api_router.get("/dashboard/stats")
async def get_dashboard_stats():
    return DashboardStats(
        totalFlows=len(traffic_flows),
        totalLeaks=len([f for f in traffic_flows if f.get("leakType")]),
        recentFlows=[TrafficFlow(**f) for f in traffic_flows[-10:]],
        privacyLeaks=[TrafficFlow(**f) for f in traffic_flows if f.get("leakType")]
    )

@api_router.get("/dashboard/flows")
async def get_all_flows():
    return [TrafficFlow(**f) for f in traffic_flows]

@api_router.get("/dashboard/leaks")
async def get_privacy_leaks():
    return [TrafficFlow(**f) for f in traffic_flows if f.get("leakType")]

# Mock data generator for testing
@api_router.post("/test/generate-mock-data")
async def generate_mock_data():
    """Generate mock traffic data for testing the dashboard"""
    
    mock_hosts = [
        "api.facebook.com", "google-analytics.com", "doubleclick.net",
        "api.twitter.com", "graph.instagram.com", "api.snapchat.com",
        "cdn.example.com", "api.weather.com", "maps.googleapis.com"
    ]
    
    mock_paths = [
        "/api/user/profile", "/track/event", "/location/update",
        "/device/register", "/ads/tracking", "/analytics/pageview",
        "/api/contacts/sync", "/user/preferences", "/data/export"
    ]
    
    methods = ["GET", "POST", "PUT"]
    statuses = ["200", "201", "301", "400", "500"]
    
    # Generate 5 mock traffic flows
    for i in range(5):
        flow_data = {
            "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S"),
            "flowId": str(uuid.uuid4()),
            "type": random.choice(["HTTP", "HTTPS"]),
            "method": random.choice(methods),
            "host": random.choice(mock_hosts),
            "url": random.choice(mock_paths),
            "status": random.choice(statuses)
        }
        
        # Apply privacy leak detection
        leak_type, leak_detail = detect_privacy_leak(flow_data)
        if leak_type:
            flow_data["leakType"] = leak_type
            flow_data["leakDetail"] = leak_detail
        
        # Store in memory
        traffic_flows.append(flow_data)
        if len(traffic_flows) > 1000:
            traffic_flows.pop(0)
        
        # Broadcast to dashboards
        await manager.broadcast_to_dashboards({
            "type": "new_traffic",
            "data": flow_data
        })
    
    return {"message": f"Generated 5 mock traffic flows"}

# Include the router in the main app
app.include_router(api_router)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],  # For WebSocket connections
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.get("/")
async def root():
    return {"message": "Mobile Privacy Leakage Detector API"}