@echo off
:: Si usas entorno virtual, descomenta la siguiente línea:
:: call venv\Scripts\activate

uvicorn app.main:app --reload
pause