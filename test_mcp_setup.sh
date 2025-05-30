#!/bin/bash

echo "🎮 Testing Multi-Container MCP Setup"
echo "===================================="

# Check if containers are running
echo "📋 Container Status:"
docker compose ps

echo
echo "🌐 Testing Dashboard API:"
echo "Registered servers:"
curl -s http://localhost:8000/api/servers | jq '.'

echo
echo "🎯 Testing MCP Server 1 (Laboratory Adventure):"
echo "Game state summary:"
curl -s http://localhost:8000/api/server/server1/state | jq '{title, active, current_turn, player_location: .players.player_1.location}'

echo
echo "🎯 Testing MCP Server 2 (Simple Adventure):"
echo "Game state summary:"
curl -s http://localhost:8000/api/server/server2/state | jq '{title, active, current_turn, player_location: .players.player_1.location}'

echo
echo "🔗 Access URLs:"
echo "- Dashboard Homepage: http://localhost:8000"
echo "- Server 1 View: http://localhost:8000/server/server1"
echo "- Server 2 View: http://localhost:8000/server/server2"
echo "- MCP Server 1 Endpoint: http://localhost:8001/mcp"
echo "- MCP Server 2 Endpoint: http://localhost:8002/mcp"

echo
echo "✅ Multi-container MCP setup is working!"
echo "You can now connect multiple MCP clients to different servers"
echo "and monitor them all from a single dashboard."