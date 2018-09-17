import os
import sys


class Config:

    PROJECT_ROOT = os.path.abspath(os.path.dirname(sys.argv[0]))

    DB_USER = os.getenv('DB_USER')
    DB_PASSWORD = os.getenv('DB_PASSWORD')
    DB_HOST = os.getenv('DB_HOST')
    DB_NAME = os.getenv('DB_NAME')

    API_LOGIN = os.getenv('API_LOGIN')
    API_PASSWORD = os.getenv('API_PASSWORD')

    # DASHBOARD_USER = ''
    # DASHBOARD_PASSWORD =
    # DASHBOARD_USER =
    # DASHBOARD_PASSWORD =
