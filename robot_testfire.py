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

import getpass
import time
import logging
import requests
import socket
import platform
from datetime import datetime
from pathlib import Path

import pandas as pd

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
class InterferenciaUsuario(Exception):
    pass


# -----------------------------
# CONFIGURACIÓN
# -----------------------------
URL = "https://demo.testfire.net/"
URL_API_LOGS = "https://script.google.com/macros/s/AKfycbzYAE9CxelORXH2E_b70id_FJYBSJhOHS79YOUwbI7VDoLv4pDe5vQeqT0C_a9Ds_yOlg/exec"
EJECUCION_ID = None
ESTADO_EJECUCION = "EN_PROCESO"
EQUIPO = socket.gethostname()
SISTEMA_OPERATIVO = platform.system()
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
            verificar_interferencia(driver)
            iniciar_accion_robot(driver)
            elemento.click()
            terminar_accion_robot(driver)
            return
        except TimeoutException as error:
            ultimo_error = error

    raise TimeoutException(
        f"No se pudo hacer clic en ninguno de estos elementos: {localizadores}"
    ) from ultimo_error
def activar_monitor_interferencia(driver):
    """Detecta cambios o acciones manuales del usuario dentro de la página."""

    driver.execute_script("""
        window.robotActuando = false;
        window.interferenciaUsuario = false;
        window.detalleInterferencia = "";

        ["input", "change", "keydown", "click"].forEach(function(tipo) {

            document.addEventListener(tipo, function(evento) {

                if (!window.robotActuando) {

                    window.interferenciaUsuario = true;

                    window.detalleInterferencia =
                        tipo + " en elemento " +
                        evento.target.tagName +
                        " id=" + (evento.target.id || "sin-id");
                }

            }, true);

        });
    """)

    logging.info("Monitor de interferencia activado.")

def verificar_interferencia(driver):
    """Comprueba si el usuario intervino manualmente."""

    interferencia = driver.execute_script(
        "return window.interferenciaUsuario === true;"
    )

    if interferencia:

        detalle = driver.execute_script(
            "return window.detalleInterferencia;"
        )

        logging.error(
            "Interferencia humana detectada: %s",
            detalle
        )

        captura(driver, "99_interferencia_usuario")

        raise InterferenciaUsuario(
            f"El usuario intervino en la automatización: {detalle}"
        )
def iniciar_accion_robot(driver):
    driver.execute_script(
        "window.robotActuando = true;"
    )


def terminar_accion_robot(driver):
    driver.execute_script(
        "window.robotActuando = false;"
    )

def ir_login(driver):
    """Hace clic automáticamente en Sign In."""

    click_primero(driver, [
        (By.LINK_TEXT, "Sign In"),
        (By.PARTIAL_LINK_TEXT, "Sign In"),
        (By.XPATH, "//a[contains(.,'Sign In')]")
    ])

    logging.info("El robot abrió la página de inicio de sesión.")

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
    verificar_interferencia(driver)

    iniciar_accion_robot(driver)
    campo_usuario.clear()
    campo_usuario.send_keys(usuario)

    campo_clave.clear()
    campo_clave.send_keys(clave)
    terminar_accion_robot(driver)

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
        enviar_log_api(
            "INFO",
            "Login",
            "Inicio de sesión correcto"
    )
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
    enviar_log_api(
        "INFO",
        "Navegación",
        "Página de resumen de cuentas abierta"
    )
    captura(driver, "02_account_summary")


def ir_actividad_cuenta(driver):
    """Navega a View Recent Transactions."""
    click_primero(driver, [
        (By.LINK_TEXT, "View Recent Transactions"),
        (By.PARTIAL_LINK_TEXT, "Recent Transactions"),
        (By.XPATH, "//a[contains(.,'View Recent Transactions')]")
    ])

    logging.info("Página de transacciones recientes abierta.")
    enviar_log_api(
        "INFO",
        "Navegación",
        "Página de transacciones recientes abierta"
    )
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
    """Extrae las transacciones de la tabla."""

    tabla = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((
            By.ID,
            "_ctl0__ctl0_Content_Main_MyTransactions"
        ))
    )

    filas = tabla.find_elements(By.TAG_NAME, "tr")

    movimientos = []

    # Recorremos todas las filas de la tabla
    for fila in filas:

        celdas = fila.find_elements(By.TAG_NAME, "td")
        valores = [celda.text.strip() for celda in celdas]

        # Evitamos guardar la cabecera y filas vacías
        if valores and valores[0] != "Transaction ID":
            movimientos.append(valores)

    if len(movimientos) > 0:
        logging.info(
            "Se extrajeron %s filas de movimientos.",
            len(movimientos)
        )
        enviar_log_api(
            "INFO",
            "Extracción",
            f"Se extrajeron {len(movimientos)} movimientos"
        )
    else:
        logging.warning(
            "No se encontraron movimientos para extraer."
        )
        enviar_log_api(
            "WARNING",
            "Extracción",
            "No se encontraron movimientos para extraer"
        )


    return movimientos


def guardar_excel(movimientos):
    fecha = datetime.now().strftime("%Y%m%d_%H%M%S")
    archivo = CARPETA_SALIDA / f"movimientos_{fecha}.xlsx"

    max_columnas = max((len(fila) for fila in movimientos), default=0)

    if max_columnas == 0:
        logging.warning("No se generó Excel porque no había datos.")
        return None

    columnas = [
        "Transaction ID",
        "Transaction Time",
        "Account ID",
        "Action",
        "Amount"
    ]

    

    movimientos_normalizados = [
        fila + [""] * (max_columnas - len(fila))
        for fila in movimientos
    ]

    df = pd.DataFrame(movimientos_normalizados, columns=columnas)
    df.to_excel(archivo, index=False)

    logging.info("Excel generado: %s", archivo)
    enviar_log_api(
        "INFO",
        "Excel",
        f"Reporte generado correctamente: {archivo.name}"
        )
    return archivo

def enviar_log_api(nivel, proceso, mensaje, estado_ejecucion=None):
    """Envía un log a Google Sheets mediante HTTP POST."""
    if estado_ejecucion is None:
        estado_ejecucion = ESTADO_EJECUCION


    datos = {
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "nivel": nivel,
        "proceso": proceso,
        "mensaje": mensaje,
        "ejecucion_id": EJECUCION_ID,
        "estado_ejecucion": estado_ejecucion,
        "equipo": EQUIPO,
        "sistema_operativo": SISTEMA_OPERATIVO

    }

    try:
        respuesta = requests.post(
            URL_API_LOGS,
            json=datos,
            timeout=10
        )

        if respuesta.status_code == 200:
            logging.info("Log enviado correctamente a Google Sheets.")
        else:
            logging.warning(
                "No se pudo enviar el log. Código HTTP: %s",
                respuesta.status_code
            )

    except requests.RequestException as error:
        logging.warning(
            "Error conectando con API de logs: %s",
            error
        )


def main():
    print("Equipo:", EQUIPO)
    print("Sistema operativo:", SISTEMA_OPERATIVO)
    global EJECUCION_ID
    global ESTADO_EJECUCION

    EJECUCION_ID = (
        datetime.now().strftime("EJEC-%Y%m%d-%H%M%S")
        + "-"
        + EQUIPO
    )
    ESTADO_EJECUCION = "EN_PROCESO"

    print("=== ROBOT RPA - DEMO TESTFIRE ===")

    # Credenciales del entorno demo
    usuario = input("Usuario TestFire: ")
    clave = getpass.getpass("Contraseña TestFire: ")

    # Configuración de Chrome
    opciones = webdriver.ChromeOptions()
    opciones.add_argument("--start-maximized")

    # Ignora el error de certificado del sitio demo
    opciones.add_argument("--ignore-certificate-errors")
    opciones.set_capability("acceptInsecureCerts", True)

    driver = None

    try:
        logging.info("Inicio de ejecución del robot.")

        enviar_log_api(
            "INFO",
            "Robot",
            "Inicio de ejecución del robot"
        )

        # -------------------------
        # ABRIR TESTFIRE
        # -------------------------

        driver = webdriver.Chrome(options=opciones)
        driver.get(URL)

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        # Activamos monitor de interferencia
        activar_monitor_interferencia(driver)

        captura(driver, "00_pagina_inicial")

        # Espera 3 segundos
        time.sleep(3)

        # Verifica si el usuario intervino
        verificar_interferencia(driver)


        # -------------------------
        # SIGN IN
        # -------------------------

        ir_login(driver)

        # Como cambió la página, reactivamos el monitor
        activar_monitor_interferencia(driver)

        time.sleep(3)

        verificar_interferencia(driver)


        # -------------------------
        # LOGIN
        # -------------------------

        if iniciar_sesion(driver, usuario, clave):

            # El login cambia nuevamente la página
            activar_monitor_interferencia(driver)

            time.sleep(3)

            verificar_interferencia(driver)


            # -------------------------
            # RESUMEN DE CUENTAS
            # -------------------------

            ir_resumen_cuentas(driver)

            # Nueva página = nuevo monitor
            activar_monitor_interferencia(driver)

            time.sleep(3)

            verificar_interferencia(driver)


            # -------------------------
            # TRANSACCIONES RECIENTES
            # -------------------------

            ir_actividad_cuenta(driver)

            # Nueva página = nuevo monitor
            activar_monitor_interferencia(driver)

            time.sleep(3)

            verificar_interferencia(driver)


            # -------------------------
            # SELECCIONAR CUENTA
            # -------------------------

            seleccionar_cuenta_si_existe(driver)

            # Por seguridad reactivamos el monitor,
            # ya que esta función podría provocar una recarga
            activar_monitor_interferencia(driver)

            time.sleep(3)

            verificar_interferencia(driver)


            # -------------------------
            # EXTRAER MOVIMIENTOS
            # -------------------------

            movimientos = extraer_movimientos(driver)

            time.sleep(3)

            verificar_interferencia(driver)


            # -------------------------
            # GENERAR EXCEL
            # -------------------------

            archivo = guardar_excel(movimientos)

            if archivo:
                ESTADO_EJECUCION = "EXITOSA"
                print(f"OK: reporte generado en {archivo}")
            else:
                ESTADO_EJECUCION = "SIN_DATOS"
                enviar_log_api(
                    "WARNING",
                    "Excel",
                    "No se generó el reporte porque no había movimientos",
                    ESTADO_EJECUCION
                )
                print(
                    "El robot terminó, pero no encontró "
                    "movimientos para exportar."
                )

        else:
            ESTADO_EJECUCION = "ERROR_LOGIN"
            enviar_log_api(
                "ERROR",
                "Login",
                "Credenciales inválidas o sesión no iniciada",
                ESTADO_EJECUCION
            )
            print(
                "ERROR: credenciales inválidas "
                "o sesión no iniciada."
            )


    # -------------------------
    # INTERFERENCIA DEL USUARIO
    # -------------------------

    except InterferenciaUsuario as error:
        

        ESTADO_EJECUCION = "CANCELADA_INTERFERENCIA"
        logging.error(str(error))
        enviar_log_api(
            "ERROR",
            "Interferencia",
            str(error),
            ESTADO_EJECUCION
        )

        print("AUTOMATIZACIÓN CANCELADA:")
        print("Se detectó intervención manual del usuario.")


    # -------------------------
    # ERRORES DE SELENIUM
    # -------------------------

    except (TimeoutException, NoSuchElementException) as error:
        ESTADO_EJECUCION = "ERROR_SELENIUM"
        logging.exception(
            "Error de Selenium: %s",
            error
        )
        enviar_log_api(
            "ERROR",
            "Selenium",
            f"No se encontró un elemento esperado: {error}",
            ESTADO_EJECUCION
        )

        print(
            "ERROR: no se encontró un elemento "
            "esperado en la página."
        )

        if driver:
            captura(
                driver,
                "99_error_selenium"
            )


    # -------------------------
    # OTROS ERRORES
    # -------------------------

    except Exception as error:
        ESTADO_EJECUCION = "ERROR_GENERAL"

        logging.exception(
            "Error inesperado: %s",
            error
        )
        enviar_log_api(
            "ERROR",
            "General",
            f"Error inesperado: {error}",
            ESTADO_EJECUCION
        )

        print(
            f"ERROR inesperado: {error}"
        )

        if driver:
            captura(
                driver,
                "99_error_general"
            )


    # -------------------------
    # CIERRE DEL ROBOT
    # -------------------------

    finally:

        if driver:
            time.sleep(2)
            driver.quit()

        logging.info(
            "Fin de ejecución del robot."
        )
        enviar_log_api(
            "INFO",
            "Robot",
            "Fin de ejecución del robot",
            ESTADO_EJECUCION
        )

        print(
            "Proceso finalizado. "
            "Revisa la carpeta 'salida' "
            "para logs, Excel y capturas."
        )


if __name__ == "__main__":
    main()