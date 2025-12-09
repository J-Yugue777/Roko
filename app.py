from flask import Flask, request, jsonify, render_template, session,url_for,redirect  # Importa Flask para crear la app web, manejar peticiones y usar plantillas HTML
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2  # Permite conectarse y trabajar con bases de datos PostgreSQL
from psycopg2.extras import RealDictCursor  # Devuelve los resultados de las consultas como diccionarios (clave: valor)
import os  # Permite acceder a variables del sistema y manejar rutas de archivos
from datetime import datetime  # Sirve para trabajar con fechas y horas

# Configuración de la aplicación
app = Flask(__name__)

DB_CONFIG = {

    'host':'localhost',
    'database':'ROKO',
    'user':'postgres',
    'password':'123456',
    'port':5432
}


def conectar_bd(): # crea funcion para crear una conexion con la base de datos 
    try:       # Intenta crear una conexión con los datos de configuración
        conexion = psycopg2.connect(**DB_CONFIG)   # Importa la librería psycopg2 para conectarse a PostgreSQL
        return conexion  # Si todo sale bien, devuelve la conexión
    except psycopg2.Error as e:   # Si ocurre un error, lo muestra en consola
        print(f" Error al conectar a la base de datos: {e}")
        return None  # Retorna None si falla la conexión

# Crea la tabla 'contactos' si aún no existe
def crear_tabla():
    conexion = conectar_bd()  # Se conecta a la base de datos
    if conexion:
        cursor = conexion.cursor()  # Crea un cursor para ejecutar SQL
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS contactos (
            id SERIAL PRIMARY KEY,    
            nombre VARCHAR(100) NOT NULL,   
            correo VARCHAR(100) NOT NULL,    
            contra TEXT,                       
            creado TIMESTAMP DEFAULT NOW()   
 );
        """)
        
        conexion.commit()  # Guarda los cambios en la base de datos
        cursor.close()     # Cierra el cursor
        conexion.close()   # Cierra la conexión

# Ruta principal del sitio web
@app.route('/')
def inicio():
    # Renderiza la página principal 'index.html'
    return render_template('index.html')

@app.route('/Login')
def Login():
    return render_template('Login.html')

@app.route('/index')
def index():
    return render_template('index.html')


@app.route('/registro')
def registro():
    return render_template('registro.html')

@app.route('/acerca_de')
def acerca_de():
    return render_template('acerca_de.html')

@app.route('/contacto')
def contacto():
    return render_template('contacto.html')

#inicio de sesion y registro guardado

app.secret_key = os.urandom(24)  # Genera una clave aleatoria


# Ruta para guardar los datos de un contacto
# CORREGIDO: antes era @app.route('/contacto', methods=['POST'])
@app.route('/contacto/guardar', methods=['POST'])
def guardar_contactos():
    try:
        conexion = conectar_bd()
        if conexion is None:
            return jsonify({'error': 'No se pudo conectar a la base de datos'}), 500

        datos = request.get_json(silent=True)
        if not datos:
            datos = request.form.to_dict()

        nombre = datos.get('nombre', '').strip()
        correo = datos.get('correo', '').strip()
        contra = datos.get('contra', '').strip()

        if not nombre or not correo or not contra:
            return jsonify({'error': 'Nombre, correo y contraseña son obligatorios'}), 400

        contra_hash = generate_password_hash(contra)

        with conexion:
            with conexion.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO contactos (nombre, correo, contra) VALUES (%s, %s, %s) RETURNING id;",
                    (nombre, correo, contra_hash)
                )
                contacto_id = cursor.fetchone()[0]

        conexion.close()
        return jsonify({'mensaje': 'Contacto guardado exitosamente', 'id': contacto_id}), 201

    except Exception:
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Error al procesar la solicitud'}), 500


# Ruta para consultar todos los contactos guardados
@app.route('/contactos', methods=['GET'])
def ver_contactos():
    try:
        conexion = conectar_bd()  # Conexión a la base de datos
        if conexion is None:
            # Si no se puede conectar, devuelve error
            return jsonify({'error': 'No se pudo conectar a la base de datos'}), 500
        
        # Crea un cursor que devuelve los resultados como diccionarios
        cursor = conexion.cursor(cursor_factory=RealDictCursor)
        # Consulta todos los contactos ordenados del más reciente al más antiguo
        cursor.execute("SELECT * FROM contactos ORDER BY creado DESC;")
        contactos = cursor.fetchall()  # Obtiene todos los registros
        cursor.close()  # Cierra el cursor
        conexion.close()  # Cierra la conexión

        # Formatea la fecha de creación para que sea legible
        for contacto in contactos:
            if contacto['creado']:
                contacto['creado'] = contacto['creado'].strftime('%Y-%m-%d %H:%M:%S')

        # Devuelve la lista de contactos en formato JSON
        return jsonify(contactos), 200

    except Exception as e:
        # Muestra el error si ocurre algún problema
        print(f" Error al obtener contactos: {e}")
        return jsonify({'error': 'Error al obtener contactos'}), 500
    

#inicio de sesion prueba

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('Login.html')

    datos = request.form.to_dict()
    correo = datos.get('correo', '').strip()
    contra = datos.get('contra', '').strip()

    conexion = conectar_bd()
    if conexion is None:
        return jsonify({'error': 'No se pudo conectar a la base de datos'}), 500

    with conexion:
        with conexion.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT * FROM contactos WHERE correo = %s", (correo,))
            usuario = cursor.fetchone()

    conexion.close()

    if usuario and check_password_hash(usuario['contra'], contra):
        session['usuario_id'] = usuario['id']
        session['usuario_nombre'] = usuario['nombre']
        return redirect(url_for('index'))
    else:
        return render_template('Login.html', error='Correo o contraseña incorrectos'), 401
    

@app.route('/perfil')
def perfil():
    if 'usuario_id' not in session:
        return redirect(url_for('Login'))  # Redirige si no está logueado
    return f"Bienvenido {session['usuario_nombre']}"

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


# Punto de inicio del servidor Flask
if __name__ == '__main__':
    print(" Iniciando servidor...")  # Mensaje en consola al iniciar
    crear_tabla()  # Crea la tabla si no existe
    # Inicia el servidor en modo debug, accesible desde cualquier IP
    app.run(debug=True, host='0.0.0.0', port=5000)
