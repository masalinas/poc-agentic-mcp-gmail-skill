import asyncio
import json
import re
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_ollama import ChatOllama
from langchain_mcp_adapters.tools import load_mcp_tools
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Configuración del servidor MCP local
server_params = StdioServerParameters(
    command="python",
    args=["gws_mcp_server.py"]
)

async def run_agent():
    print("[Cliente] Conectando al Servidor MCP para extraer herramientas y Skills...")

    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            
            await session.initialize()
            print("[Cliente] Conexión MCP Establecida.")

            # 1. Cargamos las herramientas desde el servidor MCP
            mcp_tools = await load_mcp_tools(session)

            # Creamos un mapa indexado por nombre para llamarlas fácilmente
            tools_map = {tool.name: tool for tool in mcp_tools}
            print(f"[Cliente] Herramientas cargadas: {list(tools_map.keys())}")

            # 2. Obtenemos las instrucciones de tu SKILL.md desde el servidor
            mcp_prompt_response = await session.get_prompt("gws_gmail_instructions")
            skill_instructions = mcp_prompt_response.messages[0].content.text
            print("[Cliente] Contexto de la Skill recuperado con éxito.")

            # 3. Inicializamos el modelo (Qwen 2.5)
            llm = ChatOllama(model="qwen2.5:7b", temperature=0)

            # 4. Definimos el System Prompt inyectando tus reglas de negocio y el formato manual
            system_prompt = f"""Eres un asistente operativo local. Ejecutas comandos de Gmail usando 'execute_gws_command'.

INSTRUCCIONES CRÍTICAS DE LA SKILL OPERATIVA (SÍGUELAS A RAJATABLA):
{skill_instructions}

Formato obligatorio de respuesta:
Si necesitas usar una herramienta, debes responder EXACTAMENTE con este formato JSON y NADA MÁS:
{{"action": "execute_gws_command", "args": ["gmail", "+subcomando"]}}

Si ya tienes la respuesta final para el usuario tras ver el resultado, responde con texto normal.
"""

            # Historial de la conversación para el bucle
            user_input = "Muéstrame los últimos 3 correos electrónicos de mi bandeja."
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_input)
            ]

            print("\n> Lanzando consulta al agente asíncrono...")
            
            # 5. Bucle de ejecución Asíncrono Real (Control de Pensamiento y Acción)
            for iteration in range(5):
                # El modelo genera su pensamiento/acción
                response = await llm.ainvoke(messages)
                content = response.content.strip()
                messages.append(response)

                # ¿El modelo ha decidido llamar a la herramienta usando nuestro JSON estructurado?
                if '"action"' in content or 'action' in content:
                    try:
                        # Extraemos el JSON del texto de Qwen por seguridad si mete texto extra
                        json_match = re.search(r'\{.*\}', content, re.DOTALL)
                        tool_call = json.loads(json_match.group(0)) if json_match else json.loads(content)
                        
                        tool_name = tool_call["action"]
                        tool_args = tool_call["args"]

                        print(f"\n[Agente] Solicitando herramienta: {tool_name} con args: {tool_args}")

                        if tool_name in tools_map:
                            # ¡AQUÍ ESTÁ LA CLAVE! Invocación asíncrona real con .ainvoke()
                            # Empaquetamos en el diccionario 'args' que espera el esquema del servidor
                            observation = await tools_map[tool_name].ainvoke({"args": tool_args})
                            print(f"[Sistema] Resultado obtenido del Servidor MCP.")
                            
                            # Añadimos el resultado al contexto para la siguiente iteración
                            messages.append(HumanMessage(content=f"Observation: {observation}"))
                        else:
                            messages.append(HumanMessage(content=f"Error: La herramienta {tool_name} no existe."))
                    
                    except Exception as e:
                        messages.append(HumanMessage(content=f"Error parseando la acción JSON: {str(e)}. Por favor, inténtalo de nuevo con el formato correcto."))
                else:
                    # Si no llamó a ninguna herramienta, es la respuesta final en lenguaje natural
                    print("\n[Respuesta Final del Agente]:")
                    print(content)
                    break
            else:
                print("\n[Cliente] Se ha alcanzado el límite máximo de iteraciones.")

if __name__ == "__main__":
    asyncio.run(run_agent())