#!/usr/bin/env python3
"""
Script to register an MCP server with the dashboard
"""
import os
import time
import json
import requests
import sys

def register_server():
    """Register this MCP server with the dashboard"""
    server_id = os.getenv("SERVER_ID", "server1")
    server_name = os.getenv("SERVER_NAME", f"Game Server {server_id}")
    mcp_port = os.getenv("MCP_PORT", "8001")
    dashboard_url = os.getenv("REGISTRY_URL", "http://dashboard:8000")
    
    # Build server info
    server_info = {
        "id": server_id,
        "name": server_name,
        "url": f"http://mcp-server-{server_id}:{mcp_port}/mcp",
        "game_id": f"game_{server_id}",
        "status": "running"
    }
    
    # Wait for dashboard to be ready
    max_retries = 30
    for attempt in range(max_retries):
        try:
            # Try to register
            response = requests.post(
                f"{dashboard_url}/api/register",
                json=server_info,
                timeout=5
            )
            
            if response.status_code == 200:
                print(f"✅ Successfully registered server {server_id} with dashboard")
                return True
            else:
                print(f"❌ Registration failed: {response.status_code} - {response.text}")
                
        except requests.exceptions.RequestException as e:
            print(f"⏳ Attempt {attempt + 1}/{max_retries}: Dashboard not ready yet ({e})")
            
        if attempt < max_retries - 1:
            time.sleep(2)
    
    print(f"❌ Failed to register server {server_id} after {max_retries} attempts")
    return False

if __name__ == "__main__":
    success = register_server()
    sys.exit(0 if success else 1)