# Archivo: MODULES/SQLITE/CONTROLLER/notificaciones.py
import sqlite3, os
from flask import session
from flask_socketio import emit
from MODULES import rutas

def _get_db_connection():
    conn = sqlite3.connect(os.path.join(rutas.convert_rutas()["ruta_script_python"], "mapa.db"))
    conn.row_factory = sqlite3.Row
    return conn

def crear_notificacion(usuario_id, mensaje, tipo, referencia_id, socketio_instance):
    """
    Guarda una notificación en la BD y la emite en tiempo real al usuario.
    """
    conn = _get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO Notificaciones (usuario_id, mensaje, tipo, referencia_id) VALUES (?, ?, ?, ?)",
        (usuario_id, mensaje, tipo, referencia_id)
    )
    conn.commit()
    nuevo_id = cursor.lastrowid
    conn.close()

    # Prepara el objeto de notificación para enviarlo por WebSocket
    notificacion_data = {
        "id": nuevo_id,
        "mensaje": mensaje,
        "tipo": tipo,
        "referencia_id": referencia_id,
        "fecha_creacion": "Ahora mismo" # Simplificado para la vista en tiempo real
    }
    
    # Emite el evento 'nueva_notificacion' solo a la sala del usuario específico
    socketio_instance.emit('nueva_notificacion', notificacion_data, room=f'user_{usuario_id}')

def get_notificaciones_usuario(usuario_id):
    """Obtiene las notificaciones (leídas y no leídas) para un usuario."""
    conn = _get_db_connection()
    notificaciones = conn.execute(
        "SELECT * FROM Notificaciones WHERE usuario_id = ? ORDER BY fecha_creacion DESC LIMIT 20",
        (usuario_id,)
    ).fetchall()
    conn.close()
    return [dict(row) for row in notificaciones]

def marcar_notificaciones_como_leidas(usuario_id):
    """Marca todas las notificaciones no leídas de un usuario como leídas."""
    conn = _get_db_connection()
    conn.execute("UPDATE Notificaciones SET leido = 1 WHERE usuario_id = ? AND leido = 0", (usuario_id,))
    conn.commit()
    conn.close()