
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
