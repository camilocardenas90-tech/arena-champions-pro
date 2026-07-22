from flask import Flask, render_template, request, redirect, flash, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "CLAVE_SECRETA_CHAMPIONS_2026")

# Conexión automática adaptable para la base de datos en Railway
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL", "sqlite:///arena_champions.db")
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
    pago_jornada_actual = db.Column(db.Boolean, default=True) # Abierto para la maqueta
    es_comisionado = db.Column(db.Boolean, default=False)

class PartidoChampions(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    club_local = db.Column(db.String(100), nullable=False)
    logo_local = db.Column(db.String(50), nullable=False)
    club_visita = db.Column(db.String(100), nullable=False)
    logo_visita = db.Column(db.String(50), nullable=False)
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

# ================= INICIALIZACIÓN AUTOMÁTICA SEGURA DE LA ARENA =================
@app.before_request
def inicializar_base_datos_segura():
    db.create_all()
    if not Usuario.query.filter_by(email="admin@champions.cl").first():
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
        
    nuevo_user = Usuario(nombre=nombre, email=email, clave=clave, pago_jornada_actual=True)
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

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/')
    usuario_actual = Usuario.query.get(session['user_id'])
    partidos = PartidoChampions.query.all()
    ranking_semana = Usuario.query.order_by(Usuario.puntos_semana.desc(), Usuario.exactos_semana.desc()).all()
    ranking_general = Usuario.query.order_by(Usuario.puntos_general.desc(), Usuario.exactos_general.desc()).all()
    
    premio_80 = 0
    
    apuestas_user = ApuestaChampions.query.filter_by(usuario_id=usuario_actual.id).all()
    mis_apuestas = {a.partido_id: a for a in apuestas_user}
    link_mercadopago = "#"
    
    return render_template('dashboard.html', 
                           usuario_actual=usuario_actual, 
                           partidos=partidos, 
                           ranking_semana=ranking_semana, 
                           ranking_general=ranking_general, 
                           premio_80=premio_80, 
                           mis_apuestas=mis_apuestas, 
                           link_mercadopago=link_mercadopago)

@app.route('/apostar/<int:partido_id>', methods=['POST'])
def apostar(partido_id):
    if 'user_id' not in session:
        return redirect('/')
    user = Usuario.query.get(session['user_id'])
    partido = PartidoChampions.query.get(partido_id)
    ahora = datetime.now()
    
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

@app.route('/admin_control_total')
def admin_control_total():
    if 'user_id' not in session or not session.get('es_admin'):
        return redirect('/')
    usuarios = Usuario.query.filter_by(es_comisionado=False).all()
    partidos = PartidoChampions.query.all()
    return render_template('admin_control.html', usuarios=usuarios, partidos=partidos)

@app.route('/admin_reiniciar_semana_manual')
def admin_reiniciar_semana_manual():
    if 'user_id' not in session or not session.get('es_admin'):
        return redirect('/')
    usuarios = Usuario.query.all()
    for u in usuarios:
        u.puntos_semana = 0
        u.exactos_semana = 0
    db.session.commit()
    flash("Arena purificada con éxito. ¡Tablero en cero para la nueva Jornada!")
    return redirect('/admin_control_total')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
