import asyncio
import json
import os
from typing import Optional
from contextlib import AsyncExitStack
import uuid
from mcp import ClientSession
from mcp.client.sse import sse_client
from openai import OpenAI
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()  # load environment variables from .env
API_KEY = os.getenv("APIKEY")
class MCPClient:
    def __init__(self):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.client = OpenAI(api_key=API_KEY)

    async def connect_to_sse_server(self, server_url: str):
        """Connect to an MCP server running with SSE transport"""
        # Store the context managers so they stay alive
        self._streams_context = sse_client(url=server_url)
        streams = await self._streams_context.__aenter__()

        self._session_context = ClientSession(*streams)
        self.session: ClientSession = await self._session_context.__aenter__()

        # Initialize
        await self.session.initialize()

        # List available tools to verify connection
        print("Initialized SSE client...")
        print("Listing tools...")
        response = await self.session.list_tools()
        tools = response.tools
        print("\nConnected to server with tools:", [tool.name for tool in tools])

    async def cleanup(self):
        """Properly clean up the session and streams"""
        if self._session_context:
            await self._session_context.__aexit__(None, None, None)
        if self._streams_context:
            await self._streams_context.__aexit__(None, None, None)

    async def process_query(self, query: str) -> str:
        """Process a query using OpenAI and available tools"""
        messages = [
            {
                "role": "user",
                "content": query
            }
        ]

        response = await self.session.list_tools()
        print("INPUT: ",response.tools[0].inputSchema)    
        for tool in response.tools:
            tool.inputSchema['additionalProperties'] = False      

        tools = [{
            "type": "function",      
            "id": str(uuid.uuid4()),                
            "function": {                            
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.inputSchema,                
                "strict": True
            }
        } for tool in response.tools]
        
        response = self.client.chat.completions.create(
            model='gpt-4o-mini',
            max_tokens=500,
            messages=messages,
            tools=tools
        )
        print("First response")
        print(response)        
        
        # Process response and handle tool calls
        tool_results = []
        final_text = []
        choice = response.choices[0]
        tool_calls = choice.message.tool_calls
        if tool_calls:            
            for tool_call in tool_calls:
                tool_name = tool_call.function.name
                tool_args = tool_call.function.arguments
                print("Running function: ",tool_name)
                print("Arguments: ",tool_args)            

                result = await self.session.call_tool(tool_name,json.loads(tool_args))
                tool_results.append({"call": tool_name, "result": result})
                final_text.append(f"[Calling tool {tool_name} with args {tool_args}]")
                print("Result: ",result)
                # Continue conversation with tool results             
                tool_call_message = {
                    "id": tool_call.id,
                    "type": "function",                  
                    "function": {
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments
                    }
                }
                tool_results.append(tool_call_message)
                messages.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [tool_call_message]
                })         
                messages.append({
                    "role": "tool", 
                    "tool_call_id":tool_call.id,
                    "content": result.content
                })
            response = self.client.chat.completions.create(
                model = 'gpt-4o-mini',
                messages = messages,
                max_tokens= 1000
            )
            print("Second Response")
            print(response)
            messages.append({
                "role":"assistant",
                "content": response.choices[0].message.content
            })
            final_text.append(response.choices[0].message.content)

            return "\n".join(final_text)
        else:
            content = choice.message.content
            messages.append({
                "role": "assistant",
                "content": content
            })
            return content
        
    

    async def chat_loop(self):
        """Run an interactive chat loop"""
        print("\nMCP Client Started!")
        print("Type your queries or 'quit' to exit.")
        
        while True:
            try:
                query = input("\nQuery: ").strip()
                
                if query.lower() == 'quit':
                    break
                    
                response = await self.process_query(query)
                print("\n" + response)
                    
            except Exception as e:
                print(f"\nError: {str(e)}")


async def main():
    if len(sys.argv) < 2:
        print("Usage: uv run client.py <URL of SSE MCP server (i.e. http://localhost:8080/sse)>")
        sys.exit(1)

    client = MCPClient()
    try:
        await client.connect_to_sse_server(server_url=sys.argv[1])
        await client.chat_loop()
    finally:
        await client.cleanup()


if __name__ == "__main__":
    import sys
    asyncio.run(main())