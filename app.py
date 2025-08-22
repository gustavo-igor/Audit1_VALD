import json, time, asyncio,threading, sys, os, webbrowser,sqlite3, pandas as pd, datetime
from playwright.sync_api import sync_playwright
from flask import Flask, flash, request, session, redirect, url_for, render_template,jsonify, send_from_directory, abort, send_file
from flask_socketio import SocketIO, emit
from functools import wraps
from apscheduler.schedulers.background import BackgroundScheduler


from MODULES import rutas
from MODULES import Sap
from MODULES.RPA_SAP.Norma_Liquidacion import norma_liquidacion_sap, CN47N, obtener_libro_abierto
from MODULES.RPA_SAP.Asignacion_programa import Programa
from MODULES.RPA_SAP.Cambio_nombre import cambio_nombre
from MODULES.RPA_SAP.CPresupuesto import cpresupuesto
from MODULES.RPA_SAP.cambio_clase_proyecto import cambio_claseproyecto
from MODULES.RPA_SAP.cambio_zonal import cambio_de_zonal


from MODULES.RPA_VALORIZA.valoriza import valoriza, esperar_login,Scrapping_valoriza, escribir_panel_obras
from MODULES.SQLITE.CONTROLLER.sqlite import crear_base_de_datos_final, crear_base_de_datos_final_conversarDB
from MODULES.SQLITE.CONTROLLER.proyectos import get_Proyectos, get_filter_options_data,get_proyectos_para_selector, get_fechas_proyecto
from MODULES.SQLITE.CONTROLLER.proyectos_detalles import get_proyecto_details, update_proyecto_details
from MODULES.maps import Creacion_mapas, obtener_categorias_unicas, obtener_contratistas_unicos
from MODULES.SQLITE.CONTROLLER.tareas import get_tareas_por_proyecto, actualizar_estado_tarea_proyecto, crear_nueva_tarea_proyecto, get_todas_las_tareas,get_checklist_por_tarea,eliminar_tarea_por_id,actualizar_tarea,agregar_comentario,get_comentarios_por_tarea, actualizar_comentario, eliminar_comentario, revisar_tareas_proximas_a_vencer 
from MODULES.SQLITE.CONTROLLER.calendario import get_eventos, crear_evento, actualizar_evento, eliminar_evento, get_todas_las_brigadas, reprogramar_evento, get_tipos_permiso_trabajo, confirmar_permiso_trabajo, eliminar_permiso_trabajo
from MODULES.SQLITE.CONTROLLER.matrizriesgo import obtener_riesgo_por_id, obtener_riesgos_por_proyecto,actualizar_riesgo,eliminar_riesgo, crear_riesgo
from MODULES.documentos import subir_documentos, listar_documentos, eliminar_documento, subir_adjunto_para_tarea, listar_adjuntos_por_tarea,get_documento_por_id
from MODULES.SQLITE.CONTROLLER.gantt import get_gantt_por_proyecto, crear_gantt_task, eliminar_gantt_batch,actualizar_gantt_task, crear_gantt_link,actualizar_gantt_link,eliminar_gantt_link
from MODULES.SQLITE.CONTROLLER.opciones_proyecto_nuevo import get_all_options, get_option_by_id, create_option, update_option, delete_option, export_table_to_excel 
from MODULES.SQLITE.CONTROLLER.beneficiario import get_beneficiarios_por_proyecto, update_beneficiario, delete_beneficiario, create_beneficiario,upload_beneficiarios_from_file,download_beneficiarios_as_excel


from MODULES.ETL.avance_financiero import get_avance_financiero_general
from MODULES.ETL.avance_fisico import get_avance_fisico_general
from MODULES.ETL.tarjetas import get_detalle_dashboard_proyecto


from MODULES.SQLITE.CONTROLLER.seguridad import verificar_password 
from MODULES.SQLITE.CONTROLLER.login import verificar_credenciales 


from MODULES.SQLITE.CONTROLLER.crear_admin import crear_usuario_admin
from MODULES.SQLITE.CONTROLLER.usuarios import get_all_users_with_details, get_user_by_id, create_user, update_user, delete_user
from MODULES.SQLITE.CONTROLLER.roles import get_all_roles, get_role_permissions, update_role_permissions


app = Flask(__name__)
socketio = SocketIO(app, async_mode="eventlet")


# Configura una clave secreta para la sesión
app.secret_key = os.urandom(24)

# --- DECORADOR DE AUTENTICACIÓN ---
# Este "decorador" se usará para proteger las rutas
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('rol') != 'Administrador':
            return jsonify({"error": "Acceso no autorizado"}), 403
        return f(*args, **kwargs)
    return decorated_function

# --- RUTAS DE LOGIN Y LOGOUT ---
@app.route("/login", methods=['GET', 'POST'])
def login_page():
    if request.method == 'POST':

        access_type = request.form.get('access_type')
        email = request.form.get('email')
        password = request.form.get('password')

        # 1. Se pasa el tipo de acceso a la función de lógica
        session_data, error_message = verificar_credenciales(email, password, access_type)

        if session_data:
            session.clear()
            for key, value in session_data.items():
                session[key] = value
            
            return redirect(url_for('index'))
        else:
            flash(error_message, 'danger')
            return redirect(url_for('login_page'))

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('login_page'))

@app.route("/")

@login_required
def index():
    #return render_template("layout.html")
    return render_template("layout.html", user_permisos=session.get('permisos', []))

@login_required
def obtener_config():
    with open('config.json', 'r', encoding='utf-8') as f:
        return json.load(f)

# =======================================================================
# ================= API PARA OBTENER DATOS DE SESIÓN ====================
# =======================================================================
@app.route('/api/session_info')
@login_required
def get_session_info():
    """
    Devuelve de forma segura la información del usuario actual en la sesión
    para que el frontend pueda adaptarse.
    """
    try:
        session_data = {
            "nombre_completo": session.get('nombre_completo'),
            "email": session.get('username'), # El username es el email
            "rol": session.get('rol'),
            "filtro_asociado": session.get('filtro_asociado')
        }
        return jsonify(session_data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
# ==============================================================================
# ======================== API PARA GESTIONAR USUARIOS (CRUD) ==================
# ==============================================================================

@app.route('/api/usuarios', methods=['GET'])
@login_required
@admin_required
def api_get_users():
    users, status_code = get_all_users_with_details()
    return jsonify(users), status_code

@app.route('/api/usuarios', methods=['POST'])
@login_required
@admin_required
def api_create_user():
    data = request.get_json()
    response, status_code = create_user(data)
    return jsonify(response), status_code

@app.route('/api/usuarios/<int:user_id>', methods=['GET'])
@login_required
@admin_required
def api_get_user(user_id):
    user, status_code = get_user_by_id(user_id)
    return jsonify(user), status_code

@app.route('/api/usuarios/<int:user_id>', methods=['PUT'])
@login_required
@admin_required
def api_update_user(user_id):
    data = request.get_json()
    response, status_code = update_user(user_id, data)
    return jsonify(response), status_code

@app.route('/api/usuarios/<int:user_id>', methods=['DELETE'])
@login_required
@admin_required
def api_delete_user(user_id):
    response, status_code = delete_user(user_id)
    return jsonify(response), status_code

# Esta ruta es para poblar el dropdown de roles en el modal de usuario
@app.route('/api/roles', methods=['GET'])
@login_required
@admin_required
def api_get_roles():
    # Reutilizamos la lógica de get_all_options para la tabla Roles
    # Asegúrate de que 'Roles' esté en la lista de tablas permitidas en opciones_proyecto_nuevo.py
    roles = get_all_options('Roles') 
    return jsonify(roles)

# ==============================================================================

# ==============================================================================
# ======================== API PARA GESTIONAR ROLES ============================
# ==============================================================================

@app.route('/api/roles_management', methods=['GET'])
@login_required
@admin_required
def api_get_roles_management():
    """Obtiene la lista de roles para la tabla de administración."""
    roles, status_code = get_all_roles()
    return jsonify(roles), status_code

@app.route('/api/roles_management/<int:role_id>', methods=['GET'])
@login_required
@admin_required
def api_get_role_permissions(role_id):
    """Obtiene los permisos de un rol para el modal de edición."""
    response, status_code = get_role_permissions(role_id)
    return jsonify(response), status_code

@app.route('/api/roles_management/<int:role_id>', methods=['PUT'])
@login_required
@admin_required
def api_update_role_permissions(role_id):
    """Actualiza los permisos de un rol."""
    data = request.get_json()
    response, status_code = update_role_permissions(role_id, data)
    return jsonify(response), status_code



# ===================================================================================
# ======================== API PARA GESTIONAR OPCIONES (CRUD) =======================
# ===================================================================================
@login_required
@app.route('/api/opciones/<string:table_name>', methods=['GET', 'POST'])
def options(table_name):
    """
    Ruta para OBTENER TODAS las opciones de una tabla (GET)
    o CREAR una nueva opción en esa tabla (POST).
    """
    if request.method == 'GET':
        try:
            # Llama a la función get_all_options del módulo de lógica
            options = get_all_options(table_name)
            return jsonify(options), 200
        except ValueError as e:
            return jsonify({"error": str(e)}), 400 # Tabla no permitida
        except Exception as e:
            return jsonify({"error": f"Error interno del servidor: {e}"}), 500

    if request.method == 'POST':
        data = request.get_json()
        # Llama a la función create_option
        new_option, error = create_option(table_name, data)
        if error:
            # Devuelve un error si el nombre falta, ya existe, o hay otro problema
            return jsonify({"error": error}), 400
        return jsonify(new_option), 201 # 201: Created

@login_required
@app.route('/api/opciones/<string:table_name>/<int:option_id>', methods=['GET', 'PUT', 'DELETE'])
def specific_option(table_name, option_id):
    """
    Ruta para ACTUALIZAR (PUT) o ELIMINAR (DELETE) una opción específica por su ID.
    """
    if request.method == 'GET':
        try:
            option = get_option_by_id(table_name, option_id)
            if option:
                return jsonify(option), 200
            else:
                return jsonify({"error": "Opción no encontrada."}), 404
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            return jsonify({"error": f"Error interno del servidor: {e}"}), 500
        
    if request.method == 'PUT':
        data = request.get_json()
        # Llama a la función update_option
        success, error = update_option(table_name, option_id, data)
        if error:
            return jsonify({"error": error}), 400
        if not success:
            return jsonify({"error": "Opción no encontrada."}), 404 # 404: Not Found
        return jsonify({"mensaje": "Opción actualizada con éxito."}), 200

    if request.method == 'DELETE':
        # Llama a la función delete_option
        success, error = delete_option(table_name, option_id)
        if error:
            return jsonify({"error": error}), 400
        if not success:
            return jsonify({"error": "Opción no encontrada."}), 404
        return jsonify({"mensaje": "Opción eliminada con éxito."}), 200
    
# ===================================================================================
# ======================== FIN API PARA GESTIONAR OPCIONES ==========================
# ===================================================================================

@login_required
@app.route('/proyectos')
def get_all_proyectos():
    try:
        # 1. El mesero (app.py) toma la orden (lee los parámetros del request)
        search_params = {
            'draw': request.args.get('draw', type=int),
            'start': request.args.get('start', type=int),
            'length': request.args.get('length', type=int),
            'sap': request.args.get('columns[0][search][value]', ''),
            'wf': request.args.get('columns[1][search][value]', ''),
            'descripcion': request.args.get('columns[2][search][value]', ''),
            'coordinador': request.args.get('columns[3][search][value]', ''),
            'contratista': request.args.get('columns[4][search][value]', ''),
            'estado': request.args.get('columns[5][search][value]', ''),
        }

        # 2. Le pasa la orden al cocinero (la función de lógica)
        proyectos_data = get_Proyectos(search_params)
        # DataTables espera un objeto con una clave "data"
        return jsonify(proyectos_data)
    except Exception as e:
        print(f"Error en la ruta /proyectos: {e}")
        # Es buena práctica devolver un error que DataTables pueda entender.
        draw = request.args.get('draw', 0, type=int)
        return jsonify({
            "error": str(e), 
            "data": [],
            "draw": draw,
            "recordsTotal": 0,
            "recordsFiltered": 0
        }), 500

@login_required
@app.route('/filter_options') # RUTA NUEVA
def get_filter_options():
    try:
        options_data = get_filter_options_data()
        return jsonify(options_data)
    except Exception as e:
        print(f"Error en la ruta /filter_options: {e}")
        return jsonify({}), 500

@login_required
@app.route('/proyectos_detalle/<path:sap_id>', methods=['GET', 'PUT'])
def get_proyecto_detalle(sap_id):
    """
    Ruta para obtener (GET) o actualizar (PUT) los detalles de un proyecto.
    """

    if request.method == 'GET':
        try:
            proyecto_data = get_proyecto_details(sap_id)
            if proyecto_data:
                return jsonify(proyecto_data)
            else:
                return jsonify({"error": "Proyecto no encontrado"}), 404
        except Exception as e:
            print(f"Error inesperado en GET /proyectos_detalle/{sap_id}: {e}")
            return jsonify({"error": "Error interno del servidor"}), 500
        
    if request.method == 'PUT':
        try:
            datos_actualizados = request.get_json()
            if not datos_actualizados:
                return jsonify({"error": "No se recibieron datos para actualizar"}), 400

            # Llama a la nueva función de lógica de actualización
            exito, mensaje = update_proyecto_details(sap_id, datos_actualizados, socketio)

            if exito:
                return jsonify({"mensaje": mensaje}), 200
            else:
                # Devuelve el mensaje de error específico (ej. "No encontrado" o "Error DB")
                return jsonify({"error": mensaje}), 500

        except Exception as e:
            print(f"Error inesperado en PUT /proyectos_detalle/{sap_id}: {e}")
            return jsonify({"error": "Error interno del servidor al actualizar"}), 500
        
@login_required
@app.route('/api/opciones/<string:table_name>/exportar_excel', methods=['GET'])
def export_options_to_excel(table_name):
    """
    Ruta para generar y descargar un archivo Excel con los datos de una tabla.
    """
    try:
        # Llama a la función de lógica para generar el archivo en memoria
        excel_buffer = export_table_to_excel(table_name)

        if excel_buffer is None:
            return jsonify({"error": "No hay datos para exportar."}), 404

        # Prepara un nombre de archivo único con la fecha y hora
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        filename = f"{table_name}_{timestamp}.xlsx"
        
        # Usa send_file para enviar el buffer como un archivo descargable
        return send_file(
            excel_buffer,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )

    except ValueError as e:
        return jsonify({"error": str(e)}), 400 # Tabla no permitida
    except Exception as e:
        print(f"Error al exportar a Excel: {e}")
        return jsonify({"error": f"Error interno del servidor: {e}"}), 500

@login_required    
@app.route('/etiquetas')
def get_etiquetas():
    # Aquí iría tu lógica para obtener las etiquetas de la base de datos
    # Por ahora, devolvemos una lista vacía para que no dé error 404
    return jsonify([])

@login_required
@app.route('/proyectos_filter')
def proyectos_filter_route():
    """
    API endpoint que devuelve la lista de proyectos (SAP y Nombre) 
    para el selector del dashboard.
    """
    try:
        # 1. Leemos el término de búsqueda 'q' que envía Select2 desde la URL.
        search_term = request.args.get('q', '')
        
        # 2. Pasamos el término de búsqueda a la función de lógica.
        lista_de_proyectos = get_proyectos_para_selector(search_term)
        
        return jsonify({"results": lista_de_proyectos})
    except Exception as e:
        print(f"Error en la ruta /proyectos_filter: {e}")
        return jsonify([]), 500

@app.route('/api/proyectos/<path:sap_id>/fechas', methods=['GET'])
@login_required
def get_fechas_proyecto_route(sap_id):
    """API para obtener las fechas clave de un proyecto."""
    fechas, status_code = get_fechas_proyecto(sap_id)
    return jsonify(fechas), status_code

###########################################################
#                #TAREAS                                  #
###########################################################
@login_required
@app.route('/proyectos/<path:sap_id>/tareas', methods=['GET'])
def get_tareas_route(sap_id):
    """API Endpoint para listar las tareas de un proyecto."""
    lista_tareas = get_tareas_por_proyecto(sap_id)
    return jsonify(lista_tareas)

@login_required
@app.route('/tareas/<int:id_tarea>/estado', methods=['PUT'])
def update_tarea_estado_route(id_tarea):
    """API Endpoint para actualizar el estado de una tarea (drag and drop)."""
    data = request.get_json()
    if not data or 'estado' not in data:
        return jsonify({"error": "Falta el nuevo estado"}), 400

    nuevo_estado = data['estado']
    exito, mensaje = actualizar_estado_tarea_proyecto(id_tarea, nuevo_estado)

    if exito:
        return jsonify({"mensaje": mensaje}), 200
    else:
        return jsonify({"error": mensaje}), 500

@login_required
@app.route('/tareas/<int:id_tarea>/checklist', methods=['GET'])
def get_checklist_route(id_tarea):
    """
    API Endpoint para obtener la checklist (subtareas) de una tarea específica.
    """
    try:
        # Llama a la función de lógica que está en tareas.py
        checklist = get_checklist_por_tarea(id_tarea)
        # Devuelve la lista de subtareas en formato JSON al frontend
        return jsonify(checklist)
    except Exception as e:
        print(f"Error en la ruta /tareas/{id_tarea}/checklist: {e}")
        return jsonify({"error": "No se pudo obtener la checklist"}), 500

@login_required    
@app.route('/tareas', methods=['POST'])
def crear_tarea_route():
    """API Endpoint para crear una nueva tarea."""
    datos_tarea = request.get_json()
    if not datos_tarea or not datos_tarea.get('nombre_tarea'):
        return jsonify({"error": "Faltan datos para crear la tarea"}), 400

    nueva_tarea = crear_nueva_tarea_proyecto(datos_tarea)

    if nueva_tarea:
        return jsonify(nueva_tarea), 201  # 201: Created
    else:
        return jsonify({"error": "No se pudo crear la tarea"}), 500

@login_required
@app.route('/api/todas_las_tareas', methods=['GET'])
def get_todas_las_tareas_route():
    """
    API Endpoint para listar TODAS las tareas para el Kanban global.
    Delega la lógica al módulo de tareas.
    """
    try:
        lista_tareas_global = get_todas_las_tareas()
        return jsonify(lista_tareas_global)
    except Exception as e:
        print(f"Error en la ruta /api/todas_las_tareas: {e}")
        return jsonify({"error": "No se pudieron obtener las tareas globales"}), 500

@login_required
@app.route('/api/tareas/<int:task_id>', methods=['DELETE'])
def delete_tarea_route(task_id):
    """ API para eliminar una tarea. """
    resultado, status_code = eliminar_tarea_por_id(task_id)
    return jsonify(resultado), status_code

@login_required
@app.route('/tareas/<int:id_tarea>', methods=['PUT'])
def update_tarea_route(id_tarea):
    """
    API para actualizar una tarea existente.
    """
    data = request.get_json()
    resultado, status_code = actualizar_tarea(id_tarea, data)
    return jsonify(resultado), status_code

@login_required
@app.route('/api/tareas/<int:id_tarea>/comentarios', methods=['POST'])
def add_comentario_route(id_tarea):
    data = request.get_json()
    resultado, status_code = agregar_comentario(id_tarea, data)
    return jsonify(resultado), status_code

@login_required
@app.route('/api/tareas/<int:id_tarea>/comentarios', methods=['GET'])
def get_comentarios_route(id_tarea):
    resultado, status = get_comentarios_por_tarea(id_tarea)
    return jsonify(resultado), status

@login_required
@app.route('/api/comentarios/<int:id_comentario>', methods=['PUT'])
def update_comentario_route(id_comentario):
    data = request.get_json()
    resultado, status = actualizar_comentario(id_comentario, data)
    return jsonify(resultado), status

@login_required
@app.route('/api/comentarios/<int:id_comentario>', methods=['DELETE'])
def delete_comentario_route(id_comentario):
    resultado, status = eliminar_comentario(id_comentario)
    return jsonify(resultado), status

###########################################################
#                #TAREAS                                  #
###########################################################



###########################################################
#                #MAPAS                                  #
###########################################################
"""@app.route("/maps")
def mapas():

    try:
        # 1. Obtener los límites desde la petición web
        bounds = {
            'north': request.args.get('north', type=float),
            'south': request.args.get('south', type=float),
            'east': request.args.get('east', type=float),
            'west': request.args.get('west', type=float)
        }
        if not all(bounds.values()):
            return jsonify([])

        categorias_str = request.args.get('categorias')
        categorias = categorias_str.split(',') if categorias_str else None

        contratistas_str = request.args.get('contratistas')
        contratistas = contratistas_str.split(',') if contratistas_str else None

        # 2. Llamar a la función auxiliar para obtener los datos puros
        proyectos_data = Creacion_mapas(bounds, categorias, contratistas)

        # 3. Convertir los datos puros en una respuesta JSON y devolverla
        return jsonify(proyectos_data)

    except Exception as e:
        print(f"Error en la ruta /maps: {e}")
        return jsonify({"error": str(e)}), 500


"""

@login_required
@app.route("/maps")
def mapas():
    try:
        # 1. Intenta obtener los límites. Si no vienen, se quedarán como None.
        north = request.args.get('north', type=float)
        south = request.args.get('south', type=float)
        east = request.args.get('east', type=float)
        west = request.args.get('west', type=float)
        
        bounds = None
        # Solo si TODOS los límites están presentes, se arma el diccionario.
        # Esto permite que la llamada sin parámetros para el buscador funcione.
        if all(v is not None for v in [north, south, east, west]):
            bounds = {
                'north': north,
                'south': south,
                'east': east,
                'west': west
            }

        # La lógica para categorías y contratistas se mantiene igual.
        categorias_str = request.args.get('categorias')
        categorias = categorias_str.split(',') if categorias_str else None

        contratistas_str = request.args.get('contratistas')
        contratistas = contratistas_str.split(',') if contratistas_str else None

        # 2. Llama a la función de lógica, pasándole los bounds (o None si no vinieron).
        proyectos_data = Creacion_mapas(bounds, categorias, contratistas)

        # 3. Devuelve el resultado en formato JSON.
        return jsonify(proyectos_data)

    except Exception as e:
        print(f"Error en la ruta /maps: {e}")
        return jsonify({"error": str(e)}), 500

@login_required
@app.route("/map/categories")
def get_map_categories():
    try:
        categorias = obtener_categorias_unicas()
        return jsonify(categorias)
    except Exception as e:
        print(f"Error en la ruta /map/categories: {e}")
        return jsonify({"error": str(e)}), 500

@login_required
@app.route("/map/contratista")
def get_map_contratista():
    try:
        contratistas = obtener_contratistas_unicos()
        return jsonify(contratistas)
    except Exception as e:
        print(f"Error en la ruta /map/contratista: {e}")
        return jsonify({"error": str(e)}), 500

@login_required    
@app.route("/search_data")
def search_data():
    """
    Esta ruta devuelve una lista de TODOS los proyectos con sus coordenadas
    para alimentar el control de búsqueda del frontend.
    """
    try:
        rutas_dict = rutas.convert_rutas()
        RUTA_DB = os.path.join(rutas_dict["ruta_script_python"], "mapa.db")

        with sqlite3.connect(RUTA_DB) as conn:
            # Traemos solo los datos necesarios: Sap y sus coordenadas
            query = """
                SELECT 
                    p.Sap,
                    c."P. Y" AS Latitud,
                    c."P. X" AS Longitud
                FROM Proyectos p
                JOIN Coordenadas c ON p.Sap = c.Sap
                WHERE c."P. Y" IS NOT NULL AND c."P. X" IS NOT NULL;
            """
            df_proyectos = pd.read_sql_query(query, conn)
        
        # Limpiamos los datos para asegurar que no haya nulos
        df_proyectos['Latitud'] = pd.to_numeric(df_proyectos['Latitud'], errors='coerce')
        df_proyectos['Longitud'] = pd.to_numeric(df_proyectos['Longitud'], errors='coerce')
        df_proyectos.dropna(subset=['Latitud', 'Longitud'], inplace=True)
        
        proyectos_json = df_proyectos.to_dict(orient='records')
        return jsonify(proyectos_json)

    except Exception as e:
        print(f"Error en la ruta /search_data: {e}")
        return jsonify({"error": str(e)}), 500

@login_required
@app.route('/data/<path:filename>')
def serve_data_file(filename):
    """
    Sirve de forma segura un archivo desde el directorio BBDD/FILES.
    """
    # Se asume que la carpeta BBDD está al mismo nivel que tu app.py
    rutas_dict = rutas.convert_rutas()
    RUTA_DB = os.path.join(rutas_dict["ruta_guardado_BBDD"])
    try:
        return send_from_directory(RUTA_DB, filename, as_attachment=False)
    except FileNotFoundError:
        abort(404)

###########################################################
#                #MAPAS                                  #
###########################################################


###########################################################
#                #CALENDARIO                              #
###########################################################

@login_required
@app.route("/calendario/eventos", methods=['GET'])
def calendario_eventos_route():
    try:
        # Los filtros ahora pueden ser listas separadas por comas
        filters = {
            'sap': request.args.get('sap', '').split(','),
            'coordinadores': request.args.get('coordinadores', '').split(','),
            'contratistas': request.args.get('contratistas', '').split(','),
            'lineas_de_negocio': request.args.get('lineas_de_negocio', '').split(',')
        }
        print("Filtros recibidos en la ruta de Flask:", filters)
        # Limpiamos los filtros que estén vacíos
        active_filters = {k: [v for v in v_list if v] for k, v_list in filters.items() if any(v_list)}
        
        eventos = get_eventos(active_filters)
        return jsonify(eventos)
    except Exception as e:
        print(f"Error en la ruta /calendario/eventos: {e}")
        return jsonify({"error": str(e)}), 500

@login_required
@app.route("/calendario/eventos", methods=['POST'])
def crear_evento_route():
    datos_evento = request.get_json()
    nuevo_id = crear_evento(datos_evento)
    if nuevo_id:
        return jsonify({"mensaje": "Evento creado", "id": nuevo_id}), 201
    return jsonify({"error": "No se pudo crear el evento"}), 500

@login_required
@app.route("/calendario/eventos/<int:evento_id>", methods=['PUT'])
def actualizar_evento_route(evento_id):
    datos_evento = request.get_json()
    exito = actualizar_evento(evento_id, datos_evento)
    if exito:
        return jsonify({"mensaje": "Evento actualizado"})
    return jsonify({"error": "No se pudo actualizar el evento"}), 500

@login_required
@app.route("/calendario/eventos/<int:evento_id>", methods=['DELETE'])
def eliminar_evento_route(evento_id):
    exito = eliminar_evento(evento_id)
    if exito:
        return jsonify({"mensaje": "Evento eliminado"})
    return jsonify({"error": "No se pudo eliminar el evento"}), 500

@login_required
@app.route("/calendario/eventos/<int:evento_id>/reprogramar", methods=['PUT'])
def reprogramar_evento_route(evento_id):
    """
    Ruta específica para manejar la reprogramación de un evento desde el modal de justificación.
    """
    try:
        datos_reprogramacion = request.get_json()
        if not datos_reprogramacion or not datos_reprogramacion.get('justificacion'):
            return jsonify({"error": "Falta la justificación para reprogramar"}), 400

        # Llamamos a la nueva función de lógica en calendario.py
        exito = reprogramar_evento(evento_id, datos_reprogramacion)

        if exito:
            return jsonify({"mensaje": "Evento reprogramado y historial actualizado con éxito"}), 200
        else:
            return jsonify({"error": "No se pudo completar la reprogramación en la base de datos"}), 500

    except Exception as e:
        print(f"Error en la ruta /reprogramar: {e}")
        return jsonify({"error": "Error interno del servidor"}), 500

@login_required 
@app.route('/brigadas')
def brigadas_route():
    try:
        brigadas = get_todas_las_brigadas()
        return jsonify(brigadas)
    except Exception as e:
        print(f"Error en la ruta /brigadas: {e}")
        return jsonify([]), 500

@login_required
@app.route('/api/tareas_para_calendario')
def get_tareas_para_calendario():
    # Aquí deberías añadir la lógica para obtener TODAS las tareas de tu base de datos
    # y devolverlas como un JSON.
    # Por ejemplo:
    #   from MODULES.PROYECTOS import tareas
    #   todas_las_tareas = tareas.get_todas_las_tareas() # Necesitarías crear esta función
    #   return jsonify(todas_las_tareas)
    
    # Como ejemplo, devolvemos datos de prueba:
    datos_de_prueba = [
        {"id_tarea": 1, "nombre_tarea": "Revisar planos eléctricos", "fecha_vencimiento": "2025-06-28", "prioridad": "Alta"},
        {"id_tarea": 2, "nombre_tarea": "Coordinar visita a terreno", "fecha_vencimiento": "2025-06-30", "prioridad": "Media"}
    ]
    return jsonify(datos_de_prueba)


@login_required
@app.route('/api/calendario/tipos_permiso_trabajo', methods=['GET'])
def get_tipos_permiso_route():
    """
    API para obtener la lista de todos los tipos de permisos de trabajo
    para poblar el dropdown en el modal de eventos.
    """
    try:
        tipos = get_tipos_permiso_trabajo()
        return jsonify(tipos), 200
    except Exception as e:
        print(f"Error en /api/calendario/tipos_permiso_trabajo: {e}")
        return jsonify({"error": "Error interno del servidor"}), 500

@login_required
@app.route('/api/calendario/permisos/<int:permiso_id>/confirmar', methods=['POST'])
def confirmar_permiso_route(permiso_id):
    """
    API para marcar un permiso de trabajo como 'Confirmado'.
    """
    try:
        # Podrías obtener el usuario de la sesión para registrar quién confirmó
        usuario = session.get('nombre_completo', 'Usuario Sistema')
        exito, mensaje = confirmar_permiso_trabajo(permiso_id, usuario)
        if exito:
            return jsonify({"mensaje": mensaje}), 200
        else:
            return jsonify({"error": mensaje}), 400
    except Exception as e:
        print(f"Error en /api/calendario/permisos/{permiso_id}/confirmar: {e}")
        return jsonify({"error": "Error interno del servidor"}), 500

@app.route('/api/calendario/permisos/<int:permiso_id>', methods=['DELETE'])
@login_required
def eliminar_permiso_route(permiso_id):
    """
    API para eliminar un permiso de trabajo.
    """
    try:
        usuario = session.get('nombre_completo', 'Usuario Sistema')
        exito, mensaje = eliminar_permiso_trabajo(permiso_id, usuario)
        if exito:
            return jsonify({"mensaje": mensaje}), 200
        else:
            return jsonify({"error": mensaje}), 404
    except Exception as e:
        print(f"Error en /api/calendario/permisos/{permiso_id}: {e}")
        return jsonify({"error": "Error interno del servidor"}), 500

###########################################################
#                #CALENDARIO                              #
###########################################################

###########################################################
#                #DOCUMENTOS                              #
###########################################################

@login_required
@app.route('/proyectos/<path:sap_id>/documentos', methods=['GET'])
def get_documentos_route(sap_id):
    """API para listar los documentos de un proyecto."""
    docs = listar_documentos(sap_id)
    return jsonify(docs)

@login_required
@app.route('/proyectos/<path:sap_id>/documentos', methods=['POST'])
def upload_documentos_route(sap_id):
    """API para subir nuevos documentos y un comentario asociado."""

    print(f"--- DEBUG EN app.py ---")
    print(f"Contenido de request.files: {request.files}")

    # ======================================================================
    # SOLUCIÓN: Extracción manual de archivos para evitar el bug de getlist
    # ======================================================================
    # En lugar de: files = request.files.getlist('file') que devuelve [], usamos esto:
    files = [v for k, v in request.files.items() if k.startswith('file[')]
    # ======================================================================

    print(f"Resultado de la extracción manual: {files}")

    # La validación ahora debe ser sobre la lista obtenida
    if not files:
        print("ERROR: La lista 'files' está vacía. La petición no será procesada.")
        return jsonify({"error": "No se encontraron archivos en la petición"}), 400

    comentario = request.form.get('comentario')
    print(f"Archivos recibidos: {len(files)}")
    print(f"Comentario recibido: '{comentario}'")
    print(f"-----------------------")

    exito, mensaje = subir_documentos(sap_id, files, comentario)
    
    if exito:
        # Devuelve los documentos recién creados para actualizar la UI dinámicamente
        return jsonify({"success": True, "documentos": mensaje}), 201
    else:
        return jsonify({"success": False, "message": mensaje}), 500

@login_required
@app.route('/documentos/<int:id_documento>', methods=['DELETE'])
def delete_documento_route(id_documento):
    """API para eliminar un documento."""
    exito, mensaje = eliminar_documento(id_documento)
    if exito:
        return jsonify({"mensaje": mensaje}), 200
    else:
        return jsonify({"error": mensaje}), 500

@login_required
@app.route('/api/tareas/upload_adjunto', methods=['POST'])
def upload_adjunto_tarea_route():
    """
    API para subir archivos adjuntos desde el modal de una tarea.
    """
    if 'file' not in request.files:
        return jsonify({"error": "No se encontró el archivo"}), 400

    # Dropzone envía el id_tarea como un campo de formulario
    id_tarea = request.form.get('task_id')
    if not id_tarea:
        return jsonify({"error": "No se especificó el ID de la tarea"}), 400

    files = request.files.getlist('file')

    exito, mensaje = subir_adjunto_para_tarea(int(id_tarea), files)

    if exito:
        return jsonify({"mensaje": mensaje}), 201
    else:
        return jsonify({"error": mensaje}), 500

@login_required
@app.route('/api/tareas/<int:id_tarea>/adjuntos')
def get_adjuntos_tarea_route(id_tarea):
    adjuntos = listar_adjuntos_por_tarea(id_tarea)
    return jsonify(adjuntos)

@login_required
@app.route('/descarga/<int:id_documento>')
def download_file_route(id_documento):
    """
    Ruta para descargar un archivo de forma segura.
    """
    # 1. Buscamos el documento en la base de datos
    documento = get_documento_por_id(id_documento)

    if not documento:
        return "Archivo no encontrado.", 404

    path_completo, nombre_original = documento

    # 2. Extraemos el directorio y el nombre del archivo de la ruta completa
    directorio = os.path.dirname(path_completo)
    nombre_archivo = os.path.basename(path_completo)

    try:
        # 3. Usamos send_from_directory para enviar el archivo de forma segura
        # 'as_attachment=True' hace que el navegador lo descargue en lugar de mostrarlo.
        return send_from_directory(directory=directorio, path=nombre_archivo, as_attachment=True, download_name=nombre_original)
    except FileNotFoundError:
        return "Archivo no encontrado en el servidor.", 404

###########################################################
#                #DOCUMENTOS                              #
###########################################################

# ===================================================================================
# =========================== API PARA MATRIZ DE RIESGO =============================
# ===================================================================================

@login_required
@app.route('/api/proyecto/<path:sap_proyecto>/riesgos', methods=['GET'])
def api_get_riesgos(sap_proyecto):
    # Esta función ahora devuelve una lista de diccionarios (gracias a la Corrección 1)
    riesgos_data = obtener_riesgos_por_proyecto(sap_proyecto) 
    
    # jsonify convierte la lista en una respuesta JSON válida que el frontend espera.
    # Este código ya estaba bien, pero ahora recibirá los datos correctos.
    return jsonify(riesgos_data) 

@login_required
@app.route('/api/riesgos/<int:id_riesgo>', methods=['GET'])
def api_get_single_riesgo(id_riesgo):
    """
    Endpoint para obtener los datos de un único riesgo por su ID.
    Esta es la ruta que tu JavaScript está intentando llamar.
    """
    # Llama a la función de lógica en matrizriesgo.py y retorna su respuesta.
    return obtener_riesgo_por_id(id_riesgo)

@login_required
@app.route('/api/riesgos', methods=['POST'])
def api_create_riesgo():
    """
    Endpoint para crear un nuevo riesgo/oportunidad.
    """
    datos = request.get_json()
    if not datos:
        return jsonify({'error': 'No se recibieron datos'}), 400
    return crear_riesgo(datos)

@login_required
@app.route('/api/riesgos/<int:id_riesgo>', methods=['PUT'])
def api_update_riesgo(id_riesgo):
    """
    Endpoint para actualizar un riesgo/oportunidad existente.
    """
    datos = request.get_json()
    if not datos:
        return jsonify({'error': 'No se recibieron datos'}), 400
    return actualizar_riesgo(id_riesgo, datos)

@login_required
@app.route('/api/riesgos/<int:id_riesgo>', methods=['DELETE'])
def api_delete_riesgo(id_riesgo):
    """
    Endpoint para eliminar un riesgo/oportunidad.
    """
    return eliminar_riesgo(id_riesgo)

# ===================================================================================
# =========================== API PARA MATRIZ DE RIESGO =============================
# ===================================================================================

# ===================================================================================
# =========================== API PARA GANTT =============================
# ===================================================================================
@login_required
@app.route('/api/proyectos/<path:sap_id>/gantt', methods=['GET'])
def get_gantt_tasks_route(sap_id):
    """
    Endpoint para obtener las tareas del Gantt para un proyecto específico.
    """
    try:
        tasks = get_gantt_por_proyecto(sap_id)
        return jsonify(tasks)
    except Exception as e:
        print(f"Error en la ruta /api/proyectos/<path:sap_id>/gantt: {e}")
        return jsonify([]), 500

@login_required
@app.route('/api/gantt', methods=['POST'])
def create_gantt_tasks_batch_route():
    """
    Endpoint para crear múltiples tareas de Gantt desde una lista.
    """
    task_data = request.get_json()
    if not task_data:
        return jsonify({"action": "error", "message": "No se recibieron datos de la tarea"}), 400

    # El 'sap_id' fue añadido en el frontend por el dataProcessor
    if 'sap_id' not in task_data:
        return jsonify({"action": "error", "message": "El sap_id del proyecto es requerido"}), 400
    
    exito, resultado = crear_gantt_task(task_data)

    if exito:
        # RESPUESTA EXITOSA: dhtmlxGantt espera este formato para confirmar la creación.
        # 'tid' es el nuevo ID de la tarea en la base de datos.
        return jsonify({"action": "inserted", "tid": resultado}), 201
    else:
        # RESPUESTA DE ERROR: dhtmlxGantt también entiende este formato.
        return jsonify({"action": "error", "message": resultado}), 500

@login_required
@app.route('/api/gantt/batch_delete', methods=['DELETE'])
def delete_gantt_tasks_batch_route():
    data = request.get_json()

    if not isinstance(data, dict) or 'ids' not in data:
        return jsonify({"error": "Formato de JSON inválido. Se esperaba un objeto con la clave 'ids'."}), 400
    
    task_ids = data['ids']
    if not isinstance(task_ids, list):
        return jsonify({"error": "La clave 'ids' debe contener una lista de IDs de tareas."}), 400
    
    exito, mensaje = eliminar_gantt_batch(task_ids)

    if exito:
        return jsonify({"mensaje": mensaje}), 200
    else:
        return jsonify({"error": mensaje}), 500

@login_required    
@app.route('/api/gantt/<int:task_id>', methods=['PUT'])
def update_gantt_task_route(task_id):
    """ API para actualizar una tarea existente. """
    data = request.get_json()
    if not data:
        return jsonify({"action": "error", "message": "No se recibieron datos"}), 400

    exito, mensaje = actualizar_gantt_task(task_id, data)
    
    if exito:
        return jsonify({"action": "updated"})
    else:
        return jsonify({"action": "error", "message": mensaje})

# =======================================================
# RUTAS API PARA DEPENDENCIAS (LINKS)
# =======================================================

@login_required
@app.route('/api/gantt_link', methods=['POST'])
def create_gantt_link_route():
    """ Crea una nueva dependencia entre tareas. """
    data = request.get_json()
    exito, resultado = crear_gantt_link(data)
    if exito:
        # Devuelve el nuevo ID como 'tid' para que Gantt lo reconozca
        return jsonify({"action": "inserted", "tid": resultado}), 201
    else:
        return jsonify({"action": "error", "message": resultado}), 500

@login_required
@app.route('/api/gantt_link/<int:link_id>', methods=['PUT'])
def update_gantt_link_route(link_id):
    """ Actualiza una dependencia existente. """
    data = request.get_json()
    exito, mensaje = actualizar_gantt_link(link_id, data)
    if exito:
        return jsonify({"action": "updated"})
    else:
        return jsonify({"action": "error", "message": mensaje}), 500

@login_required
@app.route('/api/gantt_link/<int:link_id>', methods=['DELETE'])
def delete_gantt_link_route(link_id):
    """ Elimina una dependencia. """
    exito, mensaje = eliminar_gantt_link(link_id)
    if exito:
        return jsonify({"action": "deleted"})
    else:
        return jsonify({"action": "error", "message": mensaje}), 500


# ===================================================================================
# =========================== API PARA GANTT =============================
# ===================================================================================

# ===================================================================================
# =========================== API PARA BENEFICIARIOS ================================
# ===================================================================================

@login_required
@app.route('/api/proyectos/<path:sap_id>/beneficiarios', methods=['GET'])
def api_get_beneficiarios(sap_id):
    """Obtiene todos los beneficiarios para un proyecto específico."""
    beneficiarios, status_code = get_beneficiarios_por_proyecto(sap_id)
    # DataTables espera los datos dentro de una clave "data"
    return jsonify({"data": beneficiarios}), status_code

@login_required
@app.route('/api/beneficiarios', methods=['POST'])
def api_create_beneficiario():
    """Crea un nuevo beneficiario."""
    data = request.get_json()
    response, status_code = create_beneficiario(data)
    return jsonify(response), status_code

@login_required
@app.route('/api/beneficiarios/<int:beneficiario_id>', methods=['PUT'])
def api_update_beneficiario(beneficiario_id):
    """Actualiza un beneficiario existente."""
    data = request.get_json()
    response, status_code = update_beneficiario(beneficiario_id, data)
    return jsonify(response), status_code

@login_required
@app.route('/api/beneficiarios/<int:beneficiario_id>', methods=['DELETE'])
def api_delete_beneficiario(beneficiario_id):
    """Elimina un beneficiario."""
    response, status_code = delete_beneficiario(beneficiario_id)
    return jsonify(response), status_code

@login_required
@app.route('/api/proyectos/<path:sap_id>/beneficiarios/upload', methods=['POST'])
def api_upload_beneficiarios(sap_id):
    """Sube y procesa un archivo Excel o CSV para poblar la tabla de beneficiarios."""
    if 'file' not in request.files:
        return jsonify({"error": "No se encontró el archivo en la petición"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No se seleccionó ningún archivo"}), 400

    response, status_code = upload_beneficiarios_from_file(sap_id, file)
    return jsonify(response), status_code

@login_required
@app.route('/api/proyectos/<path:sap_id>/beneficiarios/download', methods=['GET'])
def api_download_beneficiarios(sap_id):
    """Descarga los beneficiarios de un proyecto en un archivo Excel."""
    try:
        excel_buffer = download_beneficiarios_as_excel(sap_id)
        
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        filename = f"Beneficiarios_{sap_id}_{timestamp}.xlsx"
        
        return send_file(
            excel_buffer,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        print(f"Error al descargar Excel de beneficiarios: {e}")
        return jsonify({"error": str(e)}), 500

# ===================================================================================
# =========================== API PARA BENEFICIARIOS ================================
# ===================================================================================



# ===================================================================================
# =========================== API DASHBOARD =============================
# ===================================================================================


# =========================== FINANCIERO GENERAL =============================
@login_required
@app.route('/api/dashboard/avance_financiero')
def get_avance_financiero_route():
    datos, status = get_avance_financiero_general()
    return jsonify(datos), status

# =========================== FISICO GENERAL =============================
@login_required
@app.route('/api/dashboard/avance_fisico')
def get_avance_fisico_route():
    datos, status = get_avance_fisico_general()
    return jsonify(datos), status

# =========================== TARJETAS GENERAL =============================
@login_required
@app.route('/api/dashboard/detalle_proyecto/<path:sap_id>')
def get_detalle_dashboard_proyecto_route(sap_id):
    """
    API para obtener los detalles de un proyecto para la tarjeta del dashboard.
    """
    datos, status_code = get_detalle_dashboard_proyecto(sap_id)
    return jsonify(datos), status_code


@login_required
@socketio.on("workflow")
def handle_workflow(message):
    texto = message.get("datos")
    modulos = message.get("modulos", {})
    browser = None
    # 1. Limpiar llaves
    texto_limpio = texto.strip("{}")
    # 2. Separar por coma
    Data = [x.strip() for x in texto_limpio.split(",") if x.strip()]

    url_reporte = "https://frontel.sharepoint.com/sites/valoriza/SitePages/ReporteDetalle_SPBox.aspx?Proyecto=31884"
    rutas_dict = rutas.convert_rutas()
    excel, libro, Hoja_norma = obtener_libro_abierto("Panel.xlsm")
    DOWNLOAD_DIR = rutas_dict['ruta_guardado_BBDD']

    if (modulos.get('norma_liquidacion') or
            modulos.get('presupuesto') or
            modulos.get('cambio_nombre') or
            modulos.get('programa') or
            modulos.get('clase_proyecto') or
            modulos.get('zonal')):

        session = Sap.iniciar_sesion_gui()

    #MODULOS SAP
    if modulos.get('norma_liquidacion'):
        CN47N(session,Data, DOWNLOAD_DIR)

    if modulos.get('valoriza'):
        credenciales = message.get("datos_login")
        correo_login = credenciales.get('correo')
        password_login = credenciales.get('contraseña')
        page,browser = esperar_login(url_reporte,correo_login,password_login)

    for sap in Data:
        if modulos.get('valoriza'):
            url_valoriza = valoriza(sap)
            Nombre_Obra, Workflow, DetallePresupuesto, TotalManoObra = Scrapping_valoriza(page, url_valoriza)
            escribir_panel_obras(sap, Nombre_Obra, Workflow, DetallePresupuesto, TotalManoObra)
        if modulos.get('presupuesto'):
            cpresupuesto(session,sap)
            print(f"-> Ejecutando: C. Presupuesto...")
        
        if modulos.get('cambio_nombre'):
            cambio_nombre(session, sap)

        if modulos.get('programa'):
            Programa(session, sap)

        if modulos.get('norma_liquidacion'):
            norma_liquidacion_sap(session,sap)

        if modulos.get('clase_proyecto'):
            cambio_claseproyecto(session,sap)
        
        if modulos.get('zonal'):
            cambio_de_zonal(session,sap)

    if browser:
        browser.close()

    try:
        libro.save()
    except Exception as e:
        print(f"ERROR: No se pudo guardar el libro de Excel.")
        print(f"Razón técnica: {e}")

def listar_etiquetas(page):
    elementos = page.evaluate("""
        () => {
            return Array.from(document.querySelectorAll('*')).map(el => {
                return {
                    tag: el.tagName.toLowerCase(),
                    class: el.className,
                    text: el.innerText.trim()
                }
            }).filter(e => e.text || e.class); // solo mostrar si hay texto o clases
        }
    """)

    for i, el in enumerate(elementos):
        print(f"{i+1}. <{el['tag']}>")
        if el['class']:
            print(f"   └─ Clase(s): {el['class']}")
        if el['text']:
            print(f"   └─ Texto: {el['text']}")
        print()

def abrir_navegador():
    webbrowser.open_new("http://127.0.0.1:5000")

def job_revisar_tareas():
    """Función que será ejecutada por el planificador."""
    print(f"[{datetime.now()}] Ejecutando tarea programada: Revisando vencimiento de tareas...")
    with app.app_context():
        # Pasamos la instancia de socketio a la función de lógica
        revisar_tareas_proximas_a_vencer(socketio)

# Configura el planificador para que ejecute la tarea todos los días a las 9 AM
scheduler = BackgroundScheduler(daemon=True)
scheduler.add_job(job_revisar_tareas, 'cron', hour=9)
scheduler.start()

if __name__ == '__main__':
    print("--- Actualizando la base de datos desde Excel al iniciar... ---")
    #crear_base_de_datos_final_conversarDB()
    #crear_usuario_admin()
    print("--- Base de datos lista. ---")

    threading.Thread(target=lambda: (time.sleep(1.5), abrir_navegador())).start()
    socketio.run(app, debug=True, port=5000, use_reloader=False)

