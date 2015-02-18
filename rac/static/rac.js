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

// worst naming scheme ever
base64decode = atob
base64encode = btoa

function getUpdateDataListTable(tSelector) {
    return function(host) {
        $("#host-group-item-"+host.id).attr({class: "list-group-item list-group-item-default"});
        $("#host-spinner-"+host.id).show();
        $("#host-spinner-"+host.id).addClass("fa-spin");
        $.get(host.data_url,
            function(response) {
                $(tSelector + ">tbody").append(response);
                $(tSelector).trigger("update");
            }
        ).done(function() {
            $("#host-group-item-"+host.id).addClass("list-group-item-success");
            $("#host-spinner-"+host.id).hide();
        }).fail(function() {
            $("#host-group-item-"+host.id).addClass("list-group-item-danger");
            addFlashMessage("danger", "<strong>"+host.hostname+"</strong> failed to load");
        }).always(function() {
            $("#host-spinner-"+host.id).removeClass("fa-spin");
        });
    };
}

function addFlashMessage(status, content) {
    var message = $("<div>").attr({
        class: "alert alert-dismissable alert-"+status,
        role: "alert",
    }).append($("<button>").attr({
        type: "button",
        class: "close",
        'data-dismiss': "alert",
        'aria-label': "Close",
    }).append($("<i>").attr({
        class: "fa fa-close",
        'aria-hidden': "true",
    }))).append(content);
    $("#message-area").append(message);
}
