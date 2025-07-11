# Usa imagen oficial de Python 3.11
FROM python:3.11-slim

# Establece el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copia los archivos necesarios al contenedor
COPY . /app

# Crea el virtualenv en /opt/venv
RUN python -m venv /opt/venv

# Actualiza pip e instala dependencias usando pip del virtualenv
RUN /opt/venv/bin/pip install --upgrade pip
RUN /opt/venv/bin/pip install -r requirements.txt

# Establece el PATH para usar el virtualenv automáticamente
ENV PATH="/opt/venv/bin:$PATH"

# Comando para correr el bot
CMD ["python", "main.py"]
