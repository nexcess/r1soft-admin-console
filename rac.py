#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Nexcess.net r1soft-admin-console
# Copyright (C) 2015  Nexcess.net L.L.C.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

from flask import Flask, url_for, render_template, jsonify, request
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.script import Manager
from flask.ext.migrate import Migrate, MigrateCommand
from r1soft.cdp3 import CDP3Client
from humanize import naturalsize
from suds.sudsobject import asdict
from types import *


app = Flask(__name__)
app.config.from_envvar('RAC_SETTINGS')
db = SQLAlchemy(app)
migrate = Migrate(app, db)
manager = Manager(app)
manager.add_command('db', MigrateCommand)


class R1softHost(db.Model):
    id          = db.Column(db.Integer(), primary_key=True)
    username    = db.Column(db.String(255), nullable=False)
    password    = db.Column(db.String(255), nullable=False)
    hostname    = db.Column(db.String(255), nullable=False, index=True)
    api_port    = db.Column(db.Integer(), default=9443)
    api_ssl     = db.Column(db.Boolean(), default=True)
    web_port    = db.Column(db.Integer(), default=8001)
    web_ssl     = db.Column(db.Boolean(), default=True)
    active      = db.Column(db.Boolean(), default=True)

    __table_args__  = (db.UniqueConstraint('hostname', 'api_port', name='api_conn_constraint'),)

    _conn       = None

    def __init__(self, hostname, username, password, api_port=9443, api_ssl=True,
            web_port=8001, web_ssl=True, active=True):
        self.hostname = hostname
        self.username = username
        self.password = password
        self.api_port = api_port
        self.api_ssl = api_ssl
        self.web_port = web_port
        self.web_ssl = web_ssl

    @property
    def conn(self):
        if self._conn is None:
            self._conn = CDP3Client(self.hostname, self.username, self.password,
                port=self.api_port, ssl=self.api_ssl)
        return self._conn

    @property
    def external_link(self):
        return '{scheme}://{hostname}:{web_port}/'.format(
            scheme='https' if self.web_ssl else 'http',
            hostname=self.hostname,
            web_port=self.web_port)

class UUIDLink(db.Model):
    id              = db.Column(db.Integer(), primary_key=True)
    host_id         = db.Column(db.Integer(), db.ForeignKey('r1soft_host.id'))
    agent_uuid      = db.Column(db.String(36), nullable=False)
    disksafe_uuid   = db.Column(db.String(36), nullable=False)
    policy_uuid     = db.Column(db.String(36), nullable=False, index=True)

    __table_args__  = (db.UniqueConstraint('agent_uuid', 'disksafe_uuid', 'policy_uuid', name='uuid_constraint'),)

    _host           = None

    def __init__(self, host_id, agent_uuid, disksafe_uuid, policy_uuid):
        self.host_id = host_id
        self.agent_uuid = agent_uuid
        self.disksafe_uuid = disksafe_uuid
        self.policy_uuid = policy_uuid

    @property
    def host(self):
        if self._host is None:
            self._host = R1softHost.query.get(self.host_id)
        return self._host

    @property
    def agent(self):
        return self.host.conn.Agent.service.getAgentByID(self.agent_uuid)

    @property
    def disksafe(self):
        return self.host.conn.DiskSafe.service.getDiskSafeByID(self.disksafe_uuid)

    @property
    def policy(self):
        return self.host.conn.DiskSafe.service.getPolicyByID(self.policy_uuid)


def soap2native(soap_obj):
    if hasattr(soap_obj, '__keylist__'):
        native_obj = {k: soap2native(getattr(soap_obj, k)) \
            for k in asdict(soap_obj).iterkeys()}
    elif isinstance(soap_obj, dict):
        native_obj = {k: soap2native(soap_obj[k]) \
            for k in soap_obj.iterkeys()}
    elif isinstance(soap_obj, list):
        native_obj = [soap2native(l) for l in soap_obj]
    else:
        native_obj = soap_obj
    return native_obj

def policy2agent(policy):
    link = UUIDLink.query.filter_by(policy_uuid=policy.id).first()
    try:
        return link.agent
    except AttributeError:
        return None


@app.context_processor
def inject_hosts():
    return {'NAV_hosts': R1softHost.query.filter_by(active=True)}

@app.template_filter('naturalsize')
def naturalsize_filter(s):
    return naturalsize(s)

@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/host/')
def list_hosts():
    return render_template('list_hosts.html')

@app.route('/host/<int:host_id>')
def show_host(host_id):
    host = R1softHost.query.get(host_id)
    return render_template('show_host.html',
        host=host,
        host_info=host.conn.Configuration.service.getServerInformation(),
        host_lic_info=host.conn.Configuration.service.getServerLicenseInformation(),
        clients=host.conn.Agent.service.getAgents())

@app.route('/host/<int:host_id>/clients')
def list_clients_json(host_id):
    host = R1softHost.query.get(host_id)
    policies = host.conn.Policy2.service.getPolicies()
    return jsonify(soap2native({
        p.id: {'policy': p, 'agent': policy2agent(p)} \
            for p in policies
        }))

@app.route('/host/<int:host_id>/return_licenses', methods=['POST'])
def host_return_licenses(host_id):
    return 'NYI'
    host = R1softHost.query.get(host_id)
    result = host.conn.Configuration.service.returnLicenses()
    return result

@app.route('/host/client/')
def list_clients():
    return render_template('list_clients.html')

@app.route('/host/<int:host_id>/client/<client_uuid>/')
def show_client(host_id, client_uuid):
    host = R1softHost.query.get(host_id)
    client = host.conn.Agent.service.getAgentByID(client_uuid)
    return render_template('show_client.html',
        host=host,
        client=client)


if __name__ == '__main__':
    app.debug = True
    app.run(host='0.0.0.0')
