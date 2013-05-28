#!/usr/bin/python
# encoding: UTF-8

__all__ = ['db', 'User', 'Forget', \
        'init_account_db']

import config
import hashlib
from datetime import datetime
from utils.token import create_token
from flask.ext.sqlalchemy import SQLAlchemy

db = SQLAlchemy()
def init_account_db(app):
    db.init_app(app)
    db.app = app
    db.create_all()

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column('id', db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.CHAR(16), nullable=False)
    passwd = db.Column(db.CHAR(50), nullable=False)
    domain = db.Column(db.String(20), unique=True)
    email = db.Column(db.String(200), nullable=False, unique=True)
    token = db.Column(db.CHAR(16))
    city = db.Column(db.String(150))
    title = db.Column(db.String(150))
    join = db.Column(db.DateTime, default=datetime.now)

    def __init__(self, username, password, email):
        self.name = username
        self.passwd = User.create_password(password)
        self.email = email.lower()
        self.token = create_token(16)

    @staticmethod
    def create(username, password, email):
        user = User(username, password, email)
        db.session.add(user)
        db.session.commit()
        return user

    @staticmethod
    def create_password(raw):
        salt = create_token(8)
        hsh = hashlib.sha1(salt + raw).hexdigest()
        return "%s$%s" % (salt, hsh)

    def check_password(self, raw):
        if '$' not in self.passwd:
            return False
        salt, hsh = self.passwd.split('$')
        verify = hashlib.sha1(salt + raw).hexdigest()
        return verify == hsh

    def change_password(self, password):
        self.token = create_token(16)
        self.passwd = User.create_password(password)
        db.session.add(self)
        db.session.commit()

    def change_username(self, name):
        self.name = name
        db.session.add(self)
        db.session.commit()

    def set_domain(self, domain):
        self.domain = domain
        db.session.add(self)
        db.session.commit()

    def set_args(self, key, value):
        setattr(self, key, value)
        db.session.add(self)
        db.session.commit()

    def avatar(self, size=48):
        md5email = hashlib.md5(self.email).hexdigest()
        query = "%s?s=%s%s" % (md5email, size, config.GRAVATAR_EXTRA)
        return '%s%s' % (config.GRAVATAR_BASE_URL, query)

class Forget(db.Model):
    __tablename__ = 'forget'
    id = db.Column('id', db.Integer, primary_key=True, autoincrement=True)
    uid = db.Column('uid', db.Integer, nullable=False, unique=True)
    stub = db.Column('stub', db.CHAR(20), nullable=False, unique=True)
    created = db.Column(db.DateTime, default=datetime.now)

    def __init__(self, uid, stub):
        self.uid = uid
        self.stub = stub

    @staticmethod
    def create(uid, stub):
        forget = Forget(uid, stub)
        db.session.add(forget)
        db.session.commit()
        return forget

    def delete(self):
        db.session.delete(self)
        db.session.commit()
