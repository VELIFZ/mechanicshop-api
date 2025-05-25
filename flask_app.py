from flask import redirect
from application import create_app

app = create_app("production")

@app.route('/', methods=['GET'])
def index():
    return redirect('api/docs')