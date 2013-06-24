#!/usr/local/bin/python2.7
#coding:utf-8

import os
import logging
import sqlalchemy.exc
from sheep.api.cache import cache, backend

from models import db
from models.repos import Repos, Commiters
from models.organization import Organization, Team

from utils import code
from utils.jagare import get_jagare
from utils.validators import check_repos_limit
from query.organization import clear_organization_cache, clear_team_cache

logger = logging.getLogger(__name__)

@cache('repos:{oid}:{path}', 864000)
def get_repo_by_path(oid, path):
    return Repos.query.filter_by(path=path, oid=oid).limit(1).first()

@cache('repos:commiter:{uid}:{rid}', 864000)
def get_repo_commiter(uid, rid):
    return Commiters.query.filter_by(uid=uid, rid=rid).limit(1).first()

@cache('repos:commiters:{rid}', 8640000)
def get_repo_commiters(rid):
    return Commiters.query.filter_by(rid=rid).all()

# clear

def clear_repo_permits(user, repo):
    keys = [
        'repos:commiter:{uid}:{rid}'.format(uid=user.id, rid=repo.id)
    ]
    backend.delete_many(*keys)

def clear_repo_cache(repo, organization, team=None, old_path=None):
    #TODO clear repo cache
    keys = [
        'repos:{oid}:{path}'.format(oid=organization.id, path=old_path or repo.path),
    ]
    clear_organization_cache(organization)
    if team:
        clear_team_cache(organization, team)
    backend.delete_many(*keys)

# create

def create_repo(name, path, user, organization, team=None, summary='', parent=0):
    try:
        tid = team.id if team else 0
        oid = organization.id
        uid = user.id
        repo = Repos(name, path, oid, uid, tid, summary, parent)
        db.session.add(repo)
        organization.repos = Organization.repos + 1
        db.session.add(organization)
        if team:
            team.repos = Team.repos + 1
            db.session.add(team)
        db.session.flush()
        if not check_repos_limit(organization):
            db.session.rollback()
            return None, code.ORGANIZATION_REPOS_LIMIT
        commiter = Commiters(user.id, repo.id)
        db.session.add(commiter)
        jagare = get_jagare(repo.id, parent)
        ret, error = jagare.init(repo.get_real_path())
        if not ret:
            db.session.rollback()
            return None, error
        db.session.commit()
        clear_repo_cache(repo, organization, team)
        clear_repo_permits(user, repo)
        return repo, None
    except sqlalchemy.exc.IntegrityError, e:
        db.session.rollback()
        if 'Duplicate entry' in e.message:
            return None, code.REPOS_PATH_EXISTS
        logger.exception(e)
        return None, code.UNHANDLE_EXCEPTION
    except Exception, e:
        db.session.rollback()
        logger.exception(e)
        return None, code.UNHANDLE_EXCEPTION

def create_commiter(user, repo):
    try:
        commiter = Commiters(user.id, repo.id)
        db.session.add(commiter)
        db.session.commit()
        clear_repo_permits(user, repo)
    except sqlalchemy.exc.IntegrityError, e:
        db.session.rollback()
        if 'Duplicate entry' in e.message:
            return None, code.REPOS_COMMITER_EXISTS
        logger.exception(e)
        return None, code.UNHANDLE_EXCEPTION
    except Exception, e:
        db.session.rollback()
        logger.exception(e)
        return None, code.UNHANDLE_EXCEPTION

# update

def update_repo(organization, repo, name, team=None):
    try:
        old_path = repo.path
        repo.name = name
        repo.path = '%s.git' % name if not team else '%s/%s.git' % (team.name, name)
        db.session.add(repo)
        db.session.commit()
        clear_repo_cache(repo, organization, old_path=old_path)
        return None
    except sqlalchemy.exc.IntegrityError, e:
        db.session.rollback()
        if 'Duplicate entry' in e.message:
            return code.REPOS_PATH_EXISTS
        logger.exception(e)
        return code.UNHANDLE_EXCEPTION

