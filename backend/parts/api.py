import glob
import os
import subprocess
from datetime import datetime

import jinja2
from flask import Flask, request, abort, redirect, url_for, send_file
from flask_restful import Api, Resource, reqparse
from flask_httpauth import HTTPBasicAuth
from flask_cors import CORS

from parts.sql import RegistrationDB
from pprint import pprint

import ipaddress
from funcy import suppress

from parts.config import Config


app = Flask(__name__, static_folder='../../frontend/dist', static_url_path='')
CORS(app)
api = Api(app, prefix='/api')

auth = HTTPBasicAuth()
db = RegistrationDB()


def render(tpl_path, context):
    """Render template with jinja2.

    Render (presumably html) template,
    which letter is to be converted to image
    of a check and sent to printing.

    Args:
        tpl_path (str): Path of the template
        context (dict): Context to render template with

    Returns:
        str: Rendered (html) template
    """
    path, filename = os.path.split(tpl_path)
    return jinja2.Environment(
        loader=jinja2.FileSystemLoader(path or './')
    ).get_template(filename).render(context)


@auth.verify_password
def verify(mail, password):
    """If mail and password are correct."""
    return (mail, password) == (Config.API_LOGIN, Config.API_PASSWORD)


@app.route('/dash/')
def dash():
    """Dashboard route."""
    return app.send_static_file('dash.html')

@app.route('/kiosk/')
def kiosk():
    """Kiosk route without ip address.

    Redirects to /kiosk/<ip-of-the-client>.
    """
    return redirect(url_for('kiosk_ip', printer_ip=request.environ['REMOTE_ADDR']))

@app.route('/kiosk/<printer_ip>')
def kiosk_ip(printer_ip):
    """Kiosk route with ip address (of the printer) set in url.

    If value stated in url is not a valid ip,
    return 422 error.
    """
    with suppress(ValueError):
        ipaddress.ip_address(printer_ip)
        return app.send_static_file('kiosk.html')
    abort(422)  # invalid IP-address

@app.route('/check/')
def check():
    """Show latest generated check.

    If no rendered checks found, returns textual message.
    """
    list_of_prints = glob.glob(os.path.abspath('resources/*.png'))
    with suppress(ValueError):
        latest_print = max(list_of_prints, key=os.path.getctime)
        return send_file(latest_print)
    return 'No checks genereated yet. Yikes!'


class DatabaseREST(Resource):
    """Database RESTful API methods."""

    decorators = [auth.login_required]

    def get(self):
        """Get teams and participants tables from the database in a JSON.

        Example:
            To access the API at localhost from CLI::

            $ http -a mail:pass GET :9998/api/db
        """
        teams, participants = db.get_full_db_serialized()
        return {'teams': teams, 'participants': participants}

    def post(self):
        """Get when the database last changed.

        Returns a JSON with iso-formatted string.
        If database is empty, returns empty string as a sensible dummy value.
        """
        last_changed = db.get_last_changed()
        return {'last_changed': last_changed.isoformat() if last_changed else ''}


class CheckREST(Resource):
    """Check in a participant API method."""

    decorators = [auth.login_required]

    def post(self):
        """Log in a participant by his first and last names.

        JSON should contain `last_name` and `first_name` fields.
        Returns either 200 http-code, or a string message with http-error.

        Returns:
            tuple: tuple containing:

                - **http-code** (*int*): http-code error to return to user (200 by default)
                - **message** (*str*): explanatory message for the error code

        Example::

            $ http -a mail:pass POST :9998/api/check last_name='Сафонов' first_name='Иван'
        """
        parser = reqparse.RequestParser()
        parser.add_argument('last_name', type=str, required=True)
        parser.add_argument('first_name', type=str, required=True)
        args = parser.parse_args()
        rez, code = db.check_in_participant(last_name=args['last_name'], first_name=args['first_name'])
        if not rez:
            return {403: 'Already registered.', 404: 'No such participant.'}[code], code


class PrintREST(Resource):
    decorators = [auth.login_required]

    def post(self):
        """
        http -a mail:pass POST :9998/api/print
        """
        args = request.get_json(force=True)
        # print(args)
        ip_addr = args.get('printer_ip')
        # ip_addr = '192.168.0.165'
        with open(f'resources/rendered_{ip_addr}.html', 'w') as file:
            print(render('resources/template.html', args), file=file)
        subprocess.call(f'''
            cd resources/
            wkhtmltoimage --zoom 5 --width 700 -f png rendered_{ip_addr}.html - > rendered_{ip_addr}.png
            convert rendered_{ip_addr}.png -rotate 180 - | lp -d {ip_addr}
        ''', shell=True)


class FilesREST(Resource):
    decorators = [auth.login_required]

    def post(self):
        files = glob.iglob('../frontend/dist/**/*', recursive=True)
        times = [os.stat(file).st_mtime for file in files]
        return {'last_changed': datetime.fromtimestamp(max(times)).isoformat()}


api.add_resource(DatabaseREST, '/db')  # GET, POST
api.add_resource(CheckREST, '/check')  # POST
api.add_resource(PrintREST, '/print')  # POST
api.add_resource(FilesREST, '/files')  # POST
