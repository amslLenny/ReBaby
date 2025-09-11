#!/usr/bin/env python3

from pathlib import Path
import os

PROJECT_DIR = Path('rebaby_site')
TEMPLATES_DIR = PROJECT_DIR / 'templates'
STATIC_DIR = PROJECT_DIR / 'static'
CSS_DIR = STATIC_DIR / 'css'
JS_DIR = STATIC_DIR / 'js'
UPLOADS_DIR = STATIC_DIR / 'uploads'

for d in (PROJECT_DIR, TEMPLATES_DIR, STATIC_DIR, CSS_DIR, JS_DIR, UPLOADS_DIR):
    d.mkdir(parents=True, exist_ok=True)

app_py = r"""
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, DecimalField, SelectField
from wtforms.validators import DataRequired, Length, Email, NumberRange
from PIL import Image, UnidentifiedImageError
import os, uuid

ALLOWED_EXTENSIONS = {'png','jpg','jpeg','gif'}

app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY','dev-secret-change-me')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL','sqlite:///rebaby.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path,'static','uploads')
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    def set_password(self, pw):
        self.password_hash = generate_password_hash(pw)

    def check_password(self, pw):
        return check_password_hash(self.password_hash, pw)

class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(140), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=False)
    condition = db.Column(db.String(50), nullable=True)
    listing_type = db.Column(db.String(10), nullable=False)
    image_filename = db.Column(db.String(255), nullable=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    available = db.Column(db.Boolean, default=True)

class RegisterForm(FlaskForm):
    name = StringField('Nom', validators=[DataRequired(), Length(min=2)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Mot de passe', validators=[DataRequired(), Length(min=6)])
    submit = SubmitField('S\u2019inscrire')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Mot de passe', validators=[DataRequired()])
    submit = SubmitField('Se connecter')

class ItemForm(FlaskForm):
    title = StringField('Titre', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[Length(max=2000)])
    price = DecimalField('Prix (€)', validators=[DataRequired(), NumberRange(min=0)])
    listing_type = SelectField('Type', choices=[('sale','Vente'),('rent','Location')])
    condition = StringField('État (ex: comme neuf, bon état)')
    submit = SubmitField('Publier')

@login_manager.user_loader
def load_user(user_id):
    try:
        return User.query.get(int(user_id))
    except Exception:
        return None

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.',1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    q = request.args.get('q','')
    filter_type = request.args.get('type','')
    page = request.args.get('page',1, type=int)
    items_query = Item.query
    if q:
        items_query = items_query.filter(Item.title.ilike(f'%{q}%'))
    if filter_type in ('sale','rent'):
        items_query = items_query.filter_by(listing_type=filter_type)
    items = items_query.order_by(Item.id.desc()).paginate(page=page, per_page=12, error_out=False)
    return render_template('index.html', items=items)

@app.route('/register', methods=['GET','POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        if User.query.filter_by(email=form.email.data).first():
            flash('Email déjà utilisé, connectez-vous.', 'warning')
            return redirect(url_for('login'))
        u = User(name=form.name.data, email=form.email.data)
        u.set_password(form.password.data)
        db.session.add(u)
        db.session.commit()
        login_user(u)
        flash('Bienvenue chez ReBaby 🎉', 'success')
        return redirect(url_for('index'))
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET','POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        u = User.query.filter_by(email=form.email.data).first()
        if u and u.check_password(form.password.data):
            login_user(u)
            flash('Connecté', 'success')
            return redirect(url_for('index'))
        flash('Email ou mot de passe incorrect', 'danger')
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Déconnecté', 'info')
    return redirect(url_for('index'))

@app.route('/add', methods=['GET','POST'])
@login_required
def add_item():
    form = ItemForm()
    if form.validate_on_submit():
        f = request.files.get('image')
        filename = None
        if f and f.filename:
            if not allowed_file(f.filename):
                flash('Format d\'image non accepté', 'danger')
                return redirect(request.url)
            orig = secure_filename(f.filename)
            ext = os.path.splitext(orig)[1].lower()
            filename = f"{uuid.uuid4().hex}{ext}"
            path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            try:
                f.save(path)
                img = Image.open(path)
                img.verify()
                img = Image.open(path)
                img.thumbnail((1200,1200))
                img.save(path)
            except (UnidentifiedImageError, OSError):
                if os.path.exists(path):
                    os.remove(path)
                flash('Erreur lors du traitement de l\'image', 'danger')
                return redirect(request.url)
        try:
            price_value = float(form.price.data)
        except Exception:
            flash('Prix invalide', 'danger')
            return redirect(request.url)
        itm = Item(
            title=form.title.data,
            description=form.description.data,
            price=price_value,
            listing_type=form.listing_type.data,
            condition=form.condition.data,
            image_filename=filename,
            owner_id=current_user.id
        )
        db.session.add(itm)
        db.session.commit()
        flash('Annonce publiée ✅', 'success')
        return redirect(url_for('index'))
    return render_template('add_item.html', form=form)

@app.route('/item/<int:item_id>')
def item_detail(item_id):
    itm = Item.query.get_or_404(item_id)
    return render_template('item_detail.html', item=itm)

@app.route('/uploads/<path:filename>')
def uploads(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=False)

@app.cli.command('init-db')
def init_db():
    db.create_all()
    print('Database created')

if __name__ == '__main__':
    app.run(debug=True)
"""

base_html = r"""
<!doctype html>
<html lang="fr">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>ReBaby — Seconde vie pour les petits</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://unpkg.com/aos@2.3.1/dist/aos.css" rel="stylesheet">
    <link rel="stylesheet" href="/static/css/styles.css">
  </head>
  <body class="bg-gray-50 text-gray-800">
    <nav class="bg-white shadow">
      <div class="max-w-6xl mx-auto px-4">
        <div class="flex justify-between">
          <a href="/" class="flex items-center gap-3 py-4">
            <div class="bg-pink-200 rounded-full w-10 h-10 flex items-center justify-center text-pink-800 font-bold">RB</div>
            <div class="text-lg font-semibold">ReBaby</div>
          </a>
          <div class="flex items-center gap-4">
            <form action="/" method="get" class="hidden md:block">
              <input name="q" placeholder="Rechercher..." class="px-3 py-2 border rounded-lg" />
            </form>
            {% if current_user.is_authenticated %}
              <a href="/add" class="px-3 py-2 bg-pink-500 text-white rounded">Publier</a>
              <a href="/logout" class="px-3 py-2">Se déconnecter</a>
            {% else %}
              <a href="/register" class="px-3 py-2">S'inscrire</a>
              <a href="/login" class="px-3 py-2">Se connecter</a>
            {% endif %}
          </div>
        </div>
      </div>
    </nav>

    <main class="max-w-6xl mx-auto p-6">
      {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
          <div class="space-y-2 mb-4">
            {% for cat, msg in messages %}
              <div class="p-3 rounded-lg border" data-aos="fade-down">{{ msg }}</div>
            {% endfor %}
          </div>
        {% endif %}
      {% endwith %}

      {% block content %}{% endblock %}
    </main>

    <footer class="text-center py-8 text-sm text-gray-600">
      © ReBaby — L'entreprise familiale. Donnez une seconde vie aux objets.
    </footer>

    <script src="https://unpkg.com/aos@2.3.1/dist/aos.js"></script>
    <script>
      AOS.init({ duration: 650 });
    </script>
    <script src="/static/js/main.js"></script>
  </body>
</html>
"""

index_html = r"""
{% extends 'base.html' %}
{% block content %}
  <section class="mb-8">
    <div class="rounded-xl bg-gradient-to-r from-pink-50 to-white p-8" data-aos="zoom-in">
      <h1 class="text-3xl font-bold">ReBaby — Donner une seconde vie aux affaires de bébé</h1>
      <p class="mt-2 text-gray-600">Achetez ou louez du matériel pour les tout-petits — économique et responsable.</p>
    </div>
  </section>

  <section>
    <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
      {% for item in items.items %}
        <article class="bg-white rounded-lg shadow p-4" data-aos="fade-up">
          {% if item.image_filename %}
            <img src="/uploads/{{ item.image_filename }}" alt="{{ item.title }}" class="w-full h-48 object-cover rounded" />
          {% else %}
            <div class="w-full h-48 bg-gray-100 rounded flex items-center justify-center">Photo manquante</div>
          {% endif %}
          <h3 class="mt-3 font-semibold">{{ item.title }}</h3>
          <p class="text-sm text-gray-500">{{ item.condition or '' }}</p>
          <div class="mt-3 flex items-center justify-between">
            <div class="text-lg font-bold">€{{ '%.2f'|format(item.price) }}</div>
            <a href="/item/{{ item.id }}" class="px-3 py-1 bg-pink-500 text-white rounded">Voir</a>
          </div>
        </article>
      {% else %}
        <p>Aucune annonce pour le moment — soyez le premier !</p>
      {% endfor %}
    </div>

    <div class="mt-6 flex justify-center">
      {% if items.has_prev %}
        <a href="?page={{ items.prev_num }}" class="px-3 py-1 border rounded mr-2">Préc</a>
      {% endif %}
      <span class="px-3 py-1">Page {{ items.page }} / {{ items.pages }}</span>
      {% if items.has_next %}
        <a href="?page={{ items.next_num }}" class="px-3 py-1 border rounded ml-2">Suiv</a>
      {% endif %}
    </div>
  </section>
{% endblock %}
"""

register_html = r"""
{% extends 'base.html' %}
{% block content %}
  <div class="max-w-md mx-auto bg-white p-6 rounded shadow" data-aos="fade-right">
    <h2 class="text-xl font-semibold">Créer un compte</h2>
    <form method="post">
      {{ form.hidden_tag() }}
      <div class="mt-4">
        {{ form.name.label }}
        {{ form.name(class_='w-full px-3 py-2 border rounded') }}
      </div>
      <div class="mt-4">
        {{ form.email.label }}
        {{ form.email(class_='w-full px-3 py-2 border rounded') }}
      </div>
      <div class="mt-4">
        {{ form.password.label }}
        {{ form.password(class_='w-full px-3 py-2 border rounded') }}
      </div>
      <div class="mt-4">
        {{ form.submit(class_='px-4 py-2 bg-pink-500 text-white rounded') }}
      </div>
    </form>
  </div>
{% endblock %}
"""

login_html = r"""
{% extends 'base.html' %}
{% block content %}
  <div class="max-w-md mx-auto bg-white p-6 rounded shadow" data-aos="fade-left">
    <h2 class="text-xl font-semibold">Connexion</h2>
    <form method="post">
      {{ form.hidden_tag() }}
      <div class="mt-4">
        {{ form.email.label }}
        {{ form.email(class_='w-full px-3 py-2 border rounded') }}
      </div>
      <div class="mt-4">
        {{ form.password.label }}
        {{ form.password(class_='w-full px-3 py-2 border rounded') }}
      </div>
      <div class="mt-4">
        {{ form.submit(class_='px-4 py-2 bg-pink-500 text-white rounded') }}
      </div>
    </form>
  </div>
{% endblock %}
"""

add_item_html = r"""
{% extends 'base.html' %}
{% block content %}
  <div class="max-w-2xl mx-auto bg-white p-6 rounded shadow" data-aos="zoom-in-up">
    <h2 class="text-xl font-semibold">Publier une annonce</h2>
    <form method="post" enctype="multipart/form-data">
      {{ form.hidden_tag() }}
      <div class="mt-4">
        {{ form.title.label }}
        {{ form.title(class_='w-full px-3 py-2 border rounded') }}
      </div>
      <div class="mt-4">
        {{ form.description.label }}
        {{ form.description(class_='w-full px-3 py-2 border rounded') }}
      </div>
      <div class="mt-4">
        {{ form.price.label }}
        {{ form.price(class_='w-full px-3 py-2 border rounded') }}
      </div>
      <div class="mt-4">
        {{ form.listing_type.label }}
        {{ form.listing_type(class_='w-full px-3 py-2 border rounded') }}
      </div>
      <div class="mt-4">
        {{ form.condition.label }}
        {{ form.condition(class_='w-full px-3 py-2 border rounded') }}
      </div>
      <div class="mt-4">
        <label>Photo (optionnelle)</label>
        <input type="file" name="image" class="w-full" accept="image/*" />
      </div>
      <div class="mt-4">
        {{ form.submit(class_='px-4 py-2 bg-pink-500 text-white rounded') }}
      </div>
    </form>
  </div>
{% endblock %}
"""

item_detail_html = r"""
{% extends 'base.html' %}
{% block content %}
  <div class="max-w-4xl mx-auto bg-white p-6 rounded shadow" data-aos="fade-up">
    <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
      <div>
        {% if item.image_filename %}
          <img src="/uploads/{{ item.image_filename }}" alt="{{ item.title }}" class="w-full h-80 object-cover rounded" />
        {% else %}
          <div class="w-full h-80 bg-gray-100 rounded flex items-center justify-center">Photo manquante</div>
        {% endif %}
      </div>
      <div class="md:col-span-2">
        <h2 class="text-2xl font-bold">{{ item.title }}</h2>
        <p class="text-gray-600 mt-2">{{ item.description }}</p>
        <div class="mt-4">
          <div class="text-2xl font-semibold">€{{ '%.2f'|format(item.price) }}</div>
          <div class="text-sm text-gray-500">Type: {{ 'Vente' if item.listing_type=='sale' else 'Location' }}</div>
          <div class="mt-4">
            <a href="#" class="px-4 py-2 bg-pink-500 text-white rounded">Contact & réserver / acheter</a>
          </div>
        </div>
      </div>
    </div>
  </div>
{% endblock %}
"""

styles_css = r"""
body { font-family: ui-sans-serif, system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial; }
"""

main_js = r"""
console.log('ReBaby: script chargé');
window.addEventListener('load', ()=>{
  document.querySelectorAll('img').forEach(img=>{
    img.style.opacity = 1;
  });
});
"""

requirements = """
Flask>=2.0
Flask-Login
Flask-WTF
Flask-SQLAlchemy
WTForms
Pillow
"""

readme_md = r"""
# ReBaby - prototype

Ceci est un prototype pour ReBaby, une plateforme familiale pour donner une seconde vie au matériel de puériculture.

## Comment démarrer

```bash
python create_rebaby_project.py
cd rebaby_site
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export FLASK_APP=app.py
export FLASK_ENV=development
flask init-db
flask run
```

Visitez http://127.0.0.1:5000
"""

files = {
    PROJECT_DIR / 'create_rebaby_project.py': '# generator kept for convenience\n',
    PROJECT_DIR / 'app.py': app_py,
    PROJECT_DIR / 'requirements.txt': requirements,
    PROJECT_DIR / 'README.md': readme_md,
    TEMPLATES_DIR / 'base.html': base_html,
    TEMPLATES_DIR / 'index.html': index_html,
    TEMPLATES_DIR / 'register.html': register_html,
    TEMPLATES_DIR / 'login.html': login_html,
    TEMPLATES_DIR / 'add_item.html': add_item_html,
    TEMPLATES_DIR / 'item_detail.html': item_detail_html,
    CSS_DIR / 'styles.css': styles_css,
    JS_DIR / 'main.js': main_js,
}

for path, content in files.items():
    path.write_text(content, encoding='utf-8')

print('Scaffold updated in ./rebaby_site')
