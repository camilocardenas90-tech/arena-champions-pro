from flask import Flask, render_template, request, redirect, flash, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "CLAVE_SECRETA_CHAMPIONS_2026")

# Conexión automática adaptable para el plan Hobby de Railway
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL", "sqlite:///arena_champions.db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ================= MODELOS DE LA BASE DE DATOS OREJONA =================
class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    clave = db.Column(db.String(120), nullable=False)
    puntos_semana = db.Column(db.Integer, default=0)    # Lo reinicias tú con el botón manual
    exactos_semana = db.Column(db.Integer, default=0)   # Desempate de la semana
    puntos_general = db.Column(db.Integer, default=0)   # Histórico acumulado para la posteridad
    exactos_general = db.Column(db.Integer, default=0)  # Histórico exactos general
    pago_jornada_actual = db.Column(db.Boolean, default=False)
    es_comisionado = db.Column(db.Boolean, default=False) # Tu usuario Dios libre de bloqueos

class PartidoChampions(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    club_local = db.Column(db.String(100), nullable=False)
    logo_local = db.Column(db.String(50), nullable=False)  
    club_visita = db.Column(db.String(100), nullable=False)
    logo_visita = db.Column(db.String(50), nullable=False)
    goles_local_real = db.Column(db.Integer, default=-1)
    goles_visita_real = db.Column(db.Integer, default=-1)
    fecha_inicio = db.Column(db.DateTime, nullable=False)
    instancia = db.Column(db.String(50), default="FASE_LIGA") # FASE_LIGA, OCTAVOS, CUARTOS, SEMIFINAL, GRAN_FINAL
    es_playoffs = db.Column(db.Boolean, default=False)
    cerrado = db.Column(db.Boolean, default=False)

class ApuestaChampions(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    partido_id = db.Column(db.Integer, db.ForeignKey('partido_champions.id'), nullable=False)
    pred_goles_l = db.Column(db.Integer, nullable=False)
    pred_goles_v = db.Column(db.Integer, nullable=False)
    pred_penales = db.Column(db.String(100), default="") 
# Creación automática de las tablas en la nube de Railway
with app.app_context():
    db.create_all()
    # Tu súper usuario Comisionado libre de cualquier paywall o bloqueo
    if not Usuario.query.filter_by(email="admin@champions.cl").first():
        admin = Usuario(nombre="K-milo", email="admin@champions.cl", clave="champions2026", es_comisionado=True, pago_jornada_actual=True)
        db.session.add(admin)
        db.session.commit()

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect('/dashboard')
    return render_template('login.html')

@app.route('/registrar', methods=['POST'])
def registrar():
    nombre = request.form['nombre']
    email = request.form['email']
    clave = request.form['clave']
    
    if Usuario.query.filter_by(email=email).first():
        flash("Este correo electrónico ya está registrado.")
        return redirect('/')
        
    nuevo_user = Usuario(nombre=nombre, email=email, clave=clave)
    db.session.add(nuevo_user)
    db.session.commit()
    flash("¡Registro exitoso en la Arena Champions Pro!")
    return redirect('/')

@app.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    clave = request.form['clave']
    user = Usuario.query.filter_by(email=email, clave=clave).first()
    
    if user:
        session['user_id'] = user.id
        session['user_nombre'] = user.nombre
        session['es_admin'] = user.es_comisionado
        return redirect('/dashboard')
    flash("Credenciales incorrectas de acceso.")
    return redirect('/')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')
@app.route('/apostar/<int:partido_id>', methods=['POST'])
def apostar(partido_id):
    if 'user_id' not in session:
        return redirect('/')
        
    user = Usuario.query.get(session['user_id'])
    partido = PartidoChampions.query.get(partido_id)
    ahora = datetime.now()
    
    # Candado de Pago por Jornada (No aplica para K-milo)
    if not user.pago_jornada_actual and not user.es_comisionado:
        flash("ACCESO RESTRINGIDO: Debes pagar tu inscripción de $2.000 para habilitar tus pronósticos de la fecha.")
        return redirect('/dashboard')
        
    if partido.fecha_inicio < ahora or partido.cerrado:
        flash("Mercado cerrado. No se permiten apuestas fuera de tiempo.")
        return redirect('/dashboard')
        
    goles_l = int(request.form['goles_l'])
    goles_v = int(request.form['goles_v'])
    pred_penales = request.form.get('pred_penales', "")
    
    apuesta = ApuestaChampions.query.filter_by(usuario_id=user.id, partido_id=partido.id).first()
    if apuesta:
        apuesta.pred_goles_l = goles_l
        apuesta.pred_goles_v = goles_v
        apuesta.pred_penales = pred_penales
    else:
        nueva_apuesta = ApuestaChampions(usuario_id=user.id, partido_id=partido.id, pred_goles_l=goles_l, pred_goles_v=goles_v, pred_penales=pred_penales)
        db.session.add(nueva_apuesta)
        
    db.session.commit()
    flash("Pronóstico guardado exitosamente.")
    return redirect('/dashboard')

# ================= EL REINICIO MANUAL DEL COMISIONADO ESTRELLA =================
@app.route('/admin_reiniciar_semana_manual')
def admin_reiniciar_semana_manual():
    if 'user_id' not in session or not session.get('es_admin'):
        return redirect('/')
        
    # El código recorre a todos tus amigos en la base de datos
    usuarios = Usuario.query.all()
    for u in usuarios:
        u.puntos_semana = 0      # Limpieza total para la nueva fecha
        u.exactos_semana = 0     # Reseteo del desempate de la fecha
        u.pago_jornada_actual = False  # Les cierra el candado de apuestas hasta que paguen la nueva ronda
        
    db.session.commit()
    flash("Arena purificada con éxito. ¡Tablero en cero para la nueva Jornada de Champions!")
    return redirect('/admin_control_total')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
