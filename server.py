from mcp.server import MCPServer

from src.tools import register_tools

mcp = MCPServer("my-mcp-project")

register_tools(mcp)

if __name__ == "__main__":
    mcp.run()
