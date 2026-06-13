# 1. Usamos una imagen base de Python
FROM python:3.11-slim

# 2. Creamos la carpeta de trabajo dentro del contenedor
WORKDIR /app

# 3. Copiamos los requisitos e instalamos las librerías
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copiamos tu código (main.py, etc.)
COPY . .

# 5. Comando para arrancar tu agente
CMD ["python", "main.py"]
