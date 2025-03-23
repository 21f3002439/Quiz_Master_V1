from flask import Flask, render_template
from application.database import db


app = Flask(__name__)
app.config.from_object("application.config.Config")

db.init_app(app)


def create_admin():
    user = User.query.filter_by(role = 'admin').first()
    if not user:
        admin = User(role = 'admin', username = 'admin', email = 'admin@gmail.com', password = 'admin',approved = True)
        db.session.add(admin)
        db.session.commit()
        print('admin created')
    else:
        print('admin already exists')

with app.app_context():
    from application.models import *
    db.create_all()
    create_admin()

from application.routes import *


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
 