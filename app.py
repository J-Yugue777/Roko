from flask import Flask, request, jsonify, render_template, session,url_for,redirect, flash# Importa Flask para crear la app web, manejar peticiones y usar plantillas HTML
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
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


# Configuración de Flask-Mail para Gmail
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS') == 'True'
app.config['MAIL_USE_SSL'] = os.getenv('MAIL_USE_SSL') == 'True'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_DEFAULT_CHARSET'] = 'utf-8'

mail = Mail(app)

# Serializador para generar tokens seguros

serializer = URLSafeTimedSerializer(os.getenv('SECRET_KEY', 'mi_clave_secreta'))


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

@app.route('/perfil')
def perfil():
    return render_template('perfil.html')

@app.route('/recuperar_contra')
def recuperar_contra():
    return render_template('recuperar_contra.html')


@app.route('/restablecer_contra')
def restablecer_contra():
    return render_template('restablecer_contra.html')

#inicio de sesion y registro guardado

app.secret_key = os.urandom(24)  # Genera una clave aleatoria

@app.route('/contacto', methods=['GET', 'POST'])
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
#Ruta para consultar todos los contactos guardados





# Ruta para guardar los datos de un contacto


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
        session['id'] = usuario['id']
        session['usuario_nombre'] = usuario['nombre']
        return redirect(url_for('index'))
    else:
        return render_template('Login.html', error='Correo o contraseña incorrectos'), 401
    

@app.route('/perfil')
def perfil_user():
    if 'id' not in session:
        return redirect(url_for('Login'))  # Redirige si no está logueado
    return f"Bienvenido {session['nombre']}"

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


#recuperar contraseña prueba


@app.route('/recuperar-password', methods=['GET', 'POST'])
def recuperar_password():
    if request.method == 'POST':
        correo = request.form.get('correo', '').strip()
        
        # Verifica si el correo existe en la base de datos
        conexion = conectar_bd()
        if conexion is None:
            flash('Error de conexión con la base de datos', 'danger')
            return render_template('recuperar_contra.html')
        
        with conexion:
            with conexion.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("SELECT * FROM contactos WHERE correo = %s", (correo,))
                usuario = cursor.fetchone()
        
        conexion.close()
        
        if usuario:
            try:
                # Genera token único con expiración de 30 minutos
                token = serializer.dumps(correo, salt='recuperar-password')
                
                # Crea el enlace de recuperación
                link = url_for('restablecer_password', token=token, _external=True)
                
                # Envía el correo
                msg = Message('Recuperación de Contraseña - ROKO',
                             recipients=[correo])
                msg.body = f'''Hola {usuario['nombre']},

Has solicitado restablecer tu contraseña en ROKO. Haz clic en el siguiente enlace:

{link}

Este enlace expirará en 30 minutos.

Si no solicitaste este cambio, ignora este correo.

Saludos,
Equipo ROKO
'''
                mail.send(msg)
                flash('Se ha enviado un correo con instrucciones para restablecer tu contraseña.', 'success')
                return redirect(url_for('Login'))
            except Exception as e:
                print(f"Error al enviar correo: {e}")
                flash('Error al enviar el correo. Verifica tu configuración de email.', 'danger')
        else:
            flash('El correo electrónico no está registrado.', 'danger')
    
    return render_template('recuperar_contra.html')


@app.route('/restablecer-password/<token>', methods=['GET', 'POST'])
def restablecer_password(token):
    try:
        # Verifica el token (expira en 1800 segundos = 30 minutos)
        correo = serializer.loads(token, salt='recuperar-password', max_age=1800)
    except SignatureExpired:
        flash('El enlace ha expirado. Solicita uno nuevo.', 'danger')
        return redirect(url_for('recuperar_contra'))
    except BadSignature:
        flash('El enlace es inválido.', 'danger')
        return redirect(url_for('recuperar_contra'))
    
    if request.method == 'POST':
        nueva_password = request.form.get('password', '').strip()
        confirmar_password = request.form.get('confirmar_password', '').strip()
        
        if nueva_password != confirmar_password:
            flash('Las contraseñas no coinciden.', 'danger')
            return render_template('restablecer_contra.html', token=token)
        
        if len(nueva_password) < 6:
            flash('La contraseña debe tener al menos 6 caracteres.', 'danger')
            return render_template('restablecer_contra.html', token=token)
        
        # Hashea la nueva contraseña
        password_hash = generate_password_hash(nueva_password)
        
        # Actualiza la contraseña en la base de datos
        conexion = conectar_bd()
        if conexion is None:
            flash('Error de conexión con la base de datos', 'danger')
            return render_template('restablecer_contra.html', token=token)
        
        with conexion:
            with conexion.cursor() as cursor:
                cursor.execute(
                    "UPDATE contactos SET contra = %s WHERE correo = %s",
                    (password_hash, correo)
                )
        
        conexion.close()
        
        flash('Tu contraseña ha sido actualizada exitosamente.', 'success')
        return redirect(url_for('Login'))
    
    return render_template('restablecer_contra.html', token=token)





# Punto de inicio del servidor Flask
if __name__ == '__main__':
    print(" Iniciando servidor...")  # Mensaje en consola al iniciar
    crear_tabla()  # Crea la tabla si no existe
    # Inicia el servidor en modo debug, accesible desde cualquier IP
    app.run(debug=True, host='0.0.0.0', port=5000)
