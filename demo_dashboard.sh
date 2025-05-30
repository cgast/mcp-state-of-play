#!/bin/bash

echo "🎮 MCP State of Play - Dashboard Demo"
echo "===================================="
echo

echo "📋 Container Status:"
docker compose ps
echo

echo "🌐 Dashboard Features:"
echo "✅ Homepage with introduction and project overview"
echo "✅ Auto-registered MCP game servers"
echo "✅ Real-time server monitoring"
echo "✅ Detailed about page with full project documentation"
echo

echo "🔗 Available URLs:"
echo "- 🏠 Dashboard Homepage: http://localhost:8000"
echo "- 📖 About Page: http://localhost:8000/about"
echo "- 🎯 Server 1 (Laboratory): http://localhost:8000/server/server1"
echo "- 🎯 Server 2 (Simple Adventure): http://localhost:8000/server/server2"
echo "- 🔧 API Endpoints: http://localhost:8000/api/servers"
echo

echo "🎲 Registered Game Servers:"
curl -s http://localhost:8000/api/servers | python3 -c "
import sys, json
data = json.load(sys.stdin)
for server in data['servers']:
    print(f\"  - {server['name']} (ID: {server['id']}) - Status: {server['status']}\")
print(f\"\\nTotal: {data['count']} servers registered\")
"

echo
echo "🚀 Ready for AI clients to connect!"
echo "Each MCP server provides full game interaction tools:"
echo "  • move_player(direction)"
echo "  • look_around()"  
echo "  • take_item(item_name)"
echo "  • use_item(item_name, target)"
echo "  • talk_to_npc(npc_name, message)"
echo "  • check_inventory()"
echo "  • get_game_status()"
echo
echo "💡 Try connecting Claude or another MCP client to:"
echo "  • Laboratory Adventure: http://localhost:8001/mcp"
echo "  • Simple Adventure: http://localhost:8002/mcp"