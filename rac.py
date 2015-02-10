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

from flask import Flask, url_for, render_template
from flask.ext.sqlalchemy import SQLAlchemy
from r1soft.cdp3 import CDP3Client
from humanize import naturalsize


app = Flask(__name__)
app.config.from_envvar('RAC_SETTINGS')
db = SQLAlchemy(app)



class R1softHost(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    username    = db.Column(db.String(255))
    password    = db.Column(db.String(255))
    hostname    = db.Column(db.String(255))
    api_port    = db.Column(db.Integer())
    api_ssl     = db.Column(db.Boolean())

    _conn       = None

    def __init__(self, hostname, username, password, api_port=9443, api_ssl=True):
        self.hostname = hostname
        self.username = username
        self.password = password
        self.api_port = api_port
        self.api_ssl = api_ssl

    @property
    def conn(self):
        if self._conn is None:
            self._conn = CDP3Client(self.hostname, self.username, self.password,
                port=self.api_port, ssl=self.api_ssl)
        return self._conn


@app.context_processor
def inject_hosts():
    return {'hosts': R1softHost.query.all()}

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
