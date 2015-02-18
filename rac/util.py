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
from rac.models import R1softHost, UUIDLink, or_, and_

import gevent.pool
from suds.sudsobject import asdict
from flask import Markup
from humanize import naturalsize


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
    # 'REPLICATING':      '',
    # 'AVAILABLE':        '',
    # 'MERGING':          '',
    # 'MERGED':           '',
    # 'LOCKED':           '',
    # 'REPLICATION_INTERRUPTED':   '',
    # 'MERGE_INTERRUPTED':'',

    # TaskState
    'FINISHED':         'fa fa-check-circle-o text-success',
    'RUNNING':          'fa fa-spinner fa-spin text-primary',
    'QUEUED':           'fa fa-pause text-info',
    'CANCELLED':        'fa fa-times-circle-o text-danger',
    'DUPLICATE':        'fa fa-files-o text-warning',

    # TaskType
    'DATA_PROTECTION_POLICY':   'fa fa-clipboard',
    'FILE_RESTORE':     'fa fa-files-o text-info',
    'MERGE_RECOVERY_POINTS':    'fa fa-cubes text-primary',
    'EMAIL_REPORT':     'fa fa-envelope-o text-primary',
    'SYSTEM':           'fa fa-cogs',
    'TASK_HISTORY_CLEANUP':     'fa fa-expand text-success',

    # Log Level
    'INFO':             'fa fa-flag text-info',
    'WARNING':          'fa fa-flag text-warning',
    'SEVERE':           'fa fa-flag text-danger',

    # Log Source
    'SERVER':           'fa fa-server text-primary',
    'AGENT':            'fa fa-desktop text-primary',

    # UserType
    'SUPER_USER':       'fa fa-user-plus text-primary',
    'SUB_USER':         'fa fa-child',
    'POWER_USER':       'fa fa-user',

    # ReportType
    # 'TASK_HISTORY':     '',
    # 'SERVER_BACKUP':    '',
    # 'QUOTA_ALERT':      '',

    # Special/shared values
    True:               'fa fa-check text-success',
    False:              'fa fa-times text-danger',
    '':                 'fa fa-times text-danger',
    'ERROR':            'fa fa-exclamation-circle text-danger',
    'UNKNOWN':          'fa fa-question-circle',
    'NEW':              'fa fa-eye-slash',
    'STUCK':            'fa fa-pause text-danger',
    'DISABLED':         'fa fa-times text-default',
    'ENABLED':          'fa fa-check text-primary',
}

API_POOL = gevent.pool.Pool(size=app.config['R1SOFT_API_CONCURRENCY'])


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

def inflate_tasks(host, task_id_list, with_alert_ids=False, with_log_message_ids=False):
    get_task_func = host.conn.TaskHistory.service.getTaskExecutionContextByID
    tasks = green_map(get_task_func, task_id_list)
    if with_alert_ids:
        get_alert_ids_func = host.conn.TaskHistory.service.getAlertIDsByTaskExecutionContextID
        def add_alerts(task):
            task.alertIDs = get_alert_ids_func(task.id)
        green_map(add_alerts, tasks)
    if with_log_message_ids:
        get_message_ids_func = host.conn.TaskHistory.service.getLogMessageIDsByTaskExecutionContextID
        def add_messages(task):
            task.logMessageIDs = get_message_ids_func(task.id)
        green_map(add_messages, tasks)
    return tasks

def inflate_task_alerts(host, task):
    if not hasattr(task, 'alertIDs'):
        task.alertIDs = host.conn.TaskHistory.service.getAlertIDsByTaskExecutionContextID(task.id)
    task.alerts = green_map(lambda aid: host.conn.TaskHistory.service.getAlertByID(task.id, aid), task.alertIDs)
    return task

def inflate_task_logs(host, task):
    if not hasattr(task, 'logMessageIDs'):
        task.logMessageIDs = host.conn.TaskHistory.service.getLogMessageIDsByTaskExecutionContextID(task.id)
    task.logMessages = green_map(lambda mid: host.conn.TaskHistory.service.getLogMessageByID(task.id, mid), task.logMessageIDs)
    return task

def search_uuid_map(*search_terms):
    search_fields = ['policy_name', 'disksafe_desc', 'agent_hostname']
    conditions = [getattr(UUIDLink, field).__eq__(search_term) \
            for field in search_fields \
        for search_term in search_terms]
    return UUIDLink.query.filter(or_(*conditions)).all()

def green_map(func, iterable):
    return API_POOL.map(func, iterable)

@app.context_processor
def inject_hosts():
    return {'NAV_hosts': R1softHost.query.filter_by(active=True)}

@app.context_processor
def inject_thing():
    return {'active_elements': [], 'search_uuid_map': search_uuid_map}

@app.context_processor
def inject_obj_attr_filter():
    return {'obj_attr_filter':
        lambda obj_list, attr, value: [o for o in obj_list if getattr(o, attr) == value]}

@app.template_filter('iconize')
def iconize_filter(s):
    icon_opts = ICONIZE_MAP.get(s, ICONIZE_MAP.get('UNKNOWN'))
    return Markup('<i title="{title}" class="{icon_opts} fa-lg"><span style="display:none">{title}</span></i>'.format(
        title=Markup(str(s).replace('_', ' ').title()),
        icon_opts=icon_opts))

@app.template_filter('naturalsize')
def naturalsize_filter(s):
    return naturalsize(s)
