from __future__ import absolute_import, division, print_function

from wqflask import app

from flask import Flask, render_template

# Setup mail
from flask.ext.mail import Mail
mail = Mail(app)

from wqflask.model import *

# Create a user to test with
##@app.before_first_request
#def create_user():
#    db.create_all()
#    user_datastore.create_user(email='matt@example.com', password='notebook')
#    db.session.commit()

import logging
file_handler = logging.FileHandler(app.config['LOGFILE'])
file_handler.setLevel(logging.DEBUG)
app.logger.addHandler(file_handler)

import logging_tree
logging_tree.printout()

#import sys
#print("At startup, path is:", sys.path)

from werkzeug.contrib.fixers import ProxyFix
app.wsgi_app = ProxyFix(app.wsgi_app)

#print("app.config is:", app.config)

if __name__ == '__main__':
    #create_user()
    app.run(host='0.0.0.0',
        port=app.config['SERVER_PORT'],
        use_debugger=False,
        threaded=True,
        use_reloader=True)
