import datetime

from funcy import walk_values, iffy, caller, omit
from sqlalchemy import create_engine, Column, String, ForeignKey, DateTime, Integer, FetchedValue, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy_repr import RepresentableBase
from sqlalchemy_utils import database_exists, create_database, drop_database
from marshmallow_sqlalchemy import ModelSchema

from parts.config import Config

Base = declarative_base(cls=RepresentableBase)


# ##################### MODELS ##################### #

class ModelMixin:

    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower() + 's'

    @declared_attr
    def json(cls):  # moves json column to the end
        return Column(JSON)

    xmin = Column("xmin", Integer, system=True, server_default=FetchedValue())
    __mapper_args__ = {
        'version_id_col': xmin,
        'version_id_generator': False,
    }


class Team(Base, ModelMixin):
    """Table containing list of teams.

    Attributes:
        __tablename__: How the table will be referenced in pure SQL
        name: Name of the team. Primary key
        tid: Team id. Unique. Nullable
        xmin: ID of inserting transaction for this row version
    """

    name = Column(String(200), primary_key=True)
    tid = Column(String(200), unique=True)


class Participant(Base, ModelMixin):
    """Table containing list of participants.

    The ``last_name`` and ``first_name`` are composite key of table.
    Column ``team`` references the team, which participant belongs to.
    Column ``time_checked`` is intended to be set via service API,
    to indicate participant presence.

    Attributes:
        last_name: Last name of participant. Part of composite primary key
        first_name: First name of participant. Part of composite primary key
        team: Team, which participant belongs to. A foreign key
        school: School name or number
        classname: Group name/grade of participant
        time_checked: timestamp, when participant has logged in
    """

    last_name = Column(String(200), primary_key=True)
    first_name = Column(String(200), primary_key=True)

    team = Column(String(200), ForeignKey('teams.name'))

    school = Column(String(200))
    classname = Column(String(200))

    time_checked = Column(DateTime(timezone=True))


# ##################### SCHEMAS ##################### #

class TeamSchema(ModelSchema):
    class Meta:
        model = Team


class ParticipantSchema(ModelSchema):
    class Meta:
        include_fk = True
        model = Participant


# ##################### WRAPPER CLASS ##################### #

class RegistrationDB():
    """Wrapper class for working with database."""

    # SELECT pg_xact_commit_timestamp(xmin), * FROM  teams;
    def __init__(self, url=None, drop_first=False, echo=False):
        if not url:
            url = f'postgresql+psycopg2://{Config.DB_USER}:{Config.DB_PASSWORD}@{Config.DB_HOST}/{Config.DB_NAME}'
        self.engine = create_engine(url, echo=echo, pool_size=10, max_overflow=20)
        self.__create_database(drop_first)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        # self.__clear_tables()

    def __create_database(self, drop_first):
        """Create database if not exists.

        Attributes:
            drop_first (bool): if set to True, a new database
                will be (re)created. If False, the method would
                do nothing if database already exists
        """
        if database_exists(self.engine.url) and drop_first:
            drop_database(self.engine.url)
        if not database_exists(self.engine.url):
            create_database(self.engine.url)

    def __clear_tables(self):
        """Empty tables without dropping."""
        session = scoped_session(self.Session)
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(table.delete())
        session.commit()

    def __add_or_update_item(self, item):
        # with session.transaction:
        session = scoped_session(self.Session)
        session.merge(item, load=True)
        session.commit()

    def add_team(self, **kwargs):
        self.__add_or_update_item(Team(**kwargs))

    def add_participant(self, **kwargs):
        self.__add_or_update_item(Participant(**kwargs))

    def add_instance(self, team_kwargs, participant_kwargs):
        def execute_values(kwargs):
            return walk_values(iffy(callable, caller()), kwargs)
        self.add_team(**execute_values(team_kwargs))
        self.add_participant(**execute_values(participant_kwargs))

    def get_full_db(self):
        """Get a tuple(list of teams, list of participants) from DB."""
        return scoped_session(self.Session).query(Team).all(), \
               scoped_session(self.Session).query(Participant).all()

    def get_full_db_serialized(self):
        teams, participants = self.get_full_db()
        return ([omit(d, ['xmin']) for d in TeamSchema(many=True).dump(teams)[0]],
                [omit(d, ['xmin']) for d in ParticipantSchema(many=True).dump(participants)[0]])

    def get_last_changed(self):
        """Get latest insertion transaction ID.

        Get biggest (i.e. latest) transaction ID,
        which did changes to database.
        """
        return scoped_session(self.Session).query(func.max(
            func.greatest(func.pg_xact_commit_timestamp(Team.xmin),
                          func.pg_xact_commit_timestamp(Participant.xmin))
        )).first()[0]

    def check_in_participant(self, last_name, first_name):
        session = scoped_session(self.Session)
        main_query = session.query(Participant) \
                            .filter(Participant.last_name == last_name,
                                    Participant.first_name == first_name)
        new_participant = main_query.filter(
            Participant.time_checked > text('NOW() - INTERVAL \'10 MINUTES\'')
        ).first()
        if new_participant is not None:
            return False, 403
        participant = main_query.first()
        if participant:
            participant.time_checked = datetime.datetime.now()
            session.commit()
            return True, 200
        return False, 404
