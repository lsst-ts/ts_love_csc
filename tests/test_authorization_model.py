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

import types
import unittest

from lsst.ts.love.csc.authorization_model import AuthorizationModel


class AuthorizationModelTestCase(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:

        self.authorization_model = AuthorizationModel()

        return super().setUp()

    def test_get_authorization(self):
        component = "Test"
        authorized_users = "+user1@node1,+user2@node2"
        non_authorized_cscs = "+MTHexapod:1,+MTHexapod:2,+MTRotator"

        component_authorization = self.authorization_model.get_authorization(
            component=component,
            authorized_users=authorized_users,
            non_authorized_cscs=non_authorized_cscs,
        )

        self.assertEqual(
            {"user1@node1", "user2@node2"}, component_authorization["authorized_users"]
        )
        self.assertEqual(
            {"MTHexapod:1", "MTHexapod:2", "MTRotator"},
            component_authorization["non_authorized_cscs"],
        )

    def test_get_authorization_empty_auth_empty_request(self):
        component = "Test"
        authorized_users = ""
        non_authorized_cscs = ""

        component_authorization = self.authorization_model.get_authorization(
            component=component,
            authorized_users=authorized_users,
            non_authorized_cscs=non_authorized_cscs,
        )

        self.assertEqual(set(), component_authorization["authorized_users"])
        self.assertEqual(
            set(),
            component_authorization["non_authorized_cscs"],
        )

    def test_get_authorization_non_empty_auth_empty_request(self):

        authorize_users = {"user1@node1", "user2@node2"}
        non_authorized_cscs = {"MTHexapod:1", "MTHexapod:2", "MTRotator"}

        self.authorization_model.set_authorization(
            "Test",
            authorized_users=authorize_users,
            non_authorized_cscs=non_authorized_cscs,
        )

        component_authorization = self.authorization_model.get_authorization(
            component="Test",
            authorized_users="",
            non_authorized_cscs="",
        )

        self.assertEqual(authorize_users, component_authorization["authorized_users"])
        self.assertEqual(
            non_authorized_cscs,
            component_authorization["non_authorized_cscs"],
        )

    def test_get_authorization_remove_user_and_csc(self):
        authorize_users = {"user1@node1", "user2@node2"}
        non_authorized_cscs = {"MTHexapod:1", "MTHexapod:2", "MTRotator"}

        self.authorization_model.set_authorization(
            "Test",
            authorized_users=authorize_users,
            non_authorized_cscs=non_authorized_cscs,
        )

        component = "Test"
        authorized_users = "-user2@node2"
        non_authorized_cscs = "-MTHexapod:1,-MTHexapod:2"

        component_authorization = self.authorization_model.get_authorization(
            component=component,
            authorized_users=authorized_users,
            non_authorized_cscs=non_authorized_cscs,
        )

        self.assertEqual({"user1@node1"}, component_authorization["authorized_users"])
        self.assertEqual(
            {"MTRotator"},
            component_authorization["non_authorized_cscs"],
        )

    def test_get_authorization_remove_user_and_csc_not_added(self):
        component = "Test"
        authorized_users = "+user1@node1,-user2@node2"
        non_authorized_cscs = "+MTHexapod:1,+MTHexapod:2,-MTRotator"

        component_authorization = self.authorization_model.get_authorization(
            component=component,
            authorized_users=authorized_users,
            non_authorized_cscs=non_authorized_cscs,
        )

        self.assertEqual({"user1@node1"}, component_authorization["authorized_users"])
        self.assertEqual(
            {"MTHexapod:1", "MTHexapod:2"},
            component_authorization["non_authorized_cscs"],
        )

    def test_get_authorization_fail_add_remove_same_user(self):
        component = "Test"
        authorized_users = "+user1@node1,+user2@node2,-user2@node2"
        non_authorized_cscs = "+MTHexapod:1,+MTHexapod:2,+MTRotator"

        with self.assertRaises(RuntimeError):
            self.authorization_model.get_authorization(
                component=component,
                authorized_users=authorized_users,
                non_authorized_cscs=non_authorized_cscs,
            )

    def test_get_authorization_bad_authorized_users(self):
        component = "Test"
        authorized_users = "+user1@node1,user2@node2"
        non_authorized_cscs = "+MTHexapod:1,+MTHexapod:2,+MTRotator"

        with self.assertRaises(RuntimeError):
            self.authorization_model.get_authorization(
                component=component,
                authorized_users=authorized_users,
                non_authorized_cscs=non_authorized_cscs,
            )

    def test_get_authorization_bad_non_authorized_cscs(self):
        component = "Test"
        authorized_users = "+user1@node1,+user2@node2"
        non_authorized_cscs = "+MTHexapod:1,+MTHexapod:2,MTRotator"

        with self.assertRaises(RuntimeError):
            self.authorization_model.get_authorization(
                component=component,
                authorized_users=authorized_users,
                non_authorized_cscs=non_authorized_cscs,
            )

    def test_set_authorization(self):
        authorize_users = {"user1@node1", "user2@node2"}
        non_authorized_cscs = {"ScriptQueue", "Script"}

        self.authorization_model.set_authorization(
            "Test",
            authorized_users=authorize_users,
            non_authorized_cscs=non_authorized_cscs,
        )

        self.assertTrue("Test" in self.authorization_model.authorization)
        self.assertEqual(
            authorize_users,
            self.authorization_model.authorization["Test"]["authorized_users"],
        )
        self.assertEqual(
            non_authorized_cscs,
            self.authorization_model.authorization["Test"]["non_authorized_cscs"],
        )

    async def test_process_request(self):

        cscs_to_change = "Test:1,Test:2"
        user_name = "user1@node1"
        authorized_users = "+user1@node1,+user2@node2"
        non_authorized_cscs = "+MTHexapod:1,+MTHexapod:2,+MTRotator"

        request = types.SimpleNamespace(
            cscsToChange=cscs_to_change,
            authorizedUsers=authorized_users,
            nonAuthorizedCSCs=non_authorized_cscs,
            private_identity=user_name,
        )
        set_auth_list_requests = dict()

        async for set_auth_list in self.authorization_model.process_request(request):
            component = set_auth_list["component"]
            if component not in set_auth_list_requests:
                set_auth_list_requests[component] = []
            set_auth_list_requests[component].append(set_auth_list["auth_list"])
            self.assertEqual(
                set(authorized_users.replace("+", "").split(",")),
                set(set_auth_list["auth_list"]["authorizedUsers"].split(",")),
            )
            self.assertEqual(
                set(non_authorized_cscs.replace("+", "").split(",")),
                set(set_auth_list["auth_list"]["nonAuthorizedCSCs"].split(",")),
            )
        self.assertEqual(len(set_auth_list_requests), len(cscs_to_change.split(",")))


if __name__ == "__main__":
    unittest.main()
