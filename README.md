# MCP Complete Architecture with OpenAI Integration
This repository consists of both server and client for a MCP interaction with integration of OpenAI for LLM.

## Code Generation:
The boiler plate was generated with the following commands:
- mcp-server: `uvx create-mcp-server`
- mcp-client: `uv init {name}`

## How to setup:
- Clone this repository
- In `mcp-client`, create .env file and add OpenAI API key as `APIKEY={API_KEY}`

## How to run:
- Navigate to `mcp-client`
- Run `uv run client_sse.py http://localhost:8080/sse`