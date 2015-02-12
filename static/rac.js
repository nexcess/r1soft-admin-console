/**
 * Nexcess.net r1soft-admin-console
 * Copyright (C) 2015  Nexcess.net L.L.C.
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License along
 * with this program; if not, write to the Free Software Foundation, Inc.,
 * 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
 */

/**
 * Shamelessly taken because I hate JS
 * @link http://kilianvalkhof.com/2010/javascript/how-to-build-a-fast-simple-list-filter-with-jquery/
 */

 function agent_collection_updateAgentList(idx, host) {
    $("#host-group-item-"+host.id).attr({class: "list-group-item list-group-item-default"});
    $("#host-spinner-"+host.id).show();
    $.getJSON(host.url_list_clients_json,
        function(response_data) {
            $.each(response_data, function(policy_id, data) {
                if(!data.agent) {
                    $("#host-group-item-"+host.id).addClass("list-group-item-warning");
                    return;
                }
                var row = $("<tr>").attr({id: policy_id}),
                    type = $("<td>"),
                    hostname = $("<td>").text(data.agent.hostname),
                    description = $("<td>").text(data.agent.description),
                    cdp_host = $("<td>").html("<a href=\""+host.external_link+"\">"+host.hostname+"</a>"),
                    rp_limit = $("<td>").text(data.policy.recoveryPointLimit),
                    db_module = $("<td>"),
                    state = $("<td>").text(data.policy.state);
                if(data.agent.databaseAddOnEnabled &&
                        data.policy.databaseInstanceList &&
                        data.policy.databaseInstanceList.length > 0) {
                    db_module.html("<span class=\"label label-success\">Yes</span>");
                } else {
                    db_module.html("<span class=\"label label-danger\">No</span>");
                }
                switch(data.agent.osType) {
                    case "LINUX":
                        $(type).append($("<i>").attr({title: data.agent.osType,
                            class: "fa fa -lg fa-linux"}));
                        break;
                    default:
                        $(type).append($("<i>").attr({title: data.agent.osType,
                            class: "fa fa -lg fa-question-circle"}));
                }
                switch(data.policy.state) {
                    case "ERROR":
                        $(row).attr({class: "danger"});
                        break;
                    case "ALERT":
                        $(row).attr({class: "warning"});
                        break;
                    case "OK":
                        $(row).attr({class: "success"});
                        break;
                }
                if(!data.policy.enabled) {
                    $(row.attr({class: "default"}));
                }

                $.each([type, hostname, description, cdp_host, rp_limit, db_module, state],
                    function(i, v) {
                        $(row).append(v);
                    });
                $(row).appendTo($("#agents-list-table"));
            });

            $("#host-group-item-"+host.id).addClass("list-group-item-success");
            $("#agents-list-table").trigger("update");
        }
    ).fail(function() {
        $("#host-group-item-"+host.id).addClass("list-group-item-danger")
            .click(function() {
                agent_collection_updateAgentList(idx, host)
            });
    }).always(function() {
        $("#host-spinner-"+host.id).hide();
    });
 }
