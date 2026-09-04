"""
ROBOT RPA - Demo TestFire
Asignatura: Automatización de Procesos Robóticos I

Objetivo:
1) Abrir TestFire.
2) Iniciar sesión.
3) Navegar al resumen de cuentas.
4) Navegar a actividad de cuenta.
5) Extraer una tabla de movimientos usando un ciclo for.
6) Guardar la información en Excel.
7) Aplicar condicionales, validaciones y manejo de excepciones.
8) Guardar capturas y logs como evidencia.
"""

import os
import time
import logging
import getpass
from datetime import datetime
from pathlib import Path

import pandas as pd

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException


# -----------------------------
# CONFIGURACIÓN
# -----------------------------
URL = "https://demo.testfire.net/"
CARPETA_SALIDA = Path("salida")
CARPETA_CAPTURAS = CARPETA_SALIDA / "capturas"
CARPETA_SALIDA.mkdir(exist_ok=True)
CARPETA_CAPTURAS.mkdir(exist_ok=True)

logging.basicConfig(
    filename=CARPETA_SALIDA / "robot_testfire.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    encoding="utf-8"
)


def captura(driver, nombre):
    """Guarda una captura de pantalla como evidencia."""
    ruta = CARPETA_CAPTURAS / f"{nombre}.png"
    driver.save_screenshot(str(ruta))
    logging.info("Captura guardada: %s", ruta)


def buscar_primero(driver, localizadores, timeout=10):
    """
    Intenta varios localizadores y devuelve el primer elemento visible.
    Esto hace el robot un poco más resistente a cambios menores del sitio.
    """
    ultimo_error = None

    for by, valor in localizadores:
        try:
            return WebDriverWait(driver, timeout).until(
                EC.visibility_of_element_located((by, valor))
            )
        except TimeoutException as error:
            ultimo_error = error

    raise TimeoutException(
        f"No se encontró ninguno de los elementos esperados: {localizadores}"
    ) from ultimo_error


def click_primero(driver, localizadores, timeout=10):
    """Intenta varios localizadores y hace clic en el primero disponible."""
    ultimo_error = None

    for by, valor in localizadores:
        try:
            elemento = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((by, valor))
            )
            elemento.click()
            return
        except TimeoutException as error:
            ultimo_error = error

    raise TimeoutException(
        f"No se pudo hacer clic en ninguno de estos elementos: {localizadores}"
    ) from ultimo_error


def iniciar_sesion(driver, usuario, clave):
    """Carga usuario/contraseña y valida si el login fue correcto."""
    logging.info("Intentando iniciar sesión.")

    campo_usuario = buscar_primero(driver, [
        (By.NAME, "uid"),
        (By.XPATH, "//input[contains(@id,'uid')]")
    ])

    campo_clave = buscar_primero(driver, [
        (By.NAME, "passw"),
        (By.XPATH, "//input[@type='password']")
    ])

    campo_usuario.clear()
    campo_usuario.send_keys(usuario)

    campo_clave.clear()
    campo_clave.send_keys(clave)

    click_primero(driver, [
        (By.NAME, "btnSubmit"),
        (By.XPATH, "//input[@type='submit']"),
        (By.XPATH, "//button[contains(.,'Login')]")
    ])

    time.sleep(1)

    # CONDICIONAL 1: comprobar si el inicio de sesión fue exitoso.
    login_correcto = (
        "sign off" in driver.page_source.lower()
        or "view account summary" in driver.page_source.lower()
        or "account summary" in driver.page_source.lower()
    )

    if login_correcto:
        logging.info("Login correcto.")
        captura(driver, "01_login_correcto")
        return True
    else:
        logging.error("Login inválido o no se pudo validar la sesión.")
        captura(driver, "01_error_login")
        return False


def ir_resumen_cuentas(driver):
    """Navega a View Account Summary."""
    click_primero(driver, [
        (By.LINK_TEXT, "View Account Summary"),
        (By.PARTIAL_LINK_TEXT, "Account Summary"),
        (By.XPATH, "//a[contains(.,'View Account Summary')]")
    ])
    logging.info("Página de resumen de cuentas abierta.")
    captura(driver, "02_account_summary")


def ir_actividad_cuenta(driver):
    """Navega a View Recent Transactions."""
    click_primero(driver, [
        (By.LINK_TEXT, "View Recent Transactions"),
        (By.PARTIAL_LINK_TEXT, "Recent Transactions"),
        (By.XPATH, "//a[contains(.,'View Recent Transactions')]")
    ])

    logging.info("Página de transacciones recientes abierta.")
    captura(driver, "03_recent_transactions")


def seleccionar_cuenta_si_existe(driver):
    """
    Si existe una lista desplegable de cuentas, selecciona la primera opción válida.
    Si no existe, el robot continúa.
    """
    try:
        select_element = WebDriverWait(driver, 4).until(
            EC.presence_of_element_located((
                By.XPATH,
                "//select[contains(@name,'account') or contains(@id,'account')]"
            ))
        )

        selector = Select(select_element)

        # CONDICIONAL 2: valida si hay más de una opción en el selector.
        if len(selector.options) > 1:
            selector.select_by_index(1)
            logging.info("Se seleccionó la primera cuenta disponible.")
        else:
            selector.select_by_index(0)
            logging.info("Solo había una cuenta disponible.")

        # Intentar ejecutar la consulta si existe un botón correspondiente.
        try:
            click_primero(driver, [
                (By.XPATH, "//input[@type='submit' and (@value='Go' or @value='GO')]"),
                (By.XPATH, "//input[@type='submit']"),
                (By.XPATH, "//button[@type='submit']")
            ], timeout=3)
        except TimeoutException:
            logging.info("No fue necesario presionar botón para seleccionar la cuenta.")

    except TimeoutException:
        logging.info("No se encontró selector de cuenta; se continúa con la vista actual.")


def extraer_movimientos(driver):
    """
    Extrae filas de una tabla de transacciones.
    Usa un ciclo FOR, cumpliendo la exigencia de repetición de la rúbrica.
    """
    posibles_filas = [
        (By.XPATH, "//table[@id='transactionTable']//tbody//tr"),
        (By.XPATH, "//table[@id='transactionTable']//tr[td]"),
        (By.XPATH, "//table[contains(.,'Transaction') or contains(.,'Date')]//tr[td]")
    ]

    filas = []
    for localizador in posibles_filas:
        try:
            filas = WebDriverWait(driver, 5).until(
                EC.presence_of_all_elements_located(localizador)
            )
            if filas:
                break
        except TimeoutException:
            filas = []

    movimientos = []

    # CICLO FOR solicitado por la rúbrica.
    for fila in filas:
        celdas = fila.find_elements(By.TAG_NAME, "td")
        valores = [celda.text.strip() for celda in celdas]

        if valores:
            movimientos.append(valores)

    # CONDICIONAL 3: validar si se extrajo información.
    if len(movimientos) > 0:
        logging.info("Se extrajeron %s filas de movimientos.", len(movimientos))
    else:
        logging.warning("No se encontraron movimientos para extraer.")

    return movimientos


def guardar_excel(movimientos):
    """Guarda los movimientos en un archivo Excel."""
    fecha = datetime.now().strftime("%Y%m%d_%H%M%S")
    archivo = CARPETA_SALIDA / f"movimientos_{fecha}.xlsx"

    # Como la tabla del sitio puede variar, se generan nombres de columnas dinámicos.
    max_columnas = max((len(fila) for fila in movimientos), default=0)

    if max_columnas == 0:
        logging.warning("No se generó Excel porque no había datos.")
        return None

    columnas = [f"Columna_{i}" for i in range(1, max_columnas + 1)]
    movimientos_normalizados = [
        fila + [""] * (max_columnas - len(fila))
        for fila in movimientos
    ]

    df = pd.DataFrame(movimientos_normalizados, columns=columnas)
    df.to_excel(archivo, index=False)

    logging.info("Excel generado: %s", archivo)
    return archivo


def main():
    print("=== ROBOT RPA - DEMO TESTFIRE ===")

    # Las credenciales no quedan escritas en el código.
    usuario = os.getenv("TESTFIRE_USER") or input("Usuario TestFire: ")
    clave = os.getenv("TESTFIRE_PASSWORD") or getpass.getpass("Contraseña TestFire: ")

    opciones = webdriver.ChromeOptions()
    opciones.add_argument("--start-maximized")

    driver = None

    try:
        logging.info("Inicio de ejecución del robot.")

        driver = webdriver.Chrome(options=opciones)
        driver.get(URL)

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        captura(driver, "00_pagina_inicial")

        if iniciar_sesion(driver, usuario, clave):
            ir_resumen_cuentas(driver)
            ir_actividad_cuenta(driver)
            seleccionar_cuenta_si_existe(driver)

            movimientos = extraer_movimientos(driver)
            archivo = guardar_excel(movimientos)

            if archivo:
                print(f"OK: reporte generado en {archivo}")
            else:
                print("El robot terminó, pero no encontró movimientos para exportar.")

        else:
            print("ERROR: credenciales inválidas o sesión no iniciada.")

    # EXCEPCIÓN / MANEJO DE ERROR exigido por la rúbrica.
    except (TimeoutException, NoSuchElementException) as error:
        logging.exception("Error de Selenium: %s", error)
        print("ERROR: no se encontró un elemento esperado en la página.")

        if driver:
            captura(driver, "99_error_selenium")

    except Exception as error:
        logging.exception("Error inesperado: %s", error)
        print(f"ERROR inesperado: {error}")

        if driver:
            captura(driver, "99_error_general")

    finally:
        if driver:
            time.sleep(2)
            driver.quit()

        logging.info("Fin de ejecución del robot.")
        print("Proceso finalizado. Revisa la carpeta 'salida' para logs, Excel y capturas.")


if __name__ == "__main__":
    main()
