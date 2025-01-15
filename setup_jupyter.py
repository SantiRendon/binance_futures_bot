import subprocess
import sys
import os

def run_command(command, error_message):
    """Ejecuta un comando en la terminal y maneja errores."""
    try:
        subprocess.check_call(command, shell=True)
    except subprocess.CalledProcessError:
        print(error_message)
        sys.exit(1)

def setup_jupyter_kernel(venv_path, kernel_name, display_name):
    """
    Configura el kernel de Jupyter para un entorno virtual.
    
    Args:
        venv_path (str): Ruta del entorno virtual.
        kernel_name (str): Nombre del kernel en Jupyter.
        display_name (str): Nombre mostrado en Jupyter.
    """
    # Activa el entorno virtual
    python_executable = os.path.join(venv_path, "python" if os.name != "nt" else "Scripts\\python.exe")
    if not os.path.exists(python_executable):
        print(f"Python ejecutable no encontrado en: {python_executable}")
        sys.exit(1)
    
    print(f"Usando Python: {python_executable}")
    
    # Instala ipykernel si no está instalado
    print("Instalando ipykernel si no está disponible...")
    run_command(f"{python_executable} -m pip install ipykernel", "Error instalando ipykernel.")
    
    # Registra el kernel
    print("Registrando kernel en Jupyter...")
    run_command(
        f"{python_executable} -m ipykernel install --user --name={kernel_name} --display-name \"{display_name}\"",
        "Error registrando el kernel en Jupyter."
    )
    print("¡Kernel configurado con éxito!")

if __name__ == "__main__":
    # Configuración del entorno
    VENV_PATH = ".venv"  # Cambia si tu entorno virtual está en otra ruta
    KERNEL_NAME = ".venv"
    DISPLAY_NAME = "Python (.venv)"

    setup_jupyter_kernel(VENV_PATH, KERNEL_NAME, DISPLAY_NAME)
