import json
import os
import subprocess
import yaml
from typing import Dict, Any

from langchain_core.tools import tool
from langchain_core.prompts import PromptTemplate
from langchain_classic.agents import AgentExecutor, create_react_agent
from langchain_ollama import ChatOllama

# ==========================================
# 1. HERRAMIENTA
# ==========================================
@tool
def execute_gws_command(tool_input: str) -> str:
    """
    Ejecuta comandos de la CLI gws para Gmail.
    
    SINTAXIS MANDATORIA (Usa SIEMPRE los helpers con el prefijo '+'):
    - Para listar/resumir correos: {"args": ["gmail", "+triage"]}
    - Para leer el contenido de un correo específico por ID: {"args": ["gmail", "+read", "<ID_DEL_MENSAJE>"]}
    
    REGLA CRÍTICA DE PARÁMETROS:
    Cuando uses helpers con el signo '+' (como +triage o +read), NO UTILICES NUNCA la clave 'params'. 
    Deja 'params' vacío o no lo incluyas. Si el usuario te pide un número específico de correos (ej. los últimos 3), 
    ejecuta simplemente {"args": ["gmail", "+triage"]} sin parámetros, lee el resultado completo y filtra tú los 3 primeros con tu propia lógica de IA.
    """

    args = []
    params = None

    clean_input = tool_input.strip()

    try:
        data = json.loads(clean_input)
        if isinstance(data, dict):
            args = data.get("args", [])
            params = data.get("params", None)
        elif isinstance(data, list):
            args = data
        else:
            args = str(clean_input).split()
    except json.JSONDecodeError:
        args = clean_input.split()

    # Limpieza de comillas residuales
    args = [arg.strip('"').strip("'") for arg in args if arg]

    full_command = ["gws"] + args

    # =========================================================================
    # ¡AQUÍ SE AÑADE EL PARCHE DE ES_HELPER!
    # =========================================================================
    # Comprobamos si alguno de los argumentos empieza por '+' (como '+triage' o '+read')
    es_helper = any(arg.startswith("+") for arg in args)

    if params and not es_helper:        
        full_command += ["--params", json.dumps(params)]
    elif params and es_helper:
        print("\n[Sistema] Aviso: Omitiendo --params porque los comandos helper (+) no los admiten.")
    # =========================================================================

    print(f"\n[Sistema] Ejecutando: {' '.join(full_command)}")

    try:
        result = subprocess.run(
            full_command,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout if result.stdout else "Comando ejecutado con éxito (sin salida)."
    except subprocess.CalledProcessError as e:
        return f"Error en la ejecución de gws: {e.stderr}"
    except FileNotFoundError:
        return "Error: La CLI 'gws' no está instalada o no está en el PATH."


# ==========================================
# 2. CARGADOR DE SKILLS
# ==========================================
def load_local_skill(file_path: str) -> Dict[str, Any]:
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"No se encontró la skill en: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        raw_content = f.read()

    if raw_content.startswith("---"):
        _, frontmatter, markdown_instructions = raw_content.split("---", 2)
        metadata = yaml.safe_load(frontmatter)
        instructions = markdown_instructions.strip()
    else:
        metadata = {"name": "generic-skill", "description": ""}
        instructions = raw_content.strip()

    return {"metadata": metadata, "instructions": instructions}


# ==========================================
# 3. ORQUESTACIÓN REACT
# ==========================================
def main():
    skill_info = load_local_skill(".agents/skills/gws-gmail/SKILL.md")

    # HE LIMPIADO ESTE PROMPT PARA BORRAR LOS EJEMPLOS VIEJOS DE 'users messages list'
    template = """Eres un asistente operativo local. Tu trabajo es ejecutar comandos del sistema usando las herramientas disponibles.

Tienes cargada esta Skill:
- Nombre: {skill_name}
- Descripción: {skill_description}
- Instrucciones:
{skill_instructions}

REGLAS CRÍTICAS para usar gws:
1. Usa SIEMPRE los comandos helper que empiezan por '+' para Gmail.
2. NUNCA uses subcomandos como 'users', 'messages' o 'list' para Gmail.
3. Si usas comandos con '+', NUNCA envíes la clave 'params'. Si te piden limitar a los 3 últimos correos, pide la lista completa con '+triage' y quédate tú con los 3 primeros en tu respuesta.

Herramientas disponibles:
{tools}

Formato obligatorio:

Question: La tarea a resolver.
Thought: Qué comando necesito ejecutar y por qué.
Action: execute_gws_command
Action Input: {{"args": ["servicio", "+helper"]}}
Observation: El resultado del sistema.

Thought: Tengo la información necesaria.
Final Answer: Respuesta final en lenguaje natural basándome en los datos obtenidos.

Ejemplos de Action Input correctos:
- Ver resumen de la bandeja de entrada (Triage): {{"args": ["gmail", "+triage"]}}
- Leer un correo específico por ID: {{"args": ["gmail", "+read", "ID_DE_PRUEBA"]}}

Herramientas disponibles: [{tool_names}]

Question: {input}
Thought: {agent_scratchpad}"""

    prompt = PromptTemplate.from_template(template).partial(
        skill_name=skill_info['metadata']['name'],
        skill_description=skill_info['metadata']['description'],
        skill_instructions=skill_info['instructions']
    )

    llm = ChatOllama(
        model="qwen2.5:7b",
        temperature=0
    )

    tools = [execute_gws_command]

    agent = create_react_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=5  
    )

    response = agent_executor.invoke({
        "input": "Muéstrame los últimos 3 correos electrónicos de mi bandeja."
    })

    print("\n[Respuesta Final]:", response["output"])


if __name__ == "__main__":
    main()