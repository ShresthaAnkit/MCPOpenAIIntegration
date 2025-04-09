import asyncio
from dotenv import load_dotenv
from typing import Optional
from contextlib import AsyncExitStack
from mcp.client.stdio import stdio_client
from mcp import ClientSession, StdioServerParameters

load_dotenv()   

class MCPClient:
    def __init__(self):
        self.session:Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()

    async def connect_to_server(self, server_script_path: str):
        """ Connect to MCP server """
        is_python = server_script_path.endswith('.py')
        is_js = server_script_path.endswith('.js')

        if not (is_python or is_js):
            raise ValueError("Server script must be a .py or .js file")
        
        command = "python" if is_python else "node"

        server_params = StdioServerParameters(
            command = command,
            args = [server_script_path],
            env = None
        )

        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport

        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio,self.write))
        await self.session.initialize()

        # List available tools
        response = await self.session.list_tools()
        tools = response.tools
        print("\nConnected to server with tools: ",[tool.name for tool in tools])
        return tools

    async def call_add_tool(self,a: int, b: int):
        """Call the add tool on the server"""
        if not self.session:
            raise RuntimeError("Not connected to server")
        
        result = await self.session.call_tool(
            name="add",
            arguments={'a':a, 'b':b}
        )
        return result.content[0].text
    
    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()

async def main():
    client = MCPClient()
    try:
        await client.connect_to_server("D:/AmnilTech/mcp/mcp-server/src/mcp_server/server.py")
        result = await client.call_add_tool(4,5)
        print(f"Result: {result}")
    finally:
        await client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())