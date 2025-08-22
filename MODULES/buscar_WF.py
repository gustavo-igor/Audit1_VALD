import asyncio
import json
from playwright.sync_api import sync_playwright


def buscador_workflow(page, browser, numero_wf, time=10000):
    # 1. Ir a la pestaña "Buscador"
    page.click("span.x-tab-strip-text:has-text('Buscador')")

    # 2. Ingresar número de requerimiento
    page.wait_for_selector("input#num_requerimiento", timeout=time)
    page.fill("input#num_requerimiento", numero_wf)

    # 3. Desplegar combo y seleccionar "En Tramite"
    page.wait_for_selector("img#ext-gen102", timeout=time)
    page.click("img#ext-gen102")
    page.wait_for_selector("div.x-combo-list-item", timeout=time)
    page.click("div.x-combo-list-item:has-text('En Tramite')")

    # 4. Clic en "Buscar"
    page.wait_for_selector("button:has-text('Buscar')", timeout=time)
    page.get_by_role("button", name="Buscar").click()

    # 5. Esperar que la tabla de resultados esté lista
    page.wait_for_selector("div.x-grid3-cell-inner", timeout=time)

    # 6. Preparar la escucha de la nueva ventana (popup)
    context = page.context
    popup_future = context.wait_for_event("page", timeout=time)

    # 7. Doble clic que dispara el popup
    page.dblclick("div.x-grid3-cell-inner.x-grid3-col-4")

    # 8. Obtener el popup y esperar carga
    popup = popup_future.value
    popup.wait_for_load_state("load")

    # 9. Dentro del popup, hacer clic en "Adjuntos"
    popup.wait_for_selector("img[onclick='AbreAdjuntos()']", timeout=time)
    popup.click("img[onclick='AbreAdjuntos()']")

    return popup


def buscador_pop(page):
    a = "a"
