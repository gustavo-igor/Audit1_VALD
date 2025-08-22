import sqlite3
import os

#ejecutar el comando en consola
#python -m MODULES.SQLITE.CONTROLLER.database_setup
def configurar_base_de_datos():
    """
    Crea o recrea el esquema completo de la base de datos, incluyendo las tablas
    para la trazabilidad de eventos del calendario.

    Esta función borrará las tablas existentes para asegurar un esquema limpio.
    """
    print("--- 🚀 Iniciando configuración del esquema de la base de datos ---")
    conn = None  # Inicializamos la conexión como nula para el bloque finally
    try:
        # --- 1. CONEXIÓN A LA BASE DE DATOS ---
        # Obtenemos la ruta de la base de datos de forma dinámica
        from MODULES.rutas import convert_rutas
        rutas_dict = convert_rutas()
        ruta_db = os.path.join(rutas_dict["ruta_script_python"],"mapa.db")
        print(f"🗄️  Conectando a la base de datos en: {ruta_db}")
        
        conn = sqlite3.connect(ruta_db)
        cursor = conn.cursor()

        # --- 2. DEFINICIÓN DEL ESQUEMA SQL ---
        # Aquí definimos todo el código SQL para crear las tablas.
        # Dentro de tu archivo database_setup.py

        #DROP TABLE IF EXISTS Comentarios;
        #DROP TABLE IF EXISTS ChecklistItems;
        #DROP TABLE IF EXISTS Tareas;
        #DROP TABLE IF EXISTS EventoHistorial;
        #DROP TABLE IF EXISTS Brigada;
        #DROP TABLE IF EXISTS EventoBrigada;
        #DROP TABLE IF EXISTS EventoCalendario;
        #DROP TABLE IF EXISTS Documentos;
        sql_schema = """
        -- Borramos las tablas en orden inverso a su creación para evitar errores de dependencias.
        
        CREATE TABLE Budget (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sap_proyecto TEXT NOT NULL,
            periodo INTEGER NOT NULL,
            outlook TEXT NOT NULL,
            fecha DATE,
            tipo_avance TEXT NOT NULL,
            valor_monetario REAL,
            valor_porcentual REAL,
            valor_fecha DATE,
            FOREIGN KEY (sap_proyecto) REFERENCES Proyectos (Sap) ON DELETE CASCADE
        );

        CREATE TABLE CREATE TABLE Gantt_Tareas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sap_proyecto TEXT NOT NULL,
            texto TEXT NOT NULL,
            fecha_inicio DATETIME NOT NULL,
            fecha_fin DATETIME NOT NULL,
            duracion INTEGER NOT NULL,
            progreso INTEGER NOT NULL DEFAULT 0 CHECK(progreso >= 0 AND progreso <= 100),
            parent INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (sap_proyecto) REFERENCES Proyectos (Sap) ON DELETE CASCADE
    
        );

        CREATE TABLE Gantt_Links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source INTEGER NOT NULL,
            target INTEGER NOT NULL,
            type TEXT NOT NULL
        );

        CREATE TABLE MatrizRiesgo (
            id_riesgo INTEGER PRIMARY KEY AUTOINCREMENT,
            sap_proyecto TEXT NOT NULL,
            clasificacion TEXT NOT NULL, -- 'Riesgo' o 'Oportunidad'
            descripcion_riesgo TEXT NOT NULL,
            comentario_descripcion TEXT,
            proceso TEXT,
            probabilidad INTEGER,
            impacto INTEGER,
            acciones_mitigacion TEXT,
            responsable_area TEXT,
            responsable_nombre TEXT,
            costo_acciones REAL, -- Usamos REAL para valores monetarios
            fecha_implementacion TEXT, -- Formato 'YYYY-MM-DD'
            estado TEXT,
            comentarios_generales TEXT,
            FOREIGN KEY (sap_proyecto) REFERENCES Proyectos (Sap) ON DELETE CASCADE
        );

        -- Tabla para las Tareas de los proyectos
        CREATE TABLE Tareas (
            id_tarea INTEGER PRIMARY KEY AUTOINCREMENT,
            Sap TEXT NOT NULL,
            nombre_tarea TEXT NOT NULL,
            PT TEXT,
            brigada TEXT,
            descripcion TEXT,
            estado TEXT DEFAULT 'Pendiente',
            prioridad TEXT,
            coordinador TEXT,
            contratista TEXT,
            etiqueta TEXT,
            fecha_creacion TEXT,
            fecha_modificacion TEXT,
            fecha_vencimiento TEXT
        );

        CREATE TABLE Brigada (
            id_brigada INTEGER PRIMARY KEY AUTOINCREMENT,
            brigada TEXT NOT NULL,
            contratista TEXT
        );

        -- Tabla Principal de Eventos del Calendario
        CREATE TABLE EventoCalendario (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sap TEXT,
            titulo TEXT NOT NULL,
            tipo_evento TEXT,
            fecha_inicio TEXT NOT NULL,
            fecha_fin TEXT NOT NULL,
            estado TEXT,
            coordinador TEXT,
            contratista TEXT,
            notas TEXT,
            creado_por TEXT,
            creado_en TEXT,
            modificado_por TEXT,
            modificado_en TEXT
        );

        -- Tabla para los ítems de un checklist asociado a una Tarea
        CREATE TABLE ChecklistItems (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_tarea INTEGER NOT NULL,
            texto_item TEXT NOT NULL,
            completado INTEGER NOT NULL DEFAULT 0, -- 0 para falso, 1 para verdadero
            FOREIGN KEY (id_tarea) REFERENCES Tarea (id_tarea) ON DELETE CASCADE
        );

        -- Tabla para los comentarios asociados a una Tarea
        CREATE TABLE Comentarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tarea_id INTEGER NOT NULL,
            autor TEXT NOT NULL,
            texto_comentario TEXT NOT NULL,
            fecha_creacion TEXT,
            FOREIGN KEY (tarea_id) REFERENCES Tarea (id_tarea) ON DELETE CASCADE
        );

        -- Tabla de Unión para la relación Muchos-a-Muchos entre Eventos y Brigadas
        CREATE TABLE EventoBrigada (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            evento_id INTEGER NOT NULL,
            brigada_id INTEGER NOT NULL,
            FOREIGN KEY (evento_id) REFERENCES EventoCalendario (id) ON DELETE CASCADE,
            FOREIGN KEY (brigada_id) REFERENCES Brigada (id) ON DELETE CASCADE
        );

        -- Tabla de Historial para Trazabilidad Completa de Eventos
        CREATE TABLE EventoHistorial (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            evento_id INTEGER NOT NULL,
            usuario_accion TEXT NOT NULL,
            fecha_accion TEXT NOT NULL,
            tipo_accion TEXT NOT NULL, -- Ej: 'CREACION', 'REPROGRAMACION', 'COMENTARIO'
            descripcion TEXT,
            datos_anteriores TEXT,
            FOREIGN KEY (evento_id) REFERENCES EventoCalendario (id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS Documentos (
            id_documento INTEGER PRIMARY KEY AUTOINCREMENT,
            sap_id TEXT NOT NULL,
            id_tarea INTEGER,
            nombre_archivo TEXT NOT NULL,
            path_archivo TEXT NOT NULL,
            comentario TEXT,
            usuario_subida TEXT,
            fecha_subida TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE Estados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre VARCHAR(255) NOT NULL UNIQUE
        );

        -- Tabla para los coordinadores
        CREATE TABLE Coordinadores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre VARCHAR(255) NOT NULL UNIQUE
        );

        -- Tabla para las empresas contratistas
        CREATE TABLE Contratista (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre VARCHAR(255) NOT NULL UNIQUE
        );

        -- Tabla para las unidades de negocio
        CREATE TABLE Unidades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre VARCHAR(255) NOT NULL UNIQUE
        );

        -- Tabla para las líneas de negocio
        CREATE TABLE Lineas_negocio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre VARCHAR(255) NOT NULL UNIQUE
        );

        -- Tabla para las comunas
        CREATE TABLE Comunas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre VARCHAR(255) NOT NULL UNIQUE
        );

        -- Tabla para los roles
        CREATE TABLE Roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_rol TEXT NOT NULL UNIQUE,
            permisos TEXT NOT NULL -- Guardará una lista de módulos permitidos, ej: "dashboard,mapa,proyectos"
        );

        CREATE TABLE Usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            nombre_completo TEXT NOT NULL,
            contratista TEXT, -- Se vincula con el nombre en la tabla Contratista
            estado TEXT NOT NULL DEFAULT 'activo', -- Puede ser 'activo' o 'inactivo'
            role_id INTEGER,
            FOREIGN KEY (role_id) REFERENCES Roles(id)
        );

        CREATE TABLE Fechas (
            Sap TEXT PRIMARY KEY,
            "Fecha emision OT" TEXT,
            "Fecha estimada de Inicio" TEXT,
            "Fecha estimada de Termino de Obras" TEXT,
            "Fecha solicitud PP" TEXT,
            "Fecha Adjudicacion" TEXT,
            "Fecha Empresa" TEXT,
            "Fecha PS Real" TEXT,
            "Fecha plano finiquito" TEXT,
            "Fecha Envio CTEC" TEXT,
            "Fecha Cierre CTEC" TEXT,
            "Fecha notificación al correo" TEXT,
            "Fecha notificación al cliente" TEXT,
            "Fecha Pago Cliente" TEXT,
            FOREIGN KEY (Sap) REFERENCES Proyectos(Sap)
        );

        CREATE TABLE Notificaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,          -- A quién va dirigida la notificación
            mensaje TEXT NOT NULL,                -- El texto que se mostrará
            leido INTEGER NOT NULL DEFAULT 0,     -- 0 para no leído, 1 para leído
            tipo TEXT NOT NULL,                   -- 'proyecto' o 'tarea' para saber a dónde redirigir
            referencia_id TEXT NOT NULL,          -- El SAP del proyecto o el ID de la tarea
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (usuario_id) REFERENCES Usuarios(id)
        );

        CREATE TABLE IF NOT EXISTS TipoPermisoTrabajo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE,
            plazo_limite_dias INTEGER NOT NULL, -- Plazo para que esté "En Plazo"
            plazo_advertencia_dias INTEGER NOT NULL -- Días extra para la advertencia
        );

        CREATE TABLE IF NOT EXISTS EventoPermisoTrabajo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            evento_id INTEGER NOT NULL,
            tipo_permiso_id INTEGER NOT NULL,
            -- Estado del permiso: Pendiente, Confirmado
            estado_confirmacion TEXT NOT NULL DEFAULT 'Pendiente',
            -- Estado del plazo: En Plazo, Fuera de Plazo, N/A (si ya está confirmado)
            estado_plazo TEXT NOT NULL DEFAULT 'En Plazo',
            fecha_solicitud TEXT, -- Fecha en que se solicita el permiso
            fecha_confirmacion TEXT, -- Fecha en que el usuario lo marca como "Confirmado"
            fecha_vencimiento_plazo TEXT, -- Fecha límite calculada para estar "En Plazo"
            creado_en TEXT NOT NULL,
            modificado_en TEXT,
            FOREIGN KEY (evento_id) REFERENCES EventoCalendario(id) ON DELETE CASCADE,
            FOREIGN KEY (tipo_permiso_id) REFERENCES TipoPermisoTrabajo(id) ON DELETE RESTRICT
        );

        CREATE TABLE IF NOT EXISTS Beneficiarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sap_id TEXT NOT NULL,
            numero_beneficiario TEXT,
            nombre_completo TEXT NOT NULL,
            rut TEXT,
            instalacion_interior TEXT DEFAULT 'N/A' CHECK(instalacion_interior IN ('Construida', 'Pendiente', 'N/A')),
            lbt TEXT DEFAULT 'N/A' CHECK(lbt IN ('Construida', 'Pendiente', 'N/A')),
            lmt TEXT DEFAULT 'N/A' CHECK(lmt IN ('Construida', 'Pendiente', 'N/A')),
            empalme TEXT DEFAULT 'N/A' CHECK(empalme IN ('Construida', 'Pendiente', 'N/A')),
            aumento_potencia TEXT DEFAULT 'N/A' CHECK(aumento_potencia IN ('Si', 'No', 'N/A')),
            servidumbre TEXT DEFAULT 'N/A' CHECK(servidumbre IN ('Si', 'No','N/A')),
            comentario_servidumbre TEXT,
            FOREIGN KEY (sap_id) REFERENCES Proyectos(Sap) ON DELETE CASCADE
        );

        CREATE TABLE Proyectos (
            Unidad TEXT, 
            Línea de Negocio TEXT, 
            Comuna TEXT, 
            Sector Urbano o Rural TEXT,
            WF SCM TEXT, 
            WF TEXT, 
            Sap TEXT PRIMARY KEY NOT NULL, 
            Valoriza TEXT,
            Programa de inversión TEXT, 
            N° ID TEXT, 
            ID TEXT, 
            ID Posicion TEXT,
            Descripción TEXT, 
            Tipo inversion TEXT, 
            Coordinador TEXT, 
            Contratista TEXT,
            Empresa TEXT, 
            Estado TEXT, 
            OBSERVACION TEXT
        );


        -- Índices para acelerar las búsquedas comunes
        CREATE INDEX idx_eventocalendario_fechas ON EventoCalendario(fecha_inicio, fecha_fin);
        CREATE INDEX idx_eventohistorial_evento_id ON EventoHistorial(evento_id);
        CREATE INDEX idx_eventobrigada_evento_id ON EventoBrigada(evento_id);
        """

        sql2 = """CREATE TABLE IF NOT EXISTS Beneficiarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sap_id TEXT NOT NULL,
            numero_beneficiario TEXT,
            nombre_completo TEXT NOT NULL,
            rut TEXT,
            instalacion_interior TEXT DEFAULT 'N/A' CHECK(instalacion_interior IN ('Construida', 'Pendiente', 'N/A')),
            lbt TEXT DEFAULT 'N/A' CHECK(lbt IN ('Construida', 'Pendiente', 'N/A')),
            lmt TEXT DEFAULT 'N/A' CHECK(lmt IN ('Construida', 'Pendiente', 'N/A')),
            empalme TEXT DEFAULT 'N/A' CHECK(empalme IN ('Construida', 'Pendiente', 'N/A')),
            aumento_potencia TEXT DEFAULT 'N/A' CHECK(aumento_potencia IN ('Si', 'No', 'N/A')),
            servidumbre TEXT DEFAULT 'N/A' CHECK(servidumbre IN ('Si', 'No','N/A')),
            comentario_servidumbre TEXT,
            FOREIGN KEY (sap_id) REFERENCES Proyectos(Sap) ON DELETE CASCADE
        );
        """

        # --- 3. EJECUCIÓN DEL SCRIPT SQL ---
        print("⚙️  Ejecutando script para crear/recrear tablas...")
        cursor.executescript(sql2)
        print("✅ Tablas creadas y configuradas exitosamente.")

        # --- 4. CONFIRMACIÓN DE CAMBIOS ---
        # Guardamos todos los cambios realizados en la base de datos.
        conn.commit()

    except sqlite3.Error as e:
        print(f"❌ Error de base de datos al configurar el esquema: {e}")
        # Si ocurre un error, revertimos cualquier cambio parcial.
        if conn:
            conn.rollback()

    except Exception as e:
        print(f"❌ Ocurrió un error inesperado: {e}")

    finally:
        # --- 5. CIERRE DE CONEXIÓN ---
        # Nos aseguramos de que la conexión siempre se cierre, incluso si hay errores.
        if conn:
            conn.close()
            print("🔌 Conexión a la base de datos cerrada.")
        print("--- ✨ Configuración del esquema finalizada ---")

# ===================================================================================
# SECCIÓN DE EJECUCIÓN DIRECTA
# ===================================================================================
# Esto permite que ejecutes este archivo directamente desde la terminal
# para configurar la base de datos en cualquier momento.
if __name__ == '__main__':
    configurar_base_de_datos()