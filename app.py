from dotenv import load_dotenv
load_dotenv()

from application import create_app
from application.models import db

app = create_app('development')

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run()
