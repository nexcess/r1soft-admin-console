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

// custom css expression for a case-insensitive contains()
jQuery.expr[':'].Contains = function(a,i,m){
    return (a.textContent || a.innerText || "").toUpperCase().indexOf(m[3].toUpperCase())>=0;
};

function listFilter(attach_point, collection, filter_item) {
    // header is any element, list is an unordered list

    // create and add the filter form to the header
    var form = $("<form>").attr({"class":"filterform pull-right", "action":"#"}),
        input = $("<input>").attr({"class":"filterinput", "type":"text",
            "placeholder": "Search..."});
    $(form).append(input).appendTo(attach_point);

    $(input).change(function () {
        var filter = $(this).val();
        if(filter) {
            // this finds all links in a list that contain the input,
            // and hide the ones not containing the input while showing the ones that do
            $(collection).find(filter_item + ":not(:Contains(" + filter + "))").parent().hide();
            $(collection).find(filter_item + ":Contains(" + filter + ")").parent().show();
        } else {
            $(collection).find(filter_item).show();
        }
        return false;
    }).keyup(function () {
        // fire the above change event after every letter
        $(this).change();
    });
};
