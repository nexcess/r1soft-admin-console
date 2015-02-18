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

from rac.models import R1softHost

from wtforms_alchemy import ModelForm
from flask.ext.wtf import Form
from wtforms import IntegerField, BooleanField, StringField
from wtforms.validators import NumberRange, InputRequired

class R1softHostForm(ModelForm):
    class Meta:
        model = R1softHost

class HostConfigurationForm(Form):
    hard_quota              = IntegerField('Manager Disk Space (Hard Quota)',
                                [NumberRange(min=1, max=99)])
    soft_quota              = IntegerField('Manager Disk Space (Soft Quota)',
                                [NumberRange(min=1, max=99)])

    task_history_limit      = IntegerField('Days to retain Task History',
                                [NumberRange(min=1, max=365)])

    http_enabled            = BooleanField('Enabled')
    http_port               = IntegerField('Port',
                                [NumberRange(min=1, max=65535)])
    http_max_conn           = IntegerField('Max Connections',
                                [NumberRange(min=1, max=9999)])

    https_enabled           = BooleanField('Enabled')
    https_port              = IntegerField('Port',
                                [NumberRange(min=1, max=65535)])
    https_keystore          = StringField('Keystore Path')
    https_max_conn          = IntegerField('Max Connections',
                                [NumberRange(min=1, max=9999)])
