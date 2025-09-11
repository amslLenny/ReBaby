
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
