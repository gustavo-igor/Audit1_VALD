from werkzeug.security import generate_password_hash, check_password_hash

def encriptar_password(password):
    """Genera un hash seguro para una contraseña."""
    return generate_password_hash(password, method='pbkdf2:sha256')

def verificar_password(hashed_password, password):
    """Verifica si una contraseña coincide con su hash."""
    return check_password_hash(hashed_password, password)