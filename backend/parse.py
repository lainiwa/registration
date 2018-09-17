import csv
import random
from string import ascii_uppercase
from funcy import suppress, walk_keys

from sqlalchemy.exc import IntegrityError

from parts.sql import RegistrationDB


def get_from_csv(path):
    """Get data from .csv file.

    Get a list of rows, each being a dictionary.
    """
    def keys_to_lower(dic):
        return walk_keys(lambda k: k.lower(), dic)

    with open(path, 'r') as f:
        return [keys_to_lower(row) for row in csv.DictReader(f)]


def make_dict(*args, locs):
    """Select variables from current scope and make a name-value dictionary with them.

    Example:
        >>> AA = 10; B = 20; make_dict('A', 'B', locs=locals())
        {'A': 10, 'B': 20}
    """
    return {name: val for name, val in locs.items() if name in args}


if __name__ == '__main__':

    db = RegistrationDB(drop_first=True)
    random.seed(42)

    rows = get_from_csv('input/data_2018_05_10.csv')

    for row in rows:

        team_kwargs = {
            'name': row['team'],
            'tid': lambda: random.choice(ascii_uppercase)
        }

        participant_kwargs = {
            'last_name': row['last'],
            'first_name': row['first'],
            'school': row['school'],
            'team': row['team'],
            'classname': random.choice([7, 8, 9]),
            # 'time_checked': func.now(),
            'json': {
                'fav_color': 'green',
                'height': 168,
            },
        }

        while True:
            with suppress(IntegrityError):
                db.add_instance(team_kwargs, participant_kwargs)
                break
