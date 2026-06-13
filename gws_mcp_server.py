import os
import subprocess
from mcp.server.fastmcp import FastMCP

# Inicializamos el servidor FastMCP
server = FastMCP("GWS-Gmail-Skill-Server")

SKILL_PATH = ".agents/skills/gws-gmail/SKILL.md"

def load_local_skill_raw() -> str:
    """Lee el archivo SKILL.md y extrae las instrucciones limpias."""
    if not os.path.exists(SKILL_PATH):
        return "Reglas: Usa siempre los helpers con '+' como +triage o +read."
        
    with open(SKILL_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    # Si contiene Frontmatter (---), nos quedamos solo con las instrucciones Markdown
    if content.startswith("---"):
        try:
            _, _, markdown_instructions = content.split("---", 2)
            return markdown_instructions.strip()
        except ValueError:
            return content.strip()

    return content.strip()

# =========================================================================
# HERRAMIENTA MCP (Tool)
# =========================================================================
@server.tool()
def execute_gws_command(args: list) -> str:
    """
    Ejecuta comandos de la CLI gws para Gmail de manera nativa en el sistema.
    
    SINTAXIS MANDATORIA:
    - Pasa los subcomandos en la lista 'args' separados por elementos.
    - Ejemplo para listar: ['gmail', '+triage']
    - Ejemplo para leer: ['gmail', '+read', 'ID_DE_CORREO']
    
    REGLA CRÍTICA: No utilices parámetros JSON ni subcomandos complejos de la API de Google.
    Usa única y exclusivamente los helpers con el signo '+' delante.
    """
    # Limpieza estricta de argumentos por seguridad
    clean_args = [str(arg).strip('"').strip("'") for arg in args if arg]
    
    full_command = ["gws"] + clean_args

    print(f"\n[Servidor MCP] Ejecutando en sistema: {' '.join(full_command)}")

    try:
        result = subprocess.run(
            full_command,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout if result.stdout else "Comando ejecutado con éxito (sin salida)."
    except subprocess.CalledProcessError as e:
        return f"Error en la ejecución de gws desde el Servidor MCP: {e.stderr}"
    except FileNotFoundError:
        return "Error crítico: El ejecutable 'gws' no está instalado en el PATH del Servidor."

# =========================================================================
# PROMPT MCP (Aquí es donde vive el contexto de tu Skill)
# =========================================================================
@server.prompt()
def gws_gmail_instructions() -> str:
    """
    Devuelve las directrices operativas, el contexto y las reglas 
    de comportamiento extraídas directamente del archivo SKILL.md.
    """
    markdown_context = load_local_skill_raw()
    
    full_prompt = f"""Estás operando bajo la Skill oficial de Gmail. 
A continuación tienes las instrucciones de comportamiento obligatorias que debes seguir:

{markdown_context}

REGLA DE ORO ADICIONAL:
Si el usuario te solicita una cantidad específica de correos (ej. los últimos 3), 
tú debes invocar la herramienta execute_gws_command enviando únicamente en args: ["gmail", "+triage"]. 
Recibirás la lista entera y tú, usando tu propia capacidad de análisis, seleccionarás y formatearás los 3 primeros para el usuario.
"""
    return full_prompt

if __name__ == "__main__":
    # Arranca el servidor usando el transporte estándar de comunicación (stdin/stdout)
    server.run(transport="stdio")