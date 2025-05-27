from flask import redirect
from application import create_app
from application.models import db

app = create_app("production")


@app.route('/', methods=['GET'])
def index():
    return redirect('/api/docs')

with app.app_context():
    db.create_all()