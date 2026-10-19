# Visualizador de pila con Flask

Aplicación educativa para visualizar una pila LIFO y practicar `push`, `pop`, `peek` y vaciado. La interfaz usa Bootstrap por CDN; no incluye CSS personalizado.

## Requisitos
- Python 3.10 o posterior
- Conexión a internet para cargar Bootstrap desde CDN

## Instalación

```bash
python -m venv .venv
```

Activa el entorno virtual:

- Windows (PowerShell): `.venv\\Scripts\\Activate.ps1`
- Windows (CMD): `.venv\\Scripts\\activate.bat`
- macOS/Linux: `source .venv/bin/activate`

Instala dependencias y ejecuta:

```bash
pip install -r requirements.txt
python app.py
```

Abre http://127.0.0.1:5000 en el navegador.

## Buenas prácticas incluidas
- Rutas separadas para cada operación de la pila.
- Validación de entradas vacías y longitud máxima en el formulario.
- Uso de `session` para que cada navegador tenga su propia pila.
- Mensajes de resultado y confirmación antes de vaciar.
- Funciones `is_empty` y `len_stack` con tipos de retorno consistentes.

## Nota de seguridad
La clave secreta de desarrollo es solo para ejecutar localmente. Antes de desplegar, define una variable de entorno `FLASK_SECRET_KEY` con una clave larga y aleatoria. No actives el modo debug en producción.
