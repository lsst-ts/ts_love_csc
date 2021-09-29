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

import unittest

from lsst.ts.love.csc.utils import get_available_components, parse_auth_request


class UtilsTestCase(unittest.TestCase):
    def test_get_available_components(self):
        available_components = get_available_components()

        self.assertIn("LOVE", available_components)

    def test_parse_auth_request(self):

        request = "+user1@node1,+user2@node2,-user3@node3"

        to_add, to_remove = parse_auth_request(request)

        self.assertEqual({"user1@node1", "user2@node2"}, to_add)
        self.assertEqual({"user3@node3"}, to_remove)

    def test_parse_auth_request_fail(self):

        request = "+user1@node1,+user2@node2,-user3@node3,bad@request"

        with self.assertRaises(RuntimeError):
            parse_auth_request(request)


if __name__ == "__main__":
    unittest.main()
