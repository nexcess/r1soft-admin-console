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

# This needs to be here to fix everything imported afterwards
# which is mainly suds in r1soft.cdp3
import gevent.monkey
gevent.monkey.patch_all()

from flask import Flask, url_for, render_template, jsonify, request, Markup
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.script import Manager
from flask.ext.migrate import Migrate, MigrateCommand
from r1soft.cdp3 import CDP3Client
from humanize import naturalsize
from suds.sudsobject import asdict
import datetime
import gevent.pool

app = Flask(__name__)
app.config.from_envvar('RAC_SETTINGS')
db = SQLAlchemy(app)
migrate = Migrate(app, db)
manager = Manager(app)
manager.add_command('db', MigrateCommand)
API_POOL = gevent.pool.Pool(size=app.config['R1SOFT_API_CONCURRENCY'])

ICONIZE_MAP = {
    # AgentType
    'PHYSICAL':         'fa fa-hdd-o',
    'VM':               'fa fa-cloud',

    # OSType
    'WINDOWS':          'fa fa-windows text-info',
    'LINUX':            'fa fa-linux',

    # PolicyState
    'OK':               'fa fa-check-circle-o text-success',
    'ALERT':            'fa fa-exclamation-triangle text-warning',

    # RecoveryPointState
    'REPLICATING':      '',
    'AVAILABLE':        '',
    'MERGING':          '',
    'MERGED':           '',
    'LOCKED':           '',
    'REPLICATION_INTERRUPTED':   '',
    'MERGE_INTERRUPTED':'',

    # TaskState
    'FINISHED':         'fa fa-check-circle-o text-success',
    'RUNNING':          'fa fa-spinner fa-spin text-primary',
    'QUEUED':           'fa fa-pause text-info',
    'CANCELLED':        'fa fa-times-circle-o text-danger',
    'DUPLICATE':        'fa fa-files-o text-warning',

    # TaskType
    'DATA_PROTECTION_POLICY':   'fa fa-clipboard',
    'FILE_RESTORE':     'fa fa-files-o text-info',
    'MERGE_RECOVERY_POINTS':    'fa fa-th-large text-primary',
    'EMAIL_REPORT':     'fa fa-envelope-o text-primary',
    'SYSTEM':           'fa fa-cogs',
    'TASK_HISTORY_CLEANUP':     'fa fa-expand text-success',



    # UserType
    'SUPER_USER':       '',
    'SUB_USER':         '',
    'POWER_USER':       '',

    # ReportType
    'TASK_HISTORY':     '',
    'SERVER_BACKUP':    '',
    'QUOTA_ALERT':      '',

    # Special/shared values
    True:               'fa fa-check text-success',
    False:              'fa fa-times text-danger',
    'ERROR':            'fa fa-exclamation-circle text-danger',
    'UNKNOWN':          'fa fa-question-circle',
}


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
        self.active = active

    @property
    def conn(self):
        if self._conn is None:
            self._conn = CDP3Client(self.hostname, self.username, self.password,
                port=self.api_port, ssl=self.api_ssl,
                timeout=app.config['R1SOFT_API_TIMEOUT'])
        return self._conn

    @property
    def external_link(self):
        return '{scheme}://{hostname}:{web_port}/'.format(
            scheme='https' if self.web_ssl else 'http',
            hostname=self.hostname,
            web_port=self.web_port)

    @property
    def server_time(self):
        # we should check with the server to find out what time it thinks it is
        # and use that for correct time deltas but there doesn't seem to be an
        # API method to get it so we'll just fake it with this for now
        return datetime.datetime.now()

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
        return self.host.conn.Policy2.service.getPolicyById(self.policy_uuid)


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

def policy2disksafe(policy):
    link = UUIDLink.query.filter_by(policy_uuid=policy.id).first()
    try:
        return link.disksafe
    except AttributeError:
        return None

def sort_tasks(task_list):
    return sorted(task_list, key=lambda t: t.executionTime)

def inflate_tasks(host, task_id_list):
    func = host.conn.TaskHistory.service.getTaskExecutionContextByID
    return API_POOL.map(func, task_id_list)


@app.context_processor
def inject_hosts():
    return {'NAV_hosts': R1softHost.query.filter_by(active=True)}

@app.context_processor
def inject_obj_attr_filter():
    return {'obj_attr_filter':
        lambda obj_list, attr, value: [o for o in obj_list if getattr(o, attr) == value]}

@app.template_filter('iconize')
def iconize_filter(s):
    icon_opts = ICONIZE_MAP.get(s, ICONIZE_MAP.get('UNKNOWN'))
    return Markup('<i title="%s" class="%s fa-lg"></i>' % \
        (Markup.escape(str(s).replace('_', ' ').title()), icon_opts))

@app.template_filter('naturalsize')
def naturalsize_filter(s):
    return naturalsize(s)

@app.route('/')
@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/host/')
def host_collection():
    return render_template('host_collection.html')

@app.route('/host/<int:host_id>')
@app.route('/host/<int:host_id>/dashboard')
def host_details(host_id):
    host = R1softHost.query.get(host_id)
    disks = sorted(API_POOL.map(host.conn.StorageDisk.service.getStorageDiskByPath,
            host.conn.StorageDisk.service.getStorageDiskPaths()),
        key=lambda i: i.capacityBytes,
        reverse=True)[:3]
    return render_template('host_overview.html',
        host=host,
        host_info=host.conn.Configuration.service.getServerInformation(),
        host_lic_info=host.conn.Configuration.service.getServerLicenseInformation(),
        policies=host.conn.Policy2.service.getPolicies(),
        volumes=host.conn.Volume.service.getVolumes(),
        disks=disks,
        agents=host.conn.Agent.service.getAgents())

@app.route('/host/<int:host_id>/volumes')
def host_volumes(host_id):
    host = R1softHost.query.get(host_id)
    return render_template('host_volumes.html',
        host=host,
        host_lic_info=host.conn.Configuration.service.getServerLicenseInformation(),
        volumes=host.conn.Volume.service.getVolumes())

@app.route('/host/<int:host_id>/agents')
def host_agents(host_id):
    host = R1softHost.query.get(host_id)
    return render_template('host_agents.html',
        host=host,
        agents=host.conn.Agent.service.getAgents())

@app.route('/host/<int:host_id>/disksafes')
def host_disksafes(host_id):
    host = R1softHost.query.get(host_id)
    return render_template('host_disksafes.html',
        host=host,
        disksafes=host.conn.DiskSafe.service.getDiskSafes())

@app.route('/host/<int:host_id>/policies')
def host_policies(host_id):
    host = R1softHost.query.get(host_id)
    return render_template('host_policies.html',
        host=host,
        policies=host.conn.Policy2.service.getPolicies())

@app.route('/host/<int:host_id>/recovery-points')
def host_recovery_points(host_id):
    host = R1softHost.query.get(host_id)
    return render_template('host_recovery_points.html',
        host=host)

@app.route('/host/<int:host_id>/task-history')
def host_task_history(host_id):
    host = R1softHost.query.get(host_id)
    tasks = inflate_tasks(host,
        host.conn.TaskHistory.service.getTaskExecutionContextIDs(
            scheduledStart=str(datetime.date.today() - \
                datetime.timedelta(app.config['R1SOFT_TASK_HISTORY_DAYS']))))
    return render_template('host_task_history.html',
        host=host,
        tasks=tasks)

@app.route('/host/<int:host_id>/configuration')
def host_configuration(host_id):
    host = R1softHost.query.get(host_id)
    return render_template('host_configuration.html',
        host=host)

@app.route('/host/<int:host_id>/api-proxy/<namespace>/<method>', methods=['POST'])
def host_api_proxy(host_id, namespace, method):
    raise NotImplementedError()

    host = R1softHost.query.get(host_id)
    soap_method = getattr(getattr(host.conn, namespace).service, method)
    params = request.get_json()
    func = lambda: soap_method(**params)
    return jsonify({'response': soap2native(func())})

@app.route('/meta/agents/')
def agent_collection():
    return render_template('agent_collection.html')

@app.route('/meta/host/<int:host_id>/agents')
def agent_collection_data(host_id):
    host = R1softHost.query.get(host_id)
    policies = host.conn.Policy2.service.getPolicies()
    return jsonify(soap2native({
        p.id: {'policy': p, 'agent': a} \
            for a, p in zip(API_POOL.map(policy2agent, policies), policies)
        }))

@app.route('/host/<int:host_id>/agent/<agent_uuid>/')
def agent_details(host_id, agent_uuid):
    host = R1softHost.query.get(host_id)
    agent = host.conn.Agent.service.getAgentByID(agent_uuid)
    links = UUIDLink.query.filter_by(agent_uuid=agent_uuid)
    return render_template('agent_details.html',
        host=host,
        links=links,
        agent=agent)

@app.route('/meta/policy-failures/')
def policy_failures_collection():
    return render_template('policy_failures_collection.html')

@app.route('/meta/policy-failures/host/<int:host_id>/policies')
def policy_failures_collection_data(host_id):
    host = R1softHost.query.get(host_id)
    policies = host.conn.Policy2.service.getPolicies()
    data = {
        'stuck': False,
        'last_successful': None,
        'policy_data': {},
    }
    for (policy, agent) in zip(policies, API_POOL.map(policy2agent, policies)):
        if agent is None: continue
        policy_data = {
            'name': policy.name,
            'hostname': agent.hostname,
            'description': agent.description,
            'timestamp': None,
            'state': None,
            'url_agent_details': url_for('agent_details', host_id=host.id, agent_uuid=agent.id),
        }

        task_ids_by_state = lambda state: host.conn.TaskHistory.service.getTaskExecutionContextIDs( \
            agents=[agent.id], taskTypes=['DATA_PROTECTION_POLICY'], taskStates=[state])

        if not policy.enabled:
            policy_data['state'] = 'disabled'
        else:
            if policy.state in ('OK', 'ALERT'):
                # latest policy run was successful (possibly with alerts)
                policy_data['state'] = policy.state.lower()
                running_task_ids = task_ids_by_state('RUNNING')
                if running_task_ids:
                    running_tasks = sort_tasks(inflate_tasks(host, running_task_ids))
                    run_time = host.server_time - running_tasks[-1].executionTime.replace(microsecond=0)
                    if (abs(run_time.days * (60 * 60 * 24)) + run_time.seconds) > app.config['R1SOFT_STUCK_TIMEOUT']:
                        data['stuck'] = True
                        policy_data['timestamp'] = running_tasks[-1].executionTime.replace(microsecond=0)
                        policy_data['state'] = 'stuck'
                if not data['stuck'] and (data['last_successful'] is None or \
                        data['last_successful'] < policy.lastReplicationRunTime):
                    data['last_successful'] = policy.lastReplicationRunTime.replace(microsecond=0)

            elif policy.state == 'ERROR':
                # latest policy run had an error
                finished_task_ids = task_ids_by_state('FINISHED')
                if finished_task_ids:
                    finished_tasks = sort_tasks(inflate_tasks(host, finished_task_ids))
                    policy_data['timestamp'] = finished_tasks[-1].executionTime.replace(microsecond=0)
                else:
                    policy_data['timestamp'] = '> 30 days'
                policy_data['state'] = 'error'
            else:
                # policy.state == 'UKNOWN' and policy hasn't been run before
                policy_data['state'] = 'new'
        data['policy_data'][policy.id] = policy_data

    return jsonify(data)


if __name__ == '__main__':
    app.run(host='0.0.0.0')
