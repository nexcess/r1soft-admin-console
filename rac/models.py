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

from rac import app, db

from r1soft.cdp3 import CDP3Client
from flask import Markup, url_for
from sqlalchemy import or_, and_
import datetime


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
    def link(self):
        html = '<a href="{internal_link}">{hostname}</a>' + \
            '<a href="{external_link}"><i class="fa fa-external-link icon-space-left"></i></a>'
        return Markup(html.format(internal_link=self.internal_url,
            hostname=self.hostname,
            external_link=self.external_url))

    @property
    def internal_url(self):
        return url_for('host_details', host_id=self.id)

    @property
    def external_url(self):
        return Markup('{scheme}://{hostname}:{web_port}/'.format(
            scheme='https' if self.web_ssl else 'http',
            hostname=self.hostname,
            web_port=self.web_port))

    @property
    def server_time(self):
        # we should check with the server to find out what time it thinks it is
        # and use that for correct time deltas but there doesn't seem to be an
        # API method to get it so we'll just fake it with this for now
        return datetime.datetime.now()

class UUIDLink(db.Model):
    id              = db.Column(db.Integer(), primary_key=True)
    host_id         = db.Column(db.Integer(), db.ForeignKey('r1soft_host.id'))
    agent_uuid      = db.Column(db.String(36), nullable=False, index=True)
    agent_hostname  = db.Column(db.String(255))
    disksafe_uuid   = db.Column(db.String(36))
    disksafe_desc   = db.Column(db.String(255))
    policy_uuid     = db.Column(db.String(36))
    policy_name     = db.Column(db.String(255))

    __table_args__  = (db.UniqueConstraint('agent_uuid', 'disksafe_uuid', 'policy_uuid', name='uuid_constraint'),)

    _host           = None

    def __init__(self, host_id, agent_uuid, disksafe_uuid, policy_uuid,
            agent_hostname='', disksafe_desc='', policy_name=''):
        self.host_id = host_id
        self.agent_uuid = agent_uuid
        self.agent_hostname = agent_hostname
        self.disksafe_uuid = disksafe_uuid
        self.disksafe_desc = disksafe_desc
        self.policy_uuid = policy_uuid
        self.policy_name = policy_name

    @property
    def host(self):
        if self._host is None:
            self._host = R1softHost.query.get(self.host_id)
        return self._host

    @property
    def agent(self):
        return self.host.conn.Agent.service.getAgentByID(self.agent_uuid)

    @property
    def agent_url(self):
        return url_for('agent_details', host_id=self.host.id, agent_uuid=self.agent_uuid)

    @property
    def disksafe(self):
        return self.host.conn.DiskSafe.service.getDiskSafeByID(self.disksafe_uuid) \
            if self.disksafe_uuid else None

    @property
    def disksafe_url(self):
        return url_for('disksafe_details', host_id=self.host.id, disksafe_uuid=self.disksafe_uuid) \
            if self.disksafe_uuid else '#'

    @property
    def policy(self):
        return self.host.conn.Policy2.service.getPolicyById(self.policy_uuid) \
            if self.policy_uuid else None

    @property
    def policy_url(self):
        return url_for('policy_details', host_id=self.host.id, policy_uuid=self.policy_uuid) \
            if self.policy_uuid else '#'

class PolicyTemplate(db.Model):
    R1SOFT_FREQUENCY_TYPES = [
        'ON_DEMAND',
        'MINUTELY',
        'HOURLY',
        'DAILY',
        'WEEKLY',
        'MONTHLY',
        'YEARLY',
    ]

    id                              = db.Column(db.Integer(), primary_key=True)

    replication_frequency           = db.Column(db.Enum(*R1SOFT_FREQUENCY_TYPES, name='rep_freq'), nullable=False)
    replication_frequency_values    = db.Column(db.String(255))

    merge_frequency                 = db.Column(db.Enum(*R1SOFT_FREQUENCY_TYPES, name='merge_freq'), nullable=False)
    merge_frequency_values          = db.Column(db.String(255))

    verification_frequency          = db.Column(db.Enum(*R1SOFT_FREQUENCY_TYPES, name='verif_freq'), nullable=False)
    verification_frequncy_values    = db.Column(db.String(255))

    enabled                         = db.Column(db.Boolean(), nullable=False)
    recovery_point_limit            = db.Column(db.Integer(), nullable=False)
    force_full_block_scan           = db.Column(db.Boolean(), nullable=False)

    backup_database                 = db.Column(db.Boolean(), nullable=False)
    database_type                   = db.Column(db.String(255))
    database_name                   = db.Column(db.String(255))
    database_hostname               = db.Column(db.String(255))
    database_port                   = db.Column(db.Integer())
    database_username               = db.Column(db.String(255))
    database_username               = db.Column(db.String(255))
    database_data_dir               = db.Column(db.String(4096))
    database_install_dir            = db.Column(db.String(4096))

    def __init__(self, **kwargs):
        for k, v in kwargs.iteritems():
            setattr(self, k, v)

    def populate_new_policy_object(self, host, disksafe_uuid):
        """Create and populate a `policy` object with the value saved to this
        template in the database

        Note that the `name` and `description` fields will still need to be
        populated in the returned object
        """

        create_type = host.conn.Policy2.factory.create
        policy = create_type('policy')
        freq_type = create_type('frequencyType')

        policy.enabled = self.enabled
        policy.recoveryPointLimit = self.recovery_point_limit
        policy.forceFullBlockScan = self.force_full_block_scan

        if self.replication_frequency:
            policy.replicationScheduleFrequencyType = freq_type[self.replication_frequency]
            policy.replicationScheduleFrequencyValues = self._populateFrequencyValues(
                host, self.replication_frequency, self.replication_frequency_values)
        if self.merge_frequency:
            policy.mergeScheduleFrequencyType = freq_type[self.merge_frequency]
            policy.mergeScheduleFrequencyValues = self._populateFrequencyValues(
                host, self.merge_frequency, self.merge_frequency_values)
        if self.verification_frequency:
            policy.verificationScheduleFrequencyType = freq_type[self.verification_frequency]
            policy.verificationScheduleFrequencyValues = self._populateFrequencyValues(
                host, self.verification_frequency, self.verification_frequency_values)

        if self.backup_database:
            db_type = create_type('dataBaseType')
            db_instance = create_type('databaseInstance')
            db_instance.dataBaseType = db_type[self.database_type]
            db_instance.name = self.database_name
            db_instance.username = self.database_username
            db_instance.password = self.database_password
            if self.database_hostname:
                db_instance.hostName = self.database_hostname
                db_instance.useAlternateHostname = True
            else:
                db_instance.useAlternateHostname = False
            db_instance.portNumber = self.database_port
            if self.database_data_dir:
                db_instance.dataDirectory = self.database_data_dir
                db_instance.useAlternateDataDirectory = True
            else:
                db_instance.useAlternateDataDirectory = False
            if self.database_install_dir:
                db_instance.installDirectory = self.database_install_dir
                db_instance.useAlternateInstallDirectory = True
            else:
                db_instance.useAlternateInstallDirectory = False

            policy.databaseInstanceList = [db_instance]

        return policy

    def _populateFrequencyValues(self, host, freq, value_string):
        """Populate a `frequencyValues` object based on the database-stored
        values

        value_string should be in a semi-colon (:) delimited format with 3 fields

        startingMinute:startingHour:comma,delimited,list

        Not all fields are used in all frequency types, but some examples:

            Daily at 0630 and 1430              -> 30::6,14
            Tues and Thurs (weekly) at 1945     -> 45:19:TUESDAY,THURSDAY
            1st and 15th (monthly) at 0700      -> 0:7:1,15
            Jan 1st at 0001 (yearly)            -> 1:0:1,JANUARY

        Note that YEARLY is special in that the 1st value of the third field
        indicates what day of every indicated month to run on
        """

        freq_values = host.conn.Policy2.factory.create('frequencyValues')
        if freq != 'ON_DEMAND':
            (start_min, start_hour, interval) = value_string.split(':')
            freq_values.startingMinute = int(start_min) if start_min else 0
            freq_values.startingHour = int(start_hour) if start_hour else 0

            if freq == 'MINUTELY':
                freq_values.minutelyValue = int(interval)
            elif freq == 'HOURLY':
                freq_values.minutelyValue = int(interval)
            elif freq == 'DAILY':
                freq_values.hoursOfDay = [int(i) for i in interval.split(',')]
            elif freq == 'WEEKLY':
                freq_values.daysOfWeek = [i.upper() for i in interval.split(',')]
            elif freq == 'MONTHLY':
                # TODO: there is probably a special value for the last day of
                # the month, need to figure out what it is at some point. also
                # applies to dayOfMonth for YEARLY
                freq_values.daysOfMonth = [int(i) for i in interval.split(',')]
            elif freq == 'YEARLY':
                interval_values = [i.upper() for i in interval.split(',')]
                freq_values.dayOfMonth = int(interval_values[0])
                freq_values.monthsOfYear = interval_values[1:]

        return freq_values
