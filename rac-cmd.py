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

from rac import app, db, manager
from rac.models import R1softHost, UUIDLink
from rac.util import green_map

from sqlalchemy.exc import IntegrityError
from r1soft.util import read_config
from urllib2 import URLError
from ssl import SSLError


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
            agents = host.conn.Agent.service.getAgents()
            app.logger.debug('Pulled %d agent objects from API', len(agents))
            disksafes = [ds for ds in green_map(
                    host.conn.DiskSafe.service.getDiskSafeByID,
                    host.conn.DiskSafe.service.getDiskSafeIDs()) \
                if hasattr(ds, 'agentID')]
            app.logger.debug('Pulled %d disk safe objects from API', len(disksafes))
            policies = [p for p in host.conn.Policy2.service.getPolicies() \
                if hasattr(p, 'diskSafeID')]
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
        app.logger.info('Deleting old mappings')
        UUIDLink.query.filter_by(host_id=host.id).delete()
        app.logger.info('Preparing to create mappings')
        for agent in agents:
            agent_disksafes = [ds for ds in disksafes if ds.agentID == agent.id]
            for disksafe in agent_disksafes:
                disksafe_policies = [p for p in policies if p.diskSafeID == disksafe.id]
                for policy in disksafe_policies:
                    map_link = UUIDLink(host.id, agent.id, disksafe.id, policy.id,
                        agent_hostname=agent.hostname, disksafe_desc=disksafe.description,
                        policy_name=policy.name)
                    db.session.add(map_link)
                    try:
                        db.session.commit()
                    except IntegrityError:
                        db.session.rollback()
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

@manager.command
def create_db():
    db.create_all()

@manager.command
def run_server():
    app.run(host='0.0.0.0')

if __name__ == '__main__':
    manager.run()
