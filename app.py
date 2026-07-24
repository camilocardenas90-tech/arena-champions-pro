from flask import Flask, render_template, request, redirect, flash, session, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "CLAVE_SECRETA_CHAMPIONS_2026")

app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///:memory:"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ================= MODELOS DE LA BASE DE DATOS OREJONA =================
class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    clave = db.Column(db.String(120), nullable=False)
    puntos_semana = db.Column(db.Integer, default=0)
    exactos_semana = db.Column(db.Integer, default=0)
    puntos_general = db.Column(db.Integer, default=0)
    exactos_general = db.Column(db.Integer, default=0)
    pago_jornada_actual = db.Column(db.Boolean, default=True)
    es_comisionado = db.Column(db.Boolean, default=False)

class PartidoChampions(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    club_local = db.Column(db.String(100), nullable=False)
    logo_local = db.Column(db.String(100), nullable=False)
    club_visita = db.Column(db.String(100), nullable=False)
    logo_visita = db.Column(db.String(100), nullable=False)
    goles_local_real = db.Column(db.Integer, default=-1)
    goles_visita_real = db.Column(db.Integer, default=-1)
    fecha_inicio = db.Column(db.DateTime, nullable=False)
    instancia = db.Column(db.String(50), default="FASE_LIGA")
    es_playoffs = db.Column(db.Boolean, default=False)
    cerrado = db.Column(db.Boolean, default=False)

class ApuestaChampions(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    partido_id = db.Column(db.Integer, db.ForeignKey('partido_champions.id'), nullable=False)
    pred_goles_l = db.Column(db.Integer, nullable=False)
    pred_goles_v = db.Column(db.Integer, nullable=False)
    pred_penales = db.Column(db.String(100), default="")

@app.before_request
def inicializar_base_datos_segura():
    db.create_all()
    admin_existe = Usuario.query.filter_by(email="admin@champions.cl").first()
    if not admin_existe:
        admin = Usuario(
            nombre="K-milo", 
            email="admin@champions.cl", 
            clave="champions2026", 
            es_comisionado=True, 
            pago_jornada_actual=True
        )
        db.session.add(admin)
        db.session.commit()

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/registrar', methods=['POST'])
def registrar():
    nombre = request.form['nombre']
    email = request.form['email']
    clave = request.form['clave']
    if Usuario.query.filter_by(email=email).first():
        flash("Este correo electrónico ya está registrado.")
        return redirect(url_for('index'))
    nuevo_user = Usuario(nombre=nombre, email=email, clave=clave, pago_jornada_actual=True)
    db.session.add(nuevo_user)
    db.session.commit()
    flash("¡Registro exitoso!")
    return redirect(url_for('index'))

@app.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    clave = request.form['clave']
    user = Usuario.query.filter_by(email=email, clave=clave).first()
    if user:
        session['user_id'] = user.id
        session['user_nombre'] = user.nombre
        session['es_admin'] = user.es_comisionado
        return redirect(url_for('dashboard'))
    flash("Credenciales incorrectas de acceso.")
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    usuario_actual = Usuario.query.get(session['user_id'])
    if not usuario_actual:
        session.clear()
        return redirect(url_for('index'))
    
    partidos = PartidoChampions.query.all()
    ranking_semana = Usuario.query.order_by(Usuario.puntos_semana.desc(), Usuario.exactos_semana.desc()).all()
    ranking_general = Usuario.query.order_by(Usuario.puntos_general.desc(), Usuario.exactos_general.desc()).all()
    premio_80 = 0
    mis_apuestas = {}
    return render_template('dashboard.html', usuario_actual=usuario_actual, partidos=partidos, ranking_semana=ranking_semana, ranking_general=ranking_general, premio_80=premio_80, mis_apuestas=mis_apuestas)

# ================= SECCIÓN DE CONTROL SUPREMO (BACKEND) =================

@app.route('/admin_control_total')
def admin_control_total():
    if 'user_id' not in session or not session.get('es_admin'):
        return redirect(url_for('index'))
    usuarios = Usuario.query.filter_by(es_comisionado=False).all()
    partidos = PartidoChampions.query.all()
    return render_template('admin_control.html', usuarios=usuarios, partidos=partidos)

@app.route('/admin_carga_masiva', methods=['POST'])
def admin_carga_masiva():
    if 'user_id' not in session or not session.get('es_admin'):
        return redirect(url_for('index'))
    
    instancia = request.form.get('instancia', 'FASE_LIGA')
    texto_partidos = request.form.get('texto_partidos', '')
    
    # Formato esperado: Local,LogoLocal,Visita,LogoVisita,FechaHora(YYYY-MM-DD HH:MM)
    # Ejemplo: Real Madrid,real-madrid.png,Manchester United,manchester-united.png,2026-09-15 16:00
    lineas = texto_partidos.strip().split('\n')
    contador = 0
    
    for linea in lineas:
        if not linea.strip():
            continue
        try:
            datos = linea.split(',')
            club_l = datos[0].strip()
            logo_l = datos[1].strip()
            club_v = datos[2].strip()
            logo_v = datos[3].strip()
            fecha_str = datos[4].strip()
            
            fecha_dt = datetime.strptime(fecha_str, "%Y-%m-%d %H:%M")
            
            nuevo_partido = PartidoChampions(
                club_local=club_l, logo_local=logo_l,
                club_visita=club_v, logo_visita=logo_v,
                fecha_inicio=fecha_dt, instancia=instancia
            )
            db.session.add(nuevo_partido)
            contador += 1
        except Exception as e:
            flash(f"Error procesando línea: '{linea}'. Verifica el formato.")
            return redirect(url_for('admin_control_total'))
            
    db.session.commit()
    flash(f"¡Carga masiva exitosa! Se inyectaron {contador} partidos a la Arena.")
    return redirect(url_for('admin_control_total'))

@app.route('/admin_eliminar_partido/<int:partido_id>')
def admin_eliminar_partido(partido_id):
    if 'user_id' not in session or not session.get('es_admin'):
        return redirect(url_for('index'))
    # Borrar primero las apuestas dependientes de este partido
    ApuestaChampions.query.filter_by(partido_id=partido_id).delete()
    PartidoChampions.query.filter_by(id=partido_id).delete()
    db.session.commit()
    flash("Partido fulminado de la cartelera de forma exitosa.")
    return redirect(url_for('admin_control_total'))

@app.route('/admin_alternar_apuestas/<int:partido_id>')
def admin_alternar_apuestas(partido_id):
    if 'user_id' not in session or not session.get('es_admin'):
        return redirect(url_for('index'))
    partido = PartidoChampions.query.get(partido_id)
    if partido:
        partido.cerrado = not partido.cerrado
        db.session.commit()
        estado = "CERRADO (Bloqueado)" if partido.cerrado else "ABIERTO (Permitido)"
        flash(f"El mercado del partido ha cambiado a: {estado}.")
    return redirect(url_for('admin_control_total'))

@app.route('/admin_eliminar_usuario/<int:usuario_id>')
def admin_eliminar_usuario(usuario_id):
    if 'user_id' not in session or not session.get('es_admin'):
        return redirect(url_for('index'))
    # Borrar las apuestas del usuario primero
    ApuestaChampions.query.filter_by(usuario_id=usuario_id).delete()
    Usuario.query.filter_by(id=usuario_id).delete()
    db.session.commit()
    flash("Usuario purgado de la competencia por orden suprema.")
    return redirect(url_for('admin_control_total'))

@app.route('/admin_reiniciar_semana_manual')
def admin_reiniciar_semana_manual():
    if 'user_id' not in session or not session.get('es_admin'):
        return redirect(url_for('index'))
    usuarios = Usuario.query.all()
    for u in usuarios:
        u.puntos_semana = 0
        u.exactos_semana = 0
    db.session.commit()
    flash("Arena purificada. ¡Tablero semanal en cero!")
    return redirect(url_for('admin_control_total'))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
