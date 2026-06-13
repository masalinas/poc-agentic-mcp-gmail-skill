pip install langchain langchain-core langchain-ollama pyyaml
pip install mcp langchain-mcp-adapters


## Execution with MCP
```bash
python main-mcp.py 
[Cliente] Conectando al Servidor MCP para extraer herramientas y Skills...
[Cliente] Conexión MCP Establecida.
Processing request of type ListToolsRequest
[Cliente] Herramientas cargadas: ['execute_gws_command']
Processing request of type GetPromptRequest
[Cliente] Contexto de la Skill recuperado con éxito.

> Lanzando consulta al agente asíncrono...

[Agente] Solicitando herramienta: execute_gws_command con args: ['gmail', '+triage']
Processing request of type CallToolRequest
[Sistema] Resultado obtenido del Servidor MCP.

[Respuesta Final del Agente]:
Aquí tienes los últimos tres correos electrónicos en tu bandeja de entrada:

1. **Fecha:** Lunes, 4 de mayo de 2026 a las 13:50
   - **De:** Gravatar <no-reply@gravatar.com>
   - **Asunto:** Tu avatar globalmente reconocido

Por favor, indícame si deseas ver más detalles sobre alguno de estos correos.
```

## Secuence Diagram

User            main-mcp.py (Cliente)               gws_mcp_server.py (Servidor)      CLI / Gmail
  |                         |                                     |                         |
  |--- python main-mcp.py ->|                                     |                         |
  |                         |--- 1. Levanta subproceso (stdio) -->|                         |
  |                         |<-- 2. Conexión Establecida ---------|                         |
  |                         |                                     |                         |
  |                         |--- 3. ListToolsRequest ------------>|                         |
  |                         |<-- Retorna ['execute_gws_command'] -|                         |
  |                         |                                     |                         |
  |                         |--- 4. GetPromptRequest ------------>|                         |
  |                         |<-- Retorna texto de SKILL.md -------|                         |
  |                         |                                     |                         |
  |                         |-- [Inyecta Skill en System Prompt]  |                         |
  |                         |                                     |                         |
  |-- "Muéstrame los..." -->|                                     |                         |
  |                         |-- [Qwen evalúa y genera JSON]       |                         |
  |                         |                                     |                         |
  |                         |==== 5. Invocación Asíncrona (await tool.ainvoke()) ===========|
  |                         |                                     |                         |
  |                         |--- CallToolRequest (args) --------->|                         |
  |                         |                                     |--- 6. Ejecuta comando ->|
  |                         |                                     |<-- Retorna Output Correo|
  |                         |<-- CallToolResult (Texto plano) ----|                         |
  |                         |===============================================================|
  |                         |                                     |                         |
  |                         |-- [Qwen lee Output y redacta]       |                         |
  |<-- Muestra resultado ---|                                     |                         |
  |                         |                                     |                         |