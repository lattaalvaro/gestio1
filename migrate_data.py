import sqlite3

def conectar_bd():
    return sqlite3.connect('fusiles.db')

def migrar_datos():
    conn = conectar_bd()
    cursor = conn.cursor()
    
    # Verificar primero si la columna tipo_arma existe
    cursor.execute("PRAGMA table_info(fusiles)")
    columnas = cursor.fetchall()
    columnas_nombres = [columna[1] for columna in columnas]
    
    if 'tipo_arma' in columnas_nombres:
        # Actualizar registros que no tienen tipo_arma
        cursor.execute("UPDATE fusiles SET tipo_arma = 'Fusil ACE 23' WHERE tipo_arma IS NULL")
        conn.commit()
        print(f"Migración completada. {cursor.rowcount} registros actualizados.")
    else:
        print("La columna 'tipo_arma' no existe en la tabla 'fusiles'.")
        
        # Agregar la columna si no existe
        try:
            cursor.execute("ALTER TABLE fusiles ADD COLUMN tipo_arma TEXT")
            cursor.execute("UPDATE fusiles SET tipo_arma = 'Fusil ACE 23'")
            conn.commit()
            print("Columna 'tipo_arma' añadida y registros actualizados.")
        except sqlite3.OperationalError as e:
            print(f"Error al añadir la columna: {e}")
    
    conn.close()

if __name__ == "__main__":
    migrar_datos()