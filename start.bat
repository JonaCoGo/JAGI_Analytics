@echo off
:: Configuramos la ruta completa del archivo
set "PAGINA_WEB=C:\JAGI_Analytics\templates\index.html"

echo [SISTEMA] Iniciando servidor y cargando interfaz...

:: Lanza un proceso en segundo plano que espera 3 segundos y abre el HTML
:: Usamos "" despues de start porque la ruta tiene espacios
start /b cmd /c "timeout /t 3 /nobreak > NUL & start "" "%PAGINA_WEB%""

:: Si usas entorno virtual, descomenta la siguiente línea:
:: call venv\Scripts\activate

:: Inicia el servidor de FastAPI/Uvicorn
uvicorn app.main:app --reload

pause