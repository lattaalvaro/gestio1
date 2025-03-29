import sqlite3

# Conectar a la base de datos (o crearla si no existe)
conn = sqlite3.connect('fusiles.db')
cursor = conn.cursor()

# Crear la tabla para almacenar los fusiles
cursor.execute('''
CREATE TABLE IF NOT EXISTS fusiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero_serie TEXT UNIQUE NOT NULL,
    estado TEXT NOT NULL,
    propietario TEXT
)
''')

# Guardar cambios y cerrar conexión
conn.commit()
conn.close()