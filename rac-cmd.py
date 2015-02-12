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

from sqlalchemy.exc import IntegrityError
from r1soft.util import read_config
from urllib2 import URLError
from ssl import SSLError

from rac import app, db, manager, R1softHost, UUIDLink


@manager.command
def populate_uuid_map(host=''):
    app.logger.info('Populating the UUID Map table')
    if host:
        hosts_list = R1softHost.query.filter_by(hostname=host)
    else:
        hosts_list = R1softHost.query.filter_by(active=True)
    for host in hosts_list:
        app.logger.info('Updating map links for host[%d]: %s', host.id, host.hostname)
        try:
            disksafes = host.conn.DiskSafe.service.getDiskSafes()
            app.logger.debug('Pulled %d disk safe objects from API', len(disksafes))
            policies = host.conn.Policy2.service.getPolicies()
            app.logger.debug('Pulled %d policy objects from API', len(policies))
        except (URLError, SSLError) as err:
            app.logger.warning('Error connecting to host: %s', host.hostname)
            app.logger.exception(err)
            app.logger.info('Marking inactive and skipping')
            host.active = False
            db.session.add(host)
            db.session.commit()
            continue
        else:
            if not host.active:
                host.active = True
                db.session.add(host)
                db.session.commit()

        app.logger.info('Preparing to create mappings')
        for policy in policies:
            policy_uuid = policy.id
            if not hasattr(policy, 'diskSafeID'):
                app.logger.warning('Policy has no disk safe ID: %r', policy)
                continue
            disksafe_uuid = policy.diskSafeID
            agent_uuid = [d.agentID for d in disksafes if d.id == disksafe_uuid][0]
            map_link = UUIDLink(host.id, agent_uuid, disksafe_uuid, policy_uuid)
            app.logger.debug('Created mapping for policy [%s:%s]: %r',
                policy.name, policy.id, map_link)

            db.session.add(map_link)
            try:
                db.session.commit()
                app.logger.debug('Mapping successfully committed...')
            except IntegrityError:
                db.session.rollback()
                app.logger.debug('Mapping already exists, skipping...')
                continue
    app.logger.info('Finished populating UUID Map table')

@manager.command
def import_old_config(old_config_filename):
    old_config = read_config(old_config_filename)
    for old_line in old_config:
        if old_line['version'] < 3:
            app.logger.warning('Skipping unsupported old version of CDP: %r', old_line)
            continue
        new_host = R1softHost(old_line['hostname'], old_line['username'],
            old_line['password'], api_port=old_line['port'], api_ssl=bool(old_line['ssl']))
        db.session.add(new_host)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            continue


if __name__ == '__main__':
    manager.run()
