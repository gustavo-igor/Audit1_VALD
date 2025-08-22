import time
import os
import pyautogui
import PyPDF2
import re
import openpyxl
import pandas as pd
import win32com.client as win32
import shutil
import winreg
import pythoncom
import numpy as np
import glob
import tkinter as tk
import matplotlib.pyplot as plt
import seaborn as sns
import cv2
import tkinter as tk
import threading
import sys
import traceback
import json

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementNotInteractableException, ElementClickInterceptedException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import StaleElementReferenceException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from datetime import datetime, timedelta
from openpyxl import load_workbook
from tqdm import tqdm
from tkinter import ttk
from PIL import Image, ImageTk
from io import BytesIO
from tkinter import messagebox
from tkinter import Tk, Button
from tkinter.scrolledtext import ScrolledText
from plyer import notification
from bs4 import BeautifulSoup
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from tkcalendar import DateEntry
from datetime import date

import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.scrolledtext import ScrolledText
from tkinter import simpledialog
from tkcalendar import DateEntry
import threading, time, sys, traceback, json, os


def get_script_directory():
    """ Obtiene la ruta del script en ejecución """
    return os.path.dirname(os.path.abspath(__file__))

def convert_rutas():
    global ruta_script_python,ruta_guardado_BBDD,ruta_guardado_PTs,ruta_guardado_Caso, ruta_guardado_Comuna
    global libro_destino_bloque_restauracion_com_xlsx

    ruta_script_python = get_script_directory()
    ruta_guardado_BBDD = os.path.join(ruta_script_python, "BBDD")
    ruta_guardado_PTs = os.path.join(ruta_script_python, "PDF")
    ruta_guardado_Caso = os.path.join(ruta_script_python, "CASO")
    ruta_guardado_Comuna = os.path.join(ruta_script_python, "COMUNAS")

    # Crear las carpetas si no existen
    if not os.path.exists(ruta_guardado_BBDD):
        os.makedirs(ruta_guardado_BBDD)
    
    if not os.path.exists(ruta_guardado_PTs):
        os.makedirs(ruta_guardado_PTs)
    
    if not os.path.exists(ruta_guardado_Caso):
        os.makedirs(ruta_guardado_Caso)

    # Definir la ruta de destino
    libro_destino_bloque_restauracion_com_xlsx = os.path.join(ruta_guardado_BBDD, 'Bloques_de_restauracion_por_com.xlsx')

def configurar_navegador_BBDD():
    chrome_options = Options()
    ruta_guardado_BBDD = os.path.join(ruta_script_python, "BBDD")

    # Configurar la ruta de descarga
    prefs = {
        "download.default_directory": ruta_guardado_BBDD,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
        'printing.print_preview_sticky_settings.appState': (
                '{"recentDestinations":[{"id":"Save as PDF","origin":"local","account":"","capabilities":{}}],'
                '"selectedDestinationId":"Save as PDF","version":2}'
        )
    }
    chrome_options.add_experimental_option("prefs", prefs)
    navegador = webdriver.Chrome(options=chrome_options)
    return navegador

def iniciar_sesion(navegador,correo,contrasena,url):
    try:
        navegador.get(url)
        navegador.maximize_window()

        email_input = WebDriverWait(navegador, 20).until(EC.visibility_of_element_located((By.ID, "i0116")))
        email_input.clear()
        email_input.send_keys(correo)

        siguiente_btn = WebDriverWait(navegador, 10).until(EC.element_to_be_clickable((By.ID, "idSIButton9")))
        siguiente_btn.click()

        password_input = WebDriverWait(navegador, 20).until(EC.visibility_of_element_located((By.ID, "i0118")))
        password_input.clear()
        password_input.send_keys(contrasena)

        sesion_btn = WebDriverWait(navegador, 10).until(EC.element_to_be_clickable((By.ID, "idSIButton9")))
        sesion_btn.click()


        boton_xpath = (
                "//div[@data-control-name='btnBuscador']"
                "//button[contains(@class,'appmagic-button-container')]"
            )

            # 2) Esperar hasta que el elemento exista en el DOM
        btn = WebDriverWait(navegador, 20).until(
            EC.presence_of_element_located((By.XPATH, boton_xpath))
        )

        # 3) Hacer scroll para que quede visible
        navegador.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)

        # 4) Esperar a que sea clickeable
        WebDriverWait(navegador, 20).until(
            EC.element_to_be_clickable((By.XPATH, boton_xpath))
        )

        # 5) Intentar click normal, sino usar JS
        try:
            btn.click()
        except Exception:
            navegador.execute_script("arguments[0].click();", btn)


    
        print("Inicio de sesión exitoso.")
    except Exception as e:
        print(f"Error en inicio de sesión: {e}")

def buscar_SAP(navegador):
    navegador.get("h")

def main():
    global libro_origen, libro_destino_bloque_restauracion_com_xlsx
    
    Valoriza = 'https://apps.powerapps.com/play/e/default-136d6ab5-5b55-496f-97cb-2424247715ed/a/3ee1e8fa-2ed3-4e1b-bfa3-9a14bb28ff6e?tenantId=136d6ab5-5b55-496f-97cb-2424247715ed&source=portal'
    correo = entry_email.get()
    password = entry_password.get()

    if stop_event.is_set(): return
    convert_rutas()

    if stop_event.is_set(): return
    navegador=configurar_navegador_BBDD()

    while pause_event.is_set(): time.sleep(0.5)
    if stop_event.is_set(): return
    iniciar_sesion(navegador,correo,password,Valoriza)

    

    navegador.quit()

# Variables globales de control
pause_event = threading.Event()
stop_event = threading.Event()
estado_pausa = False

# Título de la ventana principal
title_form = "RPA Probatorio"

class TextRedirector:
    
    def __init__(self, widget, tag="stdout"):
        self.widget = widget
        self.tag = tag

    def write(self, str):
        self.widget.configure(state='normal')  # Habilita temporalmente para insertar
        self.widget.insert(tk.END, str)
        self.widget.see(tk.END)
        self.widget.configure(state='disabled')  # Desactiva edición

    def flush(self):
        pass  # Requerido por sys.stdout

# Funciones de control
def iniciar_app():
    boton_inicio.config(state='disabled')
    stop_event.clear()
    pause_event.clear()

    def ejecutar_main():
        try:
            boton_inicio.config(text="Procesando...", state="disabled")
            print("Proceso iniciado...")

            # Aquí iría u función principal
            main()

            if not stop_event.is_set():
                print("¡Proceso finalizado correctamente!")
                messagebox.showinfo("Proceso finalizado", "La ejecución ha terminado correctamente.")
        except Exception:
            error_msg = traceback.format_exc()
            print(error_msg)
            messagebox.showerror("Error", "Ocurrió un error durante la ejecución.\nRevisa la consola para más detalles.")
        finally:
            boton_inicio.config(text="Iniciar", state="normal")

    threading.Thread(target=ejecutar_main, daemon=True).start()

def pausar_app():
    global estado_pausa
    estado_pausa = not estado_pausa

    if estado_pausa:
        pause_event.set()
        boton_pausa.config(text="Reanudar")
        print("⏸ Proceso en pausa...")
    else:
        pause_event.clear()
        boton_pausa.config(text="Pausar")
        print("▶ Proceso reanudado...")

def detener_app():
    stop_event.set()
    print("==> Solicitud de detención recibida...")

def limpiar_consola():
    output_text.configure(state='normal')
    output_text.delete(1.0, tk.END)
    output_text.configure(state='disabled')

def main_loop_simulado():
    for i in range(1, 101):
        if stop_event.is_set():
            print(f"Proceso detenido en el paso {i}")
            break
        while pause_event.is_set():
            time.sleep(0.5)
        print(f"Paso {i} completado.")
        time.sleep(0.1)

def toggle_password():
    if entry_password.cget('show') == '':
        entry_password.config(show='*')
        toggle_btn.config(text='Mostrar')
    else:
        entry_password.config(show='')
        toggle_btn.config(text='Ocultar')

# Configuración de la interfaz
root = tk.Tk()
root.title(f"{title_form} - (©) abdiel.reyes@saesa.cl")
root.geometry("900x600")

# Aplicar tema 'clam' para un estilo moderno
style = ttk.Style()
style.theme_use('clam')

# Frame superior para correo y contraseña
top_frame = ttk.Frame(root)
top_frame.pack(side='top', fill='x', padx=10, pady=10)

# Campo de correo
ttk.Label(top_frame, text='Correo:').pack(side='left', padx=5)
entry_email = ttk.Entry(top_frame, width=30)
entry_email.pack(side='left', padx=5)

# Campo de contraseña
ttk.Label(top_frame, text='Contraseña:').pack(side='left', padx=5)
entry_password = ttk.Entry(top_frame, width=30, show='*')
entry_password.pack(side='left', padx=5)

# Botón para mostrar/ocultar contraseña
toggle_btn = ttk.Button(top_frame, text='Mostrar', width=10, command=toggle_password)
toggle_btn.pack(side='left', padx=5)

# Frame principal
main_frame = ttk.Frame(root)
main_frame.pack(fill='both', expand=True, padx=10, pady=10)

# Frame izquierdo para fechas y consola
left_frame = ttk.Frame(main_frame)
left_frame.pack(side='left', fill='both', expand=True)

# Consola
output_text = ScrolledText(left_frame, height=20)
output_text.configure(state='disabled')
output_text.pack(fill='both', expand=True, pady=10)

# Redirigir stdout y stderr
sys.stdout = TextRedirector(output_text, "stdout")
sys.stderr = TextRedirector(output_text, "stderr")

# Frame derecho para órdenes de trabajo y botones
right_frame = ttk.Frame(main_frame)
right_frame.pack(side='right', fill='y', padx=10)

# Campo para órdenes de trabajo
ttk.Label(right_frame, text='Órdenes de Trabajo:').pack(pady=5)
ordenes_text = tk.Text(right_frame, width=30, height=15)
ordenes_text.pack(pady=5)

# Botones de control
boton_inicio = ttk.Button(right_frame, text="Iniciar", width=20, command=iniciar_app)
boton_inicio.pack(pady=5)

boton_pausa = ttk.Button(right_frame, text="Pausar", width=20, command=pausar_app)
boton_pausa.pack(pady=5)

boton_detener = ttk.Button(right_frame, text="Detener", width=20, command=detener_app)
boton_detener.pack(pady=5)

boton_limpiar = ttk.Button(right_frame, text="Limpiar consola", width=20, command=limpiar_consola)
boton_limpiar.pack(pady=5)

root.mainloop()