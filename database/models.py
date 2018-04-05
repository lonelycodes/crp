from database import Base
from flask_security import UserMixin, RoleMixin
from sqlalchemy import create_engine
from sqlalchemy.orm import relationship, backref
from sqlalchemy import Boolean, DateTime, Column, Integer, \
                       String, ForeignKey
from sqlalchemy import UniqueConstraint

class RolesUsers(Base):
    __tablename__ = 'roles_users'
    id = Column(Integer(), primary_key=True)
    user_id = Column('user_id', Integer(), ForeignKey('user.id'))
    role_id = Column('role_id', Integer(), ForeignKey('role.id'))


class Role(Base, RoleMixin):
    __tablename__ = 'role'
    id = Column(Integer(), primary_key=True)
    name = Column(String(80), unique=True)
    description = Column(String(255))
    # __str__ is required by Flask-Admin, so we can have human-readable values for
    # the Role when editing a User.
    # If we were using Python 2.7, this would be __unicode__ instead.
    def __str__(self):
        return self.name

    # __hash__ is required to avoid the exception TypeError:
    # unhashable type: 'Role' when saving a User
    def __hash__(self):
        return hash(self.name)


class User(Base, UserMixin):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True)
    username = Column(String(255))
    password = Column(String(255))
    last_login_at = Column(DateTime())
    current_login_at = Column(DateTime())
    last_login_ip = Column(String(100))
    current_login_ip = Column(String(100))
    login_count = Column(Integer)
    active = Column(Boolean())
    confirmed_at = Column(DateTime())
    roles = relationship('Role', secondary='roles_users',
                         backref=backref('users', lazy='dynamic'))

class Source(Base):
    __tablename__ = 'source'
    id = Column(Integer, primary_key=True)
    name = Column(String(20), unique=True)
    domain = Column(String(50), default="")
    xp_title = Column(String(512), default="")
    xp_lead = Column(String(512), default="")
    xp_content = Column(String(512), default="")
    xp_date = Column(String(512), default="")
    xp_author = Column(String(512), default="")
    xp_keywords = Column(String(512), default="")
    f_title = Column(String(512), default="")
    f_lead = Column(String(512), default="")
    f_content = Column(String(512), default="")
    f_date = Column(String(512), default="")
    f_author = Column(String(512), default="")
    f_keywords = Column(String(512), default="")
    num_files_pdf = Column(Integer, default=0)
    num_files_html = Column(Integer, default=0)
    num_token_pdf = Column(Integer, default=0)
    num_token_html = Column(Integer, default=0)
    num_texts_de = Column(Integer, default=0)
    num_texts_fr = Column(Integer, default=0)
    num_texts_it = Column(Integer, default=0)
    num_texts_en = Column(Integer, default=0)
    crawling = Column(Boolean, default=False)

class SourceLog(Base):
    __tablename__ = 'sourcelog'
    id = Column(Integer, primary_key=True)
    srcname = Column(String(128))
    username = Column(String(128))
    timestamp = Column(DateTime())


class Actor(Base):
    __tablename__ = 'actor'
    id = Column(Integer, primary_key=True)
    name = Column(String(128))

class Text(Base):
    __tablename__ = 'text'
    id = Column(Integer, primary_key=True)
    src_id = Column(Integer, ForeignKey('source.id'))
    url = Column(String(256))
    title = Column(String(128))
    lead = Column(String(512), default='')
    content = Column(String(20000))
    date = Column(String(128))
    author = Column(String(128))
    keywords = Column(String(128))
    lang = Column(String(8))
    ftype = Column(String(8), default='html')
    num_token = Column(Integer)
