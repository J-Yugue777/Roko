from flask import Flask, request, jsonify, render_template, session,url_for,redirect, flash# Importa Flask para crear la app web, manejar peticiones y usar plantillas HTML
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
import secrets, hashlib
import psycopg2  # Permite conectarse y trabajar con bases de datos PostgreSQL
from psycopg2.extras import RealDictCursor  # Devuelve los resultados de las consultas como diccionarios (clave: valor)
import os  # Permite acceder a variables del sistema y manejar rutas de archivos
from datetime import datetime , timedelta
 # Sirve para trabajar con fechas y horas

# Configuración de la aplicación
app = Flask(__name__)

# Generar una clave secreta segura como string
# En producción, usa una clave fija guardada en variable de entorno
app.secret_key = secrets.token_hex(32)  # Genera 64 caracteres hexadecimales

# Configuración de correo electrónico
app.config['MAIL_SERVER'] = 'smtp.gmail.com'  # Cambia según tu proveedor
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'tu_correo@gmail.com'  # Pon tu correo aquí
app.config['MAIL_PASSWORD'] = 'tu_contraseña_app'  # Contraseña de aplicación de Gmail
app.config['MAIL_DEFAULT_SENDER'] = 'tu_correo@gmail.com'

mail = Mail(app)
serializer = URLSafeTimedSerializer(app.secret_key)

DB_CONFIG = {
    'host': 'localhost',
    'database': 'ROKO',
    'user': 'postgres',
    'password': '123456',
    'port': 5432
}


def conectar_bd():
    try:
        conexion = psycopg2.connect(**DB_CONFIG)
        return conexion
    except psycopg2.Error as e:
        print(f"Error al conectar a la base de datos: {e}")
        return None


# Crea la tabla 'contactos' si aún no existe
def crear_tabla():
    conexion = conectar_bd()
    if conexion:
        cursor = conexion.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS contactos (
                id SERIAL PRIMARY KEY,    
                nombre VARCHAR(100) NOT NULL,   
                correo VARCHAR(100) NOT NULL UNIQUE,    
                contra TEXT,                       
                creado TIMESTAMP DEFAULT NOW()
            );
        """)
        
        # Tabla opcional para tokens de recuperación (más seguro)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tokens_recuperacion (
                id SERIAL PRIMARY KEY,
                correo VARCHAR(100) NOT NULL,
                token TEXT NOT NULL,
                usado BOOLEAN DEFAULT FALSE,
                creado TIMESTAMP DEFAULT NOW(),
                expira TIMESTAMP NOT NULL
            );
        """)
        
        conexion.commit()
        cursor.close()
        conexion.close()


# ==========================================
# RUTAS DE VISTAS SIMPLES
# ==========================================

@app.route('/')
def inicio():
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


# ==========================================
# RUTAS DE FUNCIONALIDAD
# ==========================================

# Ruta para guardar contactos (registro)
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


# Ruta para consultar todos los contactos guardados
@app.route('/contactos', methods=['GET'])
def ver_contactos():
    try:
        conexion = conectar_bd()
        if conexion is None:
            return jsonify({'error': 'No se pudo conectar a la base de datos'}), 500
        
        cursor = conexion.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM contactos ORDER BY creado DESC;")
        contactos = cursor.fetchall()
        cursor.close()
        conexion.close()

        for contacto in contactos:
            if contacto['creado']:
                contacto['creado'] = contacto['creado'].strftime('%Y-%m-%d %H:%M:%S')

        return jsonify(contactos), 200

    except Exception as e:
        print(f"Error al obtener contactos: {e}")
        return jsonify({'error': 'Error al obtener contactos'}), 500


# Inicio de sesión
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('Login.html')

    datos = request.form.to_dict()
    correo = datos.get('correo', '').strip()
    contra = datos.get('contra', '').strip()

    conexion = conectar_bd()
    if conexion is None:
        flash('No se pudo conectar a la base de datos', 'error')
        return render_template('Login.html'), 500

    with conexion:
        with conexion.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT * FROM contactos WHERE correo = %s", (correo,))
            usuario = cursor.fetchone()

    conexion.close()

    if usuario and check_password_hash(usuario['contra'], contra):
        session['id'] = usuario['id']
        session['usuario_nombre'] = usuario['nombre']
        flash('Inicio de sesión exitoso', 'success')
        return redirect(url_for('index'))
    else:
        flash('Correo o contraseña incorrectos', 'error')
        return render_template('Login.html'), 401


@app.route('/perfil')
def perfil_user():
    if 'id' not in session:
        return redirect(url_for('Login'))
    return f"Bienvenido {session['usuario_nombre']}"


@app.route('/logout')
def logout():
    session.clear()
    flash('Sesión cerrada exitosamente', 'success')
    return redirect(url_for('index'))


# ============================================
# SISTEMA DE RECUPERACIÓN DE CONTRASEÑA
# ============================================

@app.route('/recuperar_contra', methods=['GET', 'POST'])
def recuperar_contra():
    if request.method == 'GET':
        return render_template('recuperar_contra.html')
    
    correo = request.form.get('correo', '').strip()
    
    if not correo:
        flash('Por favor ingresa tu correo electrónico', 'error')
        return render_template('recuperar_contra.html')
    
    # Verificar si el correo existe
    conexion = conectar_bd()
    if conexion is None:
        flash('Error al conectar con la base de datos', 'error')
        return render_template('recuperar_contra.html')
    
    with conexion:
        with conexion.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT * FROM contactos WHERE correo = %s", (correo,))
            usuario = cursor.fetchone()
    
    # Por seguridad, siempre mostramos el mismo mensaje
    # aunque el correo no exista (para no dar pistas)
    if usuario:
        try:
            # Generar token con expiración de 1 hora
            token = serializer.dumps(correo, salt='recuperar-contraseña')
            
            # Guardar token en base de datos (opcional pero recomendado)
            expira = datetime.now() + timedelta(hours=1)
            with conexion:
                with conexion.cursor() as cursor:
                    cursor.execute(
                        "INSERT INTO tokens_recuperacion (correo, token, expira) VALUES (%s, %s, %s)",
                        (correo, token, expira)
                    )
            
            # Enviar correo
            link_recuperacion = url_for('restablecer_contra', token=token, _external=True)
            
            msg = Message(
                'Recuperación de Contraseña - ROKO',
                recipients=[correo]
            )
            msg.body = f'''Hola {usuario['nombre']},

Has solicitado restablecer tu contraseña. Haz clic en el siguiente enlace para continuar:

{link_recuperacion}

Este enlace expirará en 1 hora.

Si no solicitaste este cambio, ignora este correo.

Saludos,
Equipo ROKO
'''
            msg.html = f'''
            <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                    <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 10px;">
                        <h2 style="color: #4CAF50;">Recuperación de Contraseña</h2>
                        <p>Hola <strong>{usuario['nombre']}</strong>,</p>
                        <p>Has solicitado restablecer tu contraseña. Haz clic en el botón de abajo para continuar:</p>
                        <div style="text-align: center; margin: 30px 0;">
                            <a href="{link_recuperacion}" 
                               style="background-color: #4CAF50; color: white; padding: 12px 30px; 
                                      text-decoration: none; border-radius: 5px; display: inline-block;">
                                Restablecer Contraseña
                            </a>
                        </div>
                        <p style="color: #666; font-size: 14px;">Este enlace expirará en 1 hora.</p>
                        <p style="color: #666; font-size: 14px;">Si no solicitaste este cambio, ignora este correo.</p>
                        <hr style="margin: 20px 0; border: none; border-top: 1px solid #ddd;">
                        <p style="color: #999; font-size: 12px;">Saludos,<br>Equipo ROKO</p>
                    </div>
                </body>
            </html>
            '''
            
            mail.send(msg)
            
        except Exception as e:
            print(f"Error al enviar correo: {e}")
            flash('Hubo un error al enviar el correo. Intenta nuevamente.', 'error')
            return render_template('recuperar_contra.html')
    
    conexion.close()
    flash('Si el correo existe, recibirás instrucciones para restablecer tu contraseña', 'success')
    return redirect(url_for('Login'))


@app.route('/restablecer_contra/<token>', methods=['GET', 'POST'])
def restablecer_contra(token):
    try:
        # Verificar el token (expira en 1 hora = 3600 segundos)
        correo = serializer.loads(token, salt='recuperar-contraseña', max_age=3600)
    except SignatureExpired:
        flash('El enlace ha expirado. Solicita uno nuevo.', 'error')
        return redirect(url_for('recuperar_contra'))
    except BadSignature:
        flash('El enlace es inválido.', 'error')
        return redirect(url_for('recuperar_contra'))
    
    if request.method == 'GET':
        return render_template('restablecer_contra.html', token=token)
    
    # Procesar el cambio de contraseña
    nueva_contra = request.form.get('nueva_contra', '').strip()
    confirmar_contra = request.form.get('confirmar_contra', '').strip()
    
    if not nueva_contra or not confirmar_contra:
        flash('Completa todos los campos', 'error')
        return render_template('restablecer_contra.html', token=token)
    
    if nueva_contra != confirmar_contra:
        flash('Las contraseñas no coinciden', 'error')
        return render_template('restablecer_contra.html', token=token)
    
    if len(nueva_contra) < 6:
        flash('La contraseña debe tener al menos 6 caracteres', 'error')
        return render_template('restablecer_contra.html', token=token)
    
    # Verificar si el token ya fue usado
    conexion = conectar_bd()
    if conexion is None:
        flash('Error al conectar con la base de datos', 'error')
        return render_template('restablecer_contra.html', token=token)
    
    with conexion:
        with conexion.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                "SELECT * FROM tokens_recuperacion WHERE token = %s AND usado = FALSE",
                (token,)
            )
            token_db = cursor.fetchone()
    
    if not token_db:
        flash('Este enlace ya fue utilizado o no es válido', 'error')
        conexion.close()
        return redirect(url_for('recuperar_contra'))
    
    # Actualizar la contraseña
    nueva_contra_hash = generate_password_hash(nueva_contra)
    
    with conexion:
        with conexion.cursor() as cursor:
            # Actualizar contraseña
            cursor.execute(
                "UPDATE contactos SET contra = %s WHERE correo = %s",
                (nueva_contra_hash, correo)
            )
            # Marcar token como usado
            cursor.execute(
                "UPDATE tokens_recuperacion SET usado = TRUE WHERE token = %s",
                (token,)
            )
    
    conexion.close()
    flash('Contraseña actualizada exitosamente. Ahora puedes iniciar sesión.', 'success')
    return redirect(url_for('Login'))



# Punto de inicio del servidor Flask
if __name__ == '__main__':
    print(" Iniciando servidor...")  # Mensaje en consola al iniciar
    crear_tabla()  # Crea la tabla si no existe
    # Inicia el servidor en modo debug, accesible desde cualquier IP
    app.run(debug=True, host='0.0.0.0', port=5000)
