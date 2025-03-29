from flask import Flask, request, jsonify, render_template, redirect, url_for, flash, session
import sqlite3
import os
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "clave_secreta_temporal")

# Configurar Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Clase de usuario para Flask-Login
class User(UserMixin):
    def __init__(self, id, username, role):
        self.id = id
        self.username = username
        self.role = role

# Función para cargar el usuario actual
@login_manager.user_loader
def load_user(user_id):
    conn = conectar_bd()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, role FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        return User(user[0], user[1], user[2])
    return None

# Función para conectar a la base de datos
def conectar_bd():
    return sqlite3.connect('fusiles.db')

# Inicializar la base de datos
def init_db():
    conn = conectar_bd()
    cursor = conn.cursor()
    
    # Tabla de fusiles
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS fusiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero_serie TEXT UNIQUE NOT NULL,
        tipo_arma TEXT,
        estado TEXT NOT NULL,
        compania TEXT,
        peloton TEXT,
        asignado TEXT
    )
    ''')
    
    # Tabla de usuarios
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL
    )
    ''')
    
    # Verificar si hay usuarios ya creados, si no, crear usuarios por defecto
    cursor.execute("SELECT COUNT(*) FROM users")
    user_count = cursor.fetchone()[0]
    
    if user_count == 0:
        # Crear usuario administrador
        admin_password = generate_password_hash("admin123")
        cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                      ("admin", admin_password, "admin"))
        
        # Crear usuario visitante
        visitor_password = generate_password_hash("visitante123")
        cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                      ("visitante", visitor_password, "visitante"))
    
    conn.commit()
    conn.close()

# Decorador personalizado para restringir acceso según el rol
def role_required(roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('login'))
            
            if current_user.role not in roles:
                flash('No tienes permiso para acceder a esta página.', 'danger')
                return redirect(url_for('buscar'))
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Crear el formulario de login
class LoginForm(FlaskForm):
    username = StringField('Usuario', validators=[DataRequired(), Length(min=3, max=50)])
    password = PasswordField('Contraseña', validators=[DataRequired()])
    submit = SubmitField('Iniciar Sesión')

# Llamar la función para crear la base de datos si no existe
init_db()

# Ruta de inicio de sesión
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        # Si el usuario ya está autenticado, redirigir a la página de inicio
        if current_user.role == 'admin':
            return redirect(url_for('home'))
        else:
            return redirect(url_for('buscar'))
    
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        
        conn = conectar_bd()
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, password, role FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()
        
        if user and check_password_hash(user[2], password):
            user_obj = User(user[0], user[1], user[3])
            login_user(user_obj)
            
            next_page = request.args.get('next')
            if not next_page or not next_page.startswith('/'):
                if user[3] == 'admin':
                    next_page = url_for('home')
                else:
                    next_page = url_for('buscar')
                
            return redirect(next_page)
        else:
            flash('Usuario o contraseña incorrectos', 'danger')
    
    return render_template('login.html', form=form)

# Ruta de cierre de sesión
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# Ruta principal (carga el HTML)
@app.route('/')
@login_required
@role_required(['admin'])
def home():
    return render_template('index.html')

# Ruta para listar los fusiles
@app.route('/lista')
@login_required
@role_required(['admin'])
def lista():
    return render_template('lista.html')

# Ruta para buscar fusiles (accesible para todos los roles)
@app.route('/buscar')
@login_required
def buscar():
    return render_template('buscar.html')

# API para listar los fusiles
@app.route('/listar_fusiles')
@login_required
def listar_fusiles():
    conn = conectar_bd()
    cursor = conn.cursor()
    cursor.execute("SELECT id, numero_serie, tipo_arma, estado, compania, peloton, asignado FROM fusiles")
    fusiles = cursor.fetchall()
    conn.close()

    return jsonify({
        "fusiles": [
            {
                "id": f[0],
                "numero_serie": f[1] or '',
                "tipo_arma": f[2] or '',
                "estado": f[3] or '',
                "compania": f[4] or '',
                "peloton": f[5] or '',
                "asignado": f[6] or ''
            }
            for f in fusiles
        ]
    })

# API para buscar fusiles
@app.route('/buscar_fusiles')
@login_required
def buscar_fusiles():
    filtro = request.args.get('filtro', '').lower()
    
    conn = conectar_bd()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, numero_serie, tipo_arma, estado, compania, peloton, asignado FROM fusiles WHERE "
        "LOWER(numero_serie) LIKE ? OR LOWER(tipo_arma) LIKE ? OR LOWER(estado) LIKE ? OR "
        "LOWER(compania) LIKE ? OR LOWER(peloton) LIKE ? OR LOWER(asignado) LIKE ?",
        (f'%{filtro}%', f'%{filtro}%', f'%{filtro}%', f'%{filtro}%', f'%{filtro}%', f'%{filtro}%')
    )
    fusiles = cursor.fetchall()
    conn.close()

    return jsonify({
        "fusiles": [
            {
                "id": f[0],
                "numero_serie": f[1] or '',
                "tipo_arma": f[2] or '',
                "estado": f[3] or '',
                "compania": f[4] or '',
                "peloton": f[5] or '',
                "asignado": f[6] or ''
            }
            for f in fusiles
        ]
    })

# Ruta para agregar un fusil (solo admin)
@app.route('/agregar_fusil', methods=['POST'])
@login_required
@role_required(['admin'])
def agregar_fusil():
    datos = request.get_json()
    numero_serie = datos.get('numero_serie')
    tipo_arma = datos.get('tipo_arma', 'Fusil ACE 23')  # Valor por defecto
    estado = datos.get('estado', 'a. operaciones')
    compania = datos.get('compania', '')
    peloton = datos.get('peloton', '')
    asignado = datos.get('asignado', '')

    if not numero_serie:
        return jsonify({"error": "El número de serie es obligatorio"}), 400

    conn = conectar_bd()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO fusiles (numero_serie, tipo_arma, estado, compania, peloton, asignado) VALUES (?, ?, ?, ?, ?, ?)",
                       (numero_serie, tipo_arma, estado, compania, peloton, asignado))
        conn.commit()
        return jsonify({"mensaje": "Armamento agregado correctamente"}), 201
    except sqlite3.IntegrityError:
        return jsonify({"error": "El número de serie ya existe"}), 400
    finally:
        conn.close()

# Ruta para editar un fusil (solo admin)
@app.route('/editar_fusil/<int:id>', methods=['PUT'])
@login_required
@role_required(['admin'])
def editar_fusil(id):
    datos = request.get_json()
    numero_serie = datos.get('numero_serie')
    tipo_arma = datos.get('tipo_arma')
    estado = datos.get('estado')
    compania = datos.get('compania')
    peloton = datos.get('peloton')
    asignado = datos.get('asignado')

    if not numero_serie:
        return jsonify({"error": "El número de serie es obligatorio"}), 400

    conn = conectar_bd()
    cursor = conn.cursor()
    cursor.execute("UPDATE fusiles SET numero_serie = ?, tipo_arma = ?, estado = ?, compania = ?, peloton = ?, asignado = ? WHERE id = ?",
                   (numero_serie, tipo_arma, estado, compania, peloton, asignado, id))
    conn.commit()
    conn.close()

    return jsonify({"mensaje": "Armamento actualizado correctamente"}), 200

# Ruta para eliminar un fusil (solo admin)
@app.route('/eliminar_fusil/<int:id>', methods=['DELETE'])
@login_required
@role_required(['admin'])
def eliminar_fusil(id):
    conn = conectar_bd()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM fusiles WHERE id = ?", (id,))
    conn.commit()
    conn.close()

    return jsonify({"mensaje": "Fusil eliminado correctamente"}), 200

# API para obtener las estadísticas (accesible para ambos roles)
@app.route('/obtener_estadisticas', methods=['GET'])
@login_required
def obtener_estadisticas():
    try:
        conn = conectar_bd()
        cursor = conn.cursor()

        # Obtener todos los fusiles con detalles completos
        cursor.execute("SELECT id, numero_serie, tipo_arma, estado, compania, peloton, asignado FROM fusiles")
        fusiles = cursor.fetchall()
        conn.close()

        # Calcular total de fusiles
        total = len(fusiles)

        # Inicializar contadores
        por_estado = {}
        por_compania = {}
        por_tipo_arma = {}
        
        # Contadores específicos para categorías de armas
        categorias = {
            "fusiles": 0,
            "ametralladoras": {"M60E3": 0, "M60E4": 0, "M60 Standar": 0, "total": 0},
            "remington": 0,
            "prieto_beretta": 0,
            "storm": 0,
            "mgl": {"MK1": 0, "MGL": 0, "total": 0},
            "mortero": {"T/C": 0, "L/A": 0, "total": 0}
        }

        # Procesar fusiles
        for fusil in fusiles:
            id, numero_serie, tipo_arma, estado, compania, peloton, asignado = fusil
            
            # Conteo por estado
            if estado not in por_estado:
                por_estado[estado] = 0
            por_estado[estado] += 1
            
            # Conteo por compañía
            if compania not in por_compania:
                por_compania[compania] = 0
            por_compania[compania] += 1
            
            # Procesamiento por tipo de arma con detalles
            if tipo_arma not in por_tipo_arma:
                por_tipo_arma[tipo_arma] = {
                    "total": 0,
                    "estados": {},
                    "companias": {}
                }
                
            # Incrementar contador total para este tipo
            por_tipo_arma[tipo_arma]["total"] += 1
            
            # Contar por estado dentro de este tipo
            if estado not in por_tipo_arma[tipo_arma]["estados"]:
                por_tipo_arma[tipo_arma]["estados"][estado] = 0
            por_tipo_arma[tipo_arma]["estados"][estado] += 1
            
            # Contar por compañía dentro de este tipo
            if compania not in por_tipo_arma[tipo_arma]["companias"]:
                por_tipo_arma[tipo_arma]["companias"][compania] = 0
            por_tipo_arma[tipo_arma]["companias"][compania] += 1
            
            # Clasificar por categorías específicas
            tipo_lower = tipo_arma.lower()
            
            # Fusiles (cualquier arma que contenga "fusil" o "galil")
            if "fusil" in tipo_lower or "galil" in tipo_lower:
                categorias["fusiles"] += 1
                
            # Ametralladoras
            elif "m60e3" in tipo_lower:
                categorias["ametralladoras"]["M60E3"] += 1
                categorias["ametralladoras"]["total"] += 1
            elif "m60e4" in tipo_lower:
                categorias["ametralladoras"]["M60E4"] += 1
                categorias["ametralladoras"]["total"] += 1
            elif "m60 standar" in tipo_lower or "m60 standard" in tipo_lower:
                categorias["ametralladoras"]["M60 Standar"] += 1
                categorias["ametralladoras"]["total"] += 1
                
            # Remington
            elif "remington" in tipo_lower:
                categorias["remington"] += 1
                
            # Prieto Beretta
            elif "prieto beretta" in tipo_lower or "beretta" in tipo_lower:
                categorias["prieto_beretta"] += 1
                
            # Storm
            elif "storm" in tipo_lower:
                categorias["storm"] += 1
                
            # MGL
            elif "mgl" in tipo_lower:
                if "mk1" in tipo_lower:
                    categorias["mgl"]["MK1"] += 1
                else:
                    categorias["mgl"]["MGL"] += 1
                categorias["mgl"]["total"] += 1
                
            # Mortero
            elif "mortero" in tipo_lower:
                if "t/c" in tipo_lower or "tc" in tipo_lower:
                    categorias["mortero"]["T/C"] += 1
                elif "l/a" in tipo_lower or "la" in tipo_lower:
                    categorias["mortero"]["L/A"] += 1
                categorias["mortero"]["total"] += 1

        # Retornar las estadísticas en formato JSON
        return jsonify({
            'total': total,
            'por_estado': por_estado,
            'por_compania': por_compania,
            'por_tipo_arma': por_tipo_arma,
            'categorias': categorias
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Ejecutar la aplicación
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)