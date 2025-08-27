from fastapi import FastAPI, WebSocket, WebSocketDisconnect, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from pathlib import Path
from pydantic import BaseModel
from typing import List, Optional, Dict, Set
import json
import asyncio
import uuid
from datetime import datetime, timezone
import os
import logging

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Create the main app
app = FastAPI(title="Mobile Privacy Leakage Detector - Backend Bridge")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# In-memory storage for real-time data (last 1000 flows)
traffic_flows: List[Dict] = []
MAX_FLOWS = 1000

# Data Models for traffic flow
class TrafficFlow(BaseModel):
    timestamp: str
    flowId: str
    type: str  # "HTTP" or "HTTPS"
    method: str  # "GET", "POST", etc.
    host: str
    url: str
    status: str
    leakType: Optional[str] = None  # Set by mitmproxy script
    leakDetail: Optional[str] = None  # Set by mitmproxy script

class DashboardStats(BaseModel):
    totalFlows: int
    totalLeaks: int
    recentFlows: List[TrafficFlow]
    privacyLeaks: List[TrafficFlow]

# WebSocket Connection Manager for Dashboard Clients
class ConnectionManager:
    def __init__(self):
        self.dashboard_connections: Set[WebSocket] = set()
    
    async def connect_dashboard(self, websocket: WebSocket):
        await websocket.accept()
        self.dashboard_connections.add(websocket)
        logging.info(f"Dashboard client connected. Total connections: {len(self.dashboard_connections)}")
        
        # Send current stats to newly connected client
        await self.send_current_stats(websocket)
    
    def disconnect_dashboard(self, websocket: WebSocket):
        self.dashboard_connections.discard(websocket)
        logging.info(f"Dashboard client disconnected. Total connections: {len(self.dashboard_connections)}")
    
    async def send_current_stats(self, websocket: WebSocket):
        """Send current statistics to a specific WebSocket"""
        try:
            stats = self._generate_current_stats()
            await websocket.send_text(json.dumps({
                "type": "stats_update",
                "data": stats.dict()
            }))
        except Exception as e:
            logging.error(f"Error sending current stats: {e}")
    
    async def broadcast_to_dashboards(self, data: dict):
        """Broadcast data to all connected dashboard clients"""
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
    
    async def broadcast_new_traffic(self, flow_data: dict):
        """Broadcast new traffic flow to all dashboard clients"""
        await self.broadcast_to_dashboards({
            "type": "new_traffic", 
            "data": flow_data
        })
    
    async def broadcast_stats_update(self):
        """Broadcast updated statistics to all dashboard clients"""
        stats = self._generate_current_stats()
        await self.broadcast_to_dashboards({
            "type": "stats_update",
            "data": stats.dict()
        })
    
    def _generate_current_stats(self) -> DashboardStats:
        """Generate current dashboard statistics"""
        total_flows = len(traffic_flows)
        privacy_leaks = [f for f in traffic_flows if f.get("leakType")]
        total_leaks = len(privacy_leaks)
        
        return DashboardStats(
            totalFlows=total_flows,
            totalLeaks=total_leaks,
            recentFlows=[TrafficFlow(**f) for f in traffic_flows[-10:]][::-1],  # Last 10, most recent first
            privacyLeaks=[TrafficFlow(**f) for f in privacy_leaks[-50:]][::-1]  # Last 50 leaks, most recent first
        )

manager = ConnectionManager()

# WebSocket Endpoints

@app.websocket("/ws/dashboard")
async def websocket_dashboard_endpoint(websocket: WebSocket):
    """WebSocket endpoint for dashboard clients to receive real-time updates"""
    await manager.connect_dashboard(websocket)
    try:
        # Keep connection alive and handle any messages from dashboard
        while True:
            # Dashboard doesn't need to send data, just receive
            # But we need to keep the connection alive
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        manager.disconnect_dashboard(websocket)

@app.websocket("/ws/traffic")
async def websocket_traffic_endpoint(websocket: WebSocket):
    """WebSocket endpoint for mitmproxy script to send traffic data"""
    await websocket.accept()
    logging.info("mitmproxy script connected to traffic endpoint")
    
    try:
        while True:
            # Receive traffic data from mitmproxy script
            data = await websocket.receive_text()
            try:
                flow_data = json.loads(data)
                logging.info(f"Received traffic data from mitmproxy: {flow_data.get('method')} {flow_data.get('host')}{flow_data.get('url')}")
                
                # Validate required fields
                required_fields = ['timestamp', 'type', 'method', 'host', 'url', 'status']
                if not all(field in flow_data for field in required_fields):
                    logging.error(f"Missing required fields in traffic data: {flow_data}")
                    continue
                
                # Ensure flowId exists
                if "flowId" not in flow_data:
                    flow_data["flowId"] = str(uuid.uuid4())
                
                # Store traffic flow (maintain max size)
                traffic_flows.append(flow_data)
                if len(traffic_flows) > MAX_FLOWS:
                    traffic_flows.pop(0)
                
                # Broadcast new traffic to all dashboard clients
                await manager.broadcast_new_traffic(flow_data)
                
                # Log privacy leak if detected
                if flow_data.get("leakType"):
                    logging.warning(f"PRIVACY LEAK DETECTED: {flow_data['leakType']} - {flow_data.get('leakDetail', 'No details')}")
                
            except json.JSONDecodeError as e:
                logging.error(f"Invalid JSON received from mitmproxy script: {e}")
            except Exception as e:
                logging.error(f"Error processing traffic data: {e}")
                
    except WebSocketDisconnect:
        logging.info("mitmproxy script disconnected from traffic endpoint")

# REST API Endpoints (for debugging and manual access)

@api_router.get("/dashboard/stats")
async def get_dashboard_stats():
    """Get current dashboard statistics"""
    return manager._generate_current_stats()

@api_router.get("/dashboard/flows")
async def get_all_flows():
    """Get all traffic flows"""
    return [TrafficFlow(**f) for f in traffic_flows]

@api_router.get("/dashboard/leaks")
async def get_privacy_leaks():
    """Get all privacy leaks"""
    return [TrafficFlow(**f) for f in traffic_flows if f.get("leakType")]

@api_router.get("/system/status")
async def get_system_status():
    """Get system status"""
    return {
        "status": "running",
        "dashboard_connections": len(manager.dashboard_connections),
        "total_flows_stored": len(traffic_flows),
        "total_leaks_detected": len([f for f in traffic_flows if f.get("leakType")]),
        "max_flows_capacity": MAX_FLOWS,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@api_router.post("/system/clear")
async def clear_traffic_data():
    """Clear all stored traffic data (for testing purposes)"""
    global traffic_flows
    traffic_flows = []
    
    # Broadcast updated stats to all clients
    await manager.broadcast_stats_update()
    
    return {"message": "All traffic data cleared", "flows_remaining": len(traffic_flows)}

# Include the router in the main app
app.include_router(api_router)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],  # Allow all origins for WebSocket connections
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
    return {
        "message": "Mobile Privacy Leakage Detector - Backend Bridge",
        "description": "Receives traffic data from mitmproxy and broadcasts to dashboard clients",
        "endpoints": {
            "dashboard_websocket": "/ws/dashboard",
            "traffic_websocket": "/ws/traffic",
            "api_stats": "/api/dashboard/stats",
            "system_status": "/api/system/status"
        }
    }