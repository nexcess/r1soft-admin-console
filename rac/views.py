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
    sort_tasks, inflate_task_logs, search_uuid_map, soap2native, split_by
from rac.forms import HostConfigurationForm, RestoreForm

from flask import render_template, request, jsonify, url_for, redirect
import datetime
from os.path import join as path_join
import itertools


@app.route('/')
@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html',
        links=UUIDLink.query.all())

@app.route('/hosts/<int:host_id>/info')
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

@app.route('/hosts/<int:host_id>/volumes/')
def host_volumes(host_id):
    host = R1softHost.query.get(host_id)
    return render_template('host/volumes.html',
        host=host,
        volumes=host.conn.Volume.service.getVolumes())

@app.route('/hosts/<int:host_id>/volumes/<volume_uuid>/delete', methods=['DELETE'])
def host_volumes_delete(host_id, volume_uuid):
    host = R1softHost.query.get(host_id)
    host.conn.Volume.service.deleteVolumeById(volume_uuid)
    return redirect(url_for('host_volumes', host_id=host_id))

@app.route('/hosts/<int:host_id>/agents/')
def host_agents(host_id):
    host = R1softHost.query.get(host_id)
    return render_template('host/agents.html',
        host=host,
        agents=host.conn.Agent.service.getAgents())

@app.route('/hosts/<int:host_id>/agents/<agent_uuid>/delete', methods=['DELETE'])
def host_agents_delete(host_id, agent_uuid):
    host = R1softHost.query.get(host_id)
    host.conn.Agent.service.deleteAgentById(agent_uuid)
    return redirect(url_for('host_agents', host_id=host_id))

@app.route('/hosts/<int:host_id>/disk-safes/')
def host_disksafes(host_id):
    host = R1softHost.query.get(host_id)
    # testing showed this way was about 1 second faster than just
    # doing getDiskSafes()
    disksafes = green_map(
        host.conn.DiskSafe.service.getDiskSafeByID,
        host.conn.DiskSafe.service.getDiskSafeIDs())
    return render_template('host/disksafes.html',
        host=host,
        disksafes=disksafes)

@app.route('/hosts/<int:host_id>/disk-safes/<ds_uuid>/close', methods=['POST'])
def host_disksafes_close(host_id, ds_uuid):
    host = R1softHost.query.get(host_id)
    host.conn.DiskSafe.service.closeDiskSafeById(ds_uuid)
    return redirect(url_for('host_disksafes', host_id=host.id))

@app.route('/hosts/<int:host_id>/disk-safes/<ds_uuid>/open', methods=['POST'])
def host_disksafes_open(host_id, ds_uuid):
    host = R1softHost.query.get(host_id)
    host.conn.DiskSafe.service.openDiskSafeById(ds_uuid)
    return redirect(url_for('host_disksafes', host_id=host.id))

@app.route('/hosts/<int:host_id>/disk-safes/<ds_uuid>/detach', methods=['POST'])
def host_disksafes_detach(host_id, ds_uuid):
    host = R1softHost.query.get(host_id)
    disksafe = host.conn.DiskSafe.service.getDiskSafeByID(ds_uuid)
    host.conn.DiskSafe.service.detachDiskSafe(disksafe)
    return redirect(url_for('host_disksafes', host_id=host.id))

@app.route('/hosts/<int:host_id>/disk-safes/<ds_uuid>/attach', methods=['POST'])
def host_disksafes_attach(host_id, ds_uuid):
    host = R1softHost.query.get(host_id)
    disksafe = host.conn.DiskSafe.service.getDiskSafeByID(ds_uuid)
    host.conn.DiskSafe.service.attachDisksafe(disksafe)
    return redirect(url_for('host_disksafes', host_id=host.id))

@app.route('/hosts/<int:host_id>/disk-safes/<ds_uuid>/delete', methods=['DELETE'])
def host_disksafes_delete(host_id, ds_uuid):
    host = R1softHost.query.get(host_id)
    host.conn.DiskSafe.service.deleteDiskSafeById(ds_uuid)
    return redirect(url_for('host_disksafes', host_id=host.id))

@app.route('/hosts/<int:host_id>/policies/')
def host_policies(host_id):
    host = R1softHost.query.get(host_id)
    return render_template('host/policies.html',
        host=host,
        policies=host.conn.Policy2.service.getPolicies())

@app.route('/hosts/<int:host_id>/policies/<policy_uuid>/run', methods=['POST'])
def host_policies_run(host_id, policy_uuid):
    host = R1softHost.query.get(host_id)
    task = host.conn.Policy2.service.runPolicyByID(policy_uuid)
    return redirect(url_for('task_details', host_id=host_id, task_uuid=task.id))

@app.route('/hosts/<int:host_id>/policies/<policy_uuid>/verify', methods=['POST'])
def host_policies_disksafe_verify(host_id, policy_uuid):
    host = R1softHost.query.get(host_id)
    task = host.conn.Policy2.service.runDiskSafeVerificationByPolicyID(policy_uuid)
    return redirect(url_for('task_details', host_id=host_id, task_uuid=task.id))

@app.route('/hosts/<int:host_id>/policies/<policy_uuid>/enable', methods=['POST'])
def host_policies_enable(host_id, policy_uuid):
    host = R1softHost.query.get(host_id)
    policy = host.conn.Policy2.service.getPolicyById(policy_uuid)
    host.conn.Policy2.service.enablePolicy(policy)
    return redirect(url_for('host_policies', host_id=host_id))

@app.route('/hosts/<int:host_id>/policies/<policy_uuid>/disable', methods=['POST'])
def host_policies_disable(host_id, policy_uuid):
    host = R1softHost.query.get(host_id)
    policy = host.conn.Policy2.service.getPolicyById(policy_uuid)
    host.conn.Policy2.service.disablePolicy(policy)
    return redirect(url_for('host_policies', host_id=host_id))

@app.route('/hosts/<int:host_id>/policies/<policy_uuid>/delete', methods=['DELETE'])
def host_policies_delete(host_id, policy_uuid):
    host = R1softHost.query.get(host_id)
    host.conn.Policy2.service.deletePolicyById(policy_uuid)
    return redirect(url_for('host_policies', host_id=host_id))

@app.route('/hosts/<int:host_id>/recovery-points/')
def host_recovery_points(host_id):
    host = R1softHost.query.get(host_id)
    agents = sorted(host.conn.Agent.service.getAgents(), key=lambda a: a.hostname)
    return render_template('host/recovery_points.html',
        host=host,
        agents=agents)

@app.route('/hosts/<int:host_id>/agents/<agent_uuid>/recovery-points/')
def host_agent_recovery_points(host_id, agent_uuid):
    host = R1softHost.query.get(host_id)
    agent = host.conn.Agent.service.getAgentByID(agent_uuid)
    disksafes = host.conn.DiskSafe.service.getDiskSafesForAgent(agent)
    all_recovery_points = green_map(lambda ds: host.conn.RecoveryPoints2.service.getRecoveryPoints(ds.id, False), disksafes)
    collection_data = {
        ds: recovery_points for ds, recovery_points in zip(disksafes, all_recovery_points)
    }
    return render_template('host/recovery_points/list.html',
        host=host,
        agent=agent,
        collection_data=collection_data)

@app.route('/hosts/<int:host_id>/disk-safes/<ds_uuid>/recovery-points/<int:rp_id>/lock', methods=['POST'])
def host_agent_recovery_points_lock(host_id, ds_uuid, rp_id):
    host = R1softHost.query.get(host_id)
    rp = host.conn.RecoveryPoints2.service.getRecoveryPointByID(ds_uuid, rp_id)
    host.conn.RecoveryPoints2.service.lockRecoveryPoint(rp)
    return redirect(url_for('host_recovery_points', host_id=host.id))

@app.route('/hosts/<int:host_id>/disk-safes/<ds_uuid>/recovery-points/<int:rp_id>/unlock', methods=['POST'])
def host_agent_recovery_points_unlock(host_id, ds_uuid, rp_id):
    host = R1softHost.query.get(host_id)
    rp = host.conn.RecoveryPoints2.service.getRecoveryPointByID(ds_uuid, rp_id)
    host.conn.RecoveryPoints2.service.unlockRecoveryPoint(rp)
    return redirect(url_for('host_recovery_points', host_id=host.id))

@app.route('/hosts/<int:host_id>/disk-safes/<ds_uuid>/recovery-points/<int:rp_id>/merge', methods=['POST'])
def host_agent_recovery_points_merge(host_id, ds_uuid, rp_id):
    host = R1softHost.query.get(host_id)
    rp = host.conn.RecoveryPoints2.service.getRecoveryPointByID(ds_uuid, rp_id)
    host.conn.RecoveryPoints2.service.mergeRecoveryPoint(rp)
    return redirect(url_for('host_recovery_points', host_id=host.id))

@app.route('/hosts/<int:host_id>/disk-safes/<ds_uuid>/recovery-points/<int:rp_id>/')
def host_agent_recovery_points_browse(host_id, ds_uuid, rp_id):
    host = R1softHost.query.get(host_id)
    name = UUIDLink.query.filter_by(disksafe_uuid=ds_uuid).first().disksafe_desc
    rp = host.conn.RecoveryPoints2.service.getRecoveryPointByID(ds_uuid, rp_id)
    return render_template('host/recovery_points/browse.html',
        host=host,
        name=name,
        disksafe_id=ds_uuid,
        recovery_point=rp)

@app.route('/hosts/<int:host_id>/disk-safes/<ds_uuid>/recovery-points/<int:rp_id>/fs-data/<path_b64>')
def host_agent_recovery_points_browse_data(host_id, ds_uuid, rp_id, path_b64):
    path = path_b64.decode('base64')
    host = R1softHost.query.get(host_id)
    rp_svc = host.conn.RecoveryPoints2.service
    rp = rp_svc.getRecoveryPointByID(ds_uuid, rp_id)
    try:
        dir_entries = rp_svc.getDirectoryEntries(rp, path)
    except Exception as err:
        app.logger.exception(err)
        file_entries = []
    else:
        API_LIST_LENGTH_LIMIT = 500 # Hard-coded files-per-call limit in API
        if len(dir_entries) > API_LIST_LENGTH_LIMIT:
            app.logger.debug('Path contains too many files for a single API request: [%d] %s',
                len(dir_entries), path)
            file_entries = itertools.chain(
                *green_map(
                    lambda de: rp_svc.getMultipleFileEntryInformation(rp, path, de),
                    split_by(dir_entries, API_LIST_LENGTH_LIMIT)))
        else:
            file_entries = rp_svc.getMultipleFileEntryInformation(rp, path, dir_entries)
    return render_template('host/recovery_points/entries.html',
        url_for_entry=lambda e: url_for('host_agent_recovery_points_browse_data',
            host_id=host.id, ds_uuid=ds_uuid, rp_id=rp_id, path_b64=path_join(path, e.filePath).encode('base64').rstrip()),
        entries=file_entries)

@app.route('/hosts/<int:host_id>/disk-safes/<ds_uuid>/recovery-points/<int:rp_id>/confirm-restore', methods=['POST'])
def host_agent_recovery_points_restore(host_id, ds_uuid, rp_id):
    host = R1softHost.query.get(host_id)
    rp = host.conn.RecoveryPoints2.service.getRecoveryPointByID(ds_uuid, rp_id)
    name = UUIDLink.query.filter_by(disksafe_uuid=ds_uuid).first().disksafe_desc
    file_names = request.form.getlist('file_names')
    form = RestoreForm(file_names=file_names)
    form.file_names.choices=[(f, f) for f in file_names]
    return render_template('host/recovery_points/restore.html',
        host=host,
        disksafe_id=ds_uuid,
        name=name,
        recovery_point=rp,
        restore_form=form)

@app.route('/hosts/<int:host_id>/disk-safes/<ds_uuid>/recovery-points/<int:rp_id>/restore', methods=['POST'])
def host_agent_recovery_points_restore_action(host_id, ds_uuid, rp_id):
    host = R1softHost.query.get(host_id)
    rp = host.conn.RecoveryPoints2.service.getRecoveryPointByID(ds_uuid, rp_id)
    restore_opts = host.conn.RecoveryPoints2.factory.create('fileRestoreOptions')
    restore_form = RestoreForm()
    restore_opts.basePath = restore_form.base_path.data
    restore_opts.fileNames = restore_form.file_names.data
    restore_opts.useCompression = restore_form.use_compression.data
    restore_opts.overwriteExistingFiles = restore_form.overwrite_existing.data
    restore_opts.estimateRestoreSize = restore_form.estimate_size.data
    if restore_form.restore_target.data == 'alt_host':
        restore_opts.useOriginalHost = False
        restore_opts.alternateHostname = restore_form.alt_restore_host.data
        restore_opts.alternateHostPort = restore_form.alt_restore_port.data
    else:
        restore_opts.useOriginalHost = True
    if restore_form.alt_restore_location.data:
        restore_opts.restoreToAlternateLocation = True
        restore_opts.alternateLocationPath = restore_form.alt_restore_location.data
    else:
        restore_opts.restoreToAlternateLocation = False

    task = host.conn.RecoveryPoints2.service.doFileRestore(rp, restore_opts)
    return redirect(url_for('task_details', host_id=host_id, task_uuid=task.id))

@app.route('/hosts/<int:host_id>/tasks/')
def host_task_history(host_id):
    host = R1softHost.query.get(host_id)
    tasks = inflate_tasks(host,
        host.conn.TaskHistory.service.getTaskExecutionContextIDs(
            scheduledStart=str(datetime.date.today() - \
                datetime.timedelta(app.config['R1SOFT_TASK_HISTORY_DAYS']))),
        with_alert_ids=True)
    agent_names = [UUIDLink.query.filter_by(agent_uuid=task.agentId).first().agent_hostname \
            if hasattr(task, 'agentId') else 'SYSTEM' \
        for task in tasks]
    return render_template('host/task_history.html',
        host=host,
        tasks=zip(tasks, agent_names))

@app.route('/hosts/<int:host_id>/tasks/<task_uuid>/rerun', methods=['POST'])
def host_task_history_rerun(host_id, task_uuid):
    host = R1softHost.query.get(host_id)
    host.conn.TaskHistory.service.runTaskByTaskExecutionContextID(task_uuid)
    return redirect(url_for('host_task_history', host_id=host.id))

@app.route('/hosts/<int:host_id>/tasks/<task_uuid>/cancel', methods=['POST'])
def host_task_history_cancel(host_id, task_uuid):
    host = R1softHost.query.get(host_id)
    host.conn.TaskHistory.service.cancelTaskByTaskExecutionContextID(task_uuid)
    return redirect(url_for('task_details', host_id=host.id, task_uuid=task_uuid))

@app.route('/hosts/<int:host_id>/users/')
def host_users(host_id):
    host = R1softHost.query.get(host_id)
    users = host.conn.User.service.getUsers()
    return render_template('host/users.html',
        host=host,
        users=users)

@app.route('/hosts/<int:host_id>/users/<user_uuid>/disable', methods=['POST'])
def host_users_disable(host_id, user_uuid):
    host = R1softHost.query.get(host_id)
    host.conn.User.service.updateUser() #switch off
    return redirect(url_for('host_users', host_id=host_id))

@app.route('/hosts/<int:host_id>/users/<user_uuid>/enable', methods=['POST'])
def host_users_enable(host_id, user_uuid):
    host = R1softHost.query.get(host_id)
    host.conn.User.service.updateUser() #switch on
    return redirect(url_for('host_users', host_id=host_id))

@app.route('/hosts/<int:host_id>/users/<user_uuid>/delete', methods=['DELETE'])
def host_users_delete(host_id, user_uuid):
    host = R1softHost.query.get(host_id)
    host.conn.User.service.deleteUserById(user_uuid)
    return redirect(url_for('host_users', host_id=host_id))

@app.route('/hosts/<int:host_id>/configuration/')
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

@app.route('/hosts/<int:host_id>/api-proxy/<namespace>/<method>', methods=['POST'])
def host_api_proxy(host_id, namespace, method):
    raise NotImplementedError()

    host = R1softHost.query.get(host_id)
    soap_method = getattr(getattr(host.conn, namespace).service, method)
    params = request.get_json()
    if params is None:
        pargs = []
        kwargs = {}
    else:
        pargs = params['pargs']
        kwargs = params['kwargs']
    response = {'response': None, 'error': None}
    try:
        response['response'] = soap2native(soap_method(*pargs, **kwargs))
    except Exception as err:
        response['error'] = {'class': err.__class__.__name__, 'message': str(err)}
    return jsonify(response)

@app.route('/hosts/<int:host_id>/agents/<agent_uuid>/')
def agent_details(host_id, agent_uuid):
    host = R1softHost.query.get(host_id)
    agent = host.conn.Agent.service.getAgentByID(agent_uuid)
    if agent.osType != 'UNKNOWN':
        try:
            remote_opts = host.conn.Agent.service.getRemoteAgentOptions(agent.id)
        except Exception as err:
            app.logger.exception(err)
            remote_opts = False
    else:
        remote_opts = False
    links = search_uuid_map(agent.hostname, agent.description)
    return render_template('host/details/agent.html',
        host=host,
        links=links,
        agent_opts=remote_opts,
        agent=agent)

@app.route('/hosts/<int:host_id>/disk-safes/<disksafe_uuid>/')
def disksafe_details(host_id, disksafe_uuid):
    host = R1softHost.query.get(host_id)
    disksafe = host.conn.DiskSafe.service.getDiskSafeByID(disksafe_uuid)
    links = search_uuid_map(disksafe.description)
    return render_template('host/details/disksafe.html',
        host=host,
        links=links,
        disksafe=disksafe)

@app.route('/hosts/<int:host_id>/volumes/<volume_uuid>/')
def volume_details(host_id, volume_uuid):
    host = R1softHost.query.get(host_id)
    volume = host.conn.Volume.service.getVolumeById(volume_uuid)
    return render_template('host/details/volume.html',
        host=host,
        volume=volume)

@app.route('/hosts/<int:host_id>/policies/<policy_uuid>/')
def policy_details(host_id, policy_uuid):
    host = R1softHost.query.get(host_id)
    policy = host.conn.Policy2.service.getPolicyById(policy_uuid)
    links = search_uuid_map(policy.name, policy.description)
    if policy.state in ('ERROR', 'ALERT'):
        agent_uuid = [l for l in links if l.policy_uuid == policy_uuid][0].agent_uuid
        task_ids = host.conn.TaskHistory.service.getTaskExecutionContextIDs(
            scheduledStart=str(policy.lastReplicationRunTime.date()),
            hasAlerts=True, taskStates=['FINISHED', 'ERROR'],
            taskTypes=['DATA_PROTECTION_POLICY'],
            agents=[agent_uuid])
        task_link = url_for('task_details', host_id=host_id, task_uuid=task_ids[-1])
    else:
        task_link = False
    return render_template('host/details/policy.html',
        host=host,
        links=links,
        task_link=task_link,
        policy=policy)

@app.route('/hosts/<int:host_id>/tasks/<task_uuid>/')
def task_details(host_id, task_uuid):
    host = R1softHost.query.get(host_id)
    task = inflate_task_logs(host, inflate_task_alerts(host,
        host.conn.TaskHistory.service.getTaskExecutionContextByID(task_uuid)))
    if hasattr(task, 'agentId'):
        link = UUIDLink.query.filter_by(agent_uuid=task.agentId).first()
        if task.taskType == 'FILE_RESTORE':
            task.fileRestoreStatistics = host.conn.TaskHistory.service.getFileRestoreStatistics(task.id)
        if task.taskType == 'MERGE_RECOVERY_POINTS':
            task.mergeStatistics = host.conn.TaskHistory.service.getMergeStatistics(task.id)
    else:
        link = False
    return render_template('host/details/task.html',
        host=host,
        link=link,
        task=task)

@app.route('/policy-directory/')
def policy_directory_collection():
    return render_template('policy_directory_collection.html')

@app.route('/hosts/<int:host_id>/policy-directory-data/')
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
