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

from rac import app
from rac.models import R1softHost, UUIDLink
from rac.util import green_map, policy2agent, inflate_tasks, inflate_task_alerts, \
    sort_tasks, inflate_task_logs, search_uuid_map
from rac.forms import HostConfigurationForm

from flask import render_template, request
import datetime


@app.route('/')
@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/host/<int:host_id>/')
def host_details(host_id):
    host = R1softHost.query.get(host_id)
    cfg_svc = host.conn.Configuration.service
    disks = sorted(green_map(host.conn.StorageDisk.service.getStorageDiskByPath,
            host.conn.StorageDisk.service.getStorageDiskPaths()),
        key=lambda i: i.capacityBytes,
        reverse=True)[:3]
    host_stats = {
        'info': cfg_svc.getServerInformation(),
        'license': cfg_svc.getServerLicenseInformation(),
        'task_scheduler': cfg_svc.getTaskSchedulerStatistics(),
    }
    return render_template('host/overview.html',
        host=host,
        host_stats=host_stats,
        policies=host.conn.Policy2.service.getPolicies(),
        volumes=host.conn.Volume.service.getVolumes(),
        disks=disks,
        agent_count=len(host.conn.Agent.service.getAgentIDs()))

@app.route('/host/<int:host_id>/volumes/')
def host_volumes(host_id):
    host = R1softHost.query.get(host_id)
    return render_template('host/volumes.html',
        host=host,
        volumes=host.conn.Volume.service.getVolumes())

@app.route('/host/<int:host_id>/agents/')
def host_agents(host_id):
    host = R1softHost.query.get(host_id)
    return render_template('host/agents.html',
        host=host,
        agents=host.conn.Agent.service.getAgents())

@app.route('/host/<int:host_id>/disksafes/')
def host_disksafes(host_id):
    host = R1softHost.query.get(host_id)
    return render_template('host/disksafes.html',
        host=host,
        disksafes=host.conn.DiskSafe.service.getDiskSafes())

@app.route('/host/<int:host_id>/policies/')
def host_policies(host_id):
    host = R1softHost.query.get(host_id)
    return render_template('host/policies.html',
        host=host,
        policies=host.conn.Policy2.service.getPolicies())

@app.route('/host/<int:host_id>/recovery-points/')
def host_recovery_points(host_id):
    host = R1softHost.query.get(host_id)
    return render_template('host/recovery_points.html',
        host=host)

@app.route('/host/<int:host_id>/task-history/')
def host_task_history(host_id):
    host = R1softHost.query.get(host_id)
    tasks = inflate_tasks(host,
        host.conn.TaskHistory.service.getTaskExecutionContextIDs(
            scheduledStart=str(datetime.date.today() - \
                datetime.timedelta(app.config['R1SOFT_TASK_HISTORY_DAYS']))),
        with_alert_ids=True)
    return render_template('host/task_history.html',
        host=host,
        tasks=tasks)

@app.route('/host/<int:host_id>/users/')
def host_users(host_id):
    host = R1softHost.query.get(host_id)
    users = host.conn.User.service.getUsers()
    return render_template('host/users.html',
        host=host,
        users=users)

@app.route('/host/<int:host_id>/configuration')
def host_configuration(host_id):
    host = R1softHost.query.get(host_id)
    cfg_svc = host.conn.Configuration.service
    config = {
        'disk_quotas': cfg_svc.getDiskQuotas(),
        'task_history_limit': cfg_svc.getTaskHistoryLimit(),
        'http_options': cfg_svc.getHTTPOptions(),
        'ssl_options': cfg_svc.getSSLOptions(),
        'maintenance_mode': cfg_svc.getMaintenanceMode(),
    }
    config_form = HostConfigurationForm(
        soft_quota=config['disk_quotas'].softQuota,
        hard_quota=config['disk_quotas'].hardQuota,
        task_history_limit=config['task_history_limit'],
        http_enabled=config['http_options'].isEnabled,
        http_port=config['http_options'].portNumber,
        http_max_conn=config['http_options'].maxConnections,
        https_enabled=config['ssl_options'].isEnabled,
        https_port=config['ssl_options'].portNumber,
        https_max_conn=config['ssl_options'].maxConnections,
        https_keystore=config['ssl_options'].keyStorePath
    )
    return render_template('host/configuration.html',
        host=host,
        host_config=config,
        config_form=config_form)

@app.route('/host/<int:host_id>/api-proxy/<namespace>/<method>', methods=['POST'])
def host_api_proxy(host_id, namespace, method):
    raise NotImplementedError()

    host = R1softHost.query.get(host_id)
    soap_method = getattr(getattr(host.conn, namespace).service, method)
    params = request.get_json()
    func = lambda: soap_method(**params)
    return jsonify({'response': soap2native(func())})

@app.route('/host/<int:host_id>/agents/<agent_uuid>/')
def agent_details(host_id, agent_uuid):
    host = R1softHost.query.get(host_id)
    agent = host.conn.Agent.service.getAgentByID(agent_uuid)
    links = search_uuid_map(agent.hostname, agent.description)
    return render_template('host/details/agent.html',
        host=host,
        links=links,
        agent=agent)

@app.route('/host/<int:host_id>/disksafes/<disksafe_uuid>/')
def disksafe_details(host_id, disksafe_uuid):
    host = R1softHost.query.get(host_id)
    disksafe = host.conn.DiskSafe.service.getDiskSafeByID(disksafe_uuid)
    links = search_uuid_map(disksafe.description)
    return render_template('host/details/disksafe.html',
        host=host,
        links=links,
        disksafe=disksafe)

@app.route('/host/<int:host_id>/volumes/<volume_uuid>/')
def volume_details(host_id, volume_uuid):
    host = R1softHost.query.get(host_id)
    volume = host.conn.Volume.service.getVolumeById(volume_uuid)
    return render_template('host/details/volume.html',
        host=host,
        volume=volume)

@app.route('/host/<int:host_id>/policies/<policy_uuid>/')
def policy_details(host_id, policy_uuid):
    host = R1softHost.query.get(host_id)
    policy = host.conn.Policy2.service.getPolicyById(policy_uuid)
    links = search_uuid_map(policy.name, policy.description)
    return render_template('host/details/policy.html',
        host=host,
        links=links,
        policy=policy)

@app.route('/host/<int:host_id>/task-history/<task_uuid>/')
def task_details(host_id, task_uuid):
    host = R1softHost.query.get(host_id)
    task = inflate_task_logs(host, inflate_task_alerts(host,
        host.conn.TaskHistory.service.getTaskExecutionContextByID(task_uuid)))
    return render_template('host/details/task.html',
        host=host,
        task=task)

@app.route('/policy-directory/')
def policy_directory_collection():
    return render_template('policy_directory_collection.html')

@app.route('/policy-directory/host/<int:host_id>/data')
def policy_directory_collection_data(host_id):
    host = R1softHost.query.get(host_id)
    policies = host.conn.Policy2.service.getPolicies()
    host_data = {
        'stuck':            False,
        'last_successful':  None,
    }
    policy_data = []

    for (agent, policy) in zip(green_map(policy2agent, policies), policies):
        if agent is None: continue
        policy_extra_data = {
            'real_state':       None,
            'timestamp':        None,
        }
        task_ids_by_state = lambda state: host.conn.TaskHistory.service.getTaskExecutionContextIDs( \
            agents=[agent.id], taskTypes=['DATA_PROTECTION_POLICY'], taskStates=[state])

        if not policy.enabled:
            policy_extra_data['real_state'] = 'disabled'
            policy_extra_data['timestamp'] = policy.lastReplicationRunTime.replace(microsecond=0)
        else:
            if policy.state in ('OK', 'ALERT'):
                # latest policy run was successful (possibly with alerts)
                policy_extra_data['real_state'] = policy.state.lower()
                policy_extra_data['timestamp'] = policy.lastReplicationRunTime.replace(microsecond=0)
                running_task_ids = task_ids_by_state('RUNNING')
                if running_task_ids:
                    running_tasks = sort_tasks(inflate_tasks(host, running_task_ids))
                    run_time = host.server_time - running_tasks[-1].executionTime.replace(microsecond=0)
                    if (abs(run_time.days * (60 * 60 * 24)) + run_time.seconds) > app.config['R1SOFT_STUCK_TIMEOUT']:
                        host_data['stuck'] = True
                        policy_extra_data['timestamp'] = running_tasks[-1].executionTime.replace(microsecond=0)
                        policy_extra_data['real_state'] = 'stuck'
                if not host_data['stuck'] and (host_data['last_successful'] is None or \
                        host_data['last_successful'] < policy.lastReplicationRunTime):
                    host_data['last_successful'] = policy.lastReplicationRunTime.replace(microsecond=0)
            elif policy.state == 'ERROR':
                # latest policy run had an error
                finished_task_ids = task_ids_by_state('FINISHED')
                if finished_task_ids:
                    finished_tasks = sort_tasks(inflate_tasks(host, finished_task_ids))
                    policy_extra_data['timestamp'] = finished_tasks[-1].executionTime.replace(microsecond=0)
                else:
                    policy_extra_data['timestamp'] = '> 30 days'
                policy_extra_data['real_state'] = 'error'
            else:
                # policy.state == 'UKNOWN' and policy hasn't been run before
                policy_extra_data['real_state'] = 'new'

        policy_data.append((agent, policy, policy_extra_data))

    return render_template('policy_directory_collection_data.html',
        host=host,
        host_extra_data=host_data,
        collection_data=policy_data)
