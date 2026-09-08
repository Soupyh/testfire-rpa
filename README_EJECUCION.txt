SOLUCIÓN RPA - DEMO TESTFIRE

1. Requisitos
   - Python 3.10 o superior.
   - Google Chrome instalado.
   - Acceso a Internet.

2. Instalar dependencias
   Abre CMD o PowerShell en esta carpeta y ejecuta:

   pip install -r requirements.txt

3. Ejecutar
   python robot_testfire.py

4. Credenciales
   El programa pedirá:
   - Usuario jsmith
   - Contraseña demo1234

   La contraseña se ingresa oculta para evitar dejarla escrita en el código.

5. Evidencias generadas
   Se crea automáticamente la carpeta "salida", que contiene:
   - robot_testfire.log
   - movimientos_FECHA.xlsx
   - capturas/00_pagina_inicial.png
   - capturas/01_login_correcto.png
   - capturas/02_account_summary.png
   - capturas/03_account_activity.png
   - capturas de error si corresponde
