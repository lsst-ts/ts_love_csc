# This file is part of ts_love_csc.
#
# Developed for Vera C. Rubin Observatory Telescope and Site Systems.
# This product includes software developed by the LSST Project
# (https://www.lsst.org).
# See the COPYRIGHT file at the top-level directory of this distribution
# for details of code ownership.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import re

from lsst.ts import idl


def get_available_components():
    """Return a list of all CSCs available in the idl directory.

    Returns
    -------
    `set` of `str`
        CSCs with idl files in the idl directory.
    """
    pattern_match = re.compile("sal_revCoded_(.*)")

    return {
        pattern_match.findall(idl_files.stem)[0]
        for idl_files in idl.get_idl_dir().glob("*.idl")
        if pattern_match.match(idl_files.stem) is not None
    }


def parse_auth_request(request):
    """Parse input request string.

    Returns
    -------
    to_add : `set`
        Requests to add.
    to_remove : `set`
        Request to remove.
    """

    if len(request) == 0:
        return set(), set()

    request_as_set = set(request.split(","))

    to_add = {item[1:] for item in request_as_set if item.startswith("+")}

    to_remove = {item[1:] for item in request_as_set if item.startswith("-")}

    union = to_add.union(to_remove)
    if len(union) != len(request_as_set):

        bad_entries = {
            item
            for item in request_as_set
            if not item.startswith("+") and not item.startswith("-")
        }

        raise RuntimeError(
            f"Bad input parameter: {request}. "
            "Requests must be preceded by a + or - sign to indicate the intention to "
            "add or remove them from the auth list. "
            f"The following entries are invalid: {bad_entries}."
        )

    return to_add, to_remove
