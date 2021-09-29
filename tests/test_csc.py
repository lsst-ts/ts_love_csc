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

import asyncio
import unittest
import functools
import contextlib

from lsst.ts import salobj
from lsst.ts.love.csc import CSC

CMD_TIMEOUT = 10


class CscTestCase(salobj.BaseCscTestCase, unittest.IsolatedAsyncioTestCase):
    def basic_make_csc(self, initial_state, config_dir, simulation_mode):
        return CSC(
            initial_state=initial_state,
            config_dir=config_dir,
            simulation_mode=simulation_mode,
            components_to_handle={"Test", "Script"},
        )

    async def test_standard_state_transitions(self):
        """Test standard CSC state transitions.

        The initial state is STANDBY.
        The standard commands and associated state transitions are:

        * start: STANDBY to DISABLED
        * enable: DISABLED to ENABLED

        * disable: ENABLED to DISABLED
        * standby: DISABLED to STANDBY
        * exitControl: STANDBY, FAULT to OFFLINE (quit)
        """

        async with self.make_csc(
            config_dir=None,
            initial_state=salobj.State.STANDBY,
            simulation_mode=0,
        ):

            await self.check_standard_state_transitions(
                enabled_commands=("requestAuthorization",)
            )

    async def test_request_authorization(self):
        async with self.make_csc(
            config_dir=None,
            initial_state=salobj.State.STANDBY,
            simulation_mode=0,
        ), self.make_test_controllers():

            self.controller_script.cmd_setAuthList.callback = functools.partial(
                self.do_set_auth_list_for_component, component="script"
            )
            self.controller_test.cmd_setAuthList.callback = functools.partial(
                self.do_set_auth_list_for_component, component="test"
            )

            await salobj.set_summary_state(self.remote, salobj.State.ENABLED)

            cscs_to_change = "Script:1,Test:1"
            authorized_users = "+user1@node1,+user2@node2"
            non_authorized_cscs = "+MTHexapod:1,+MTHexapod:2,+MTRotator"

            await self.remote.cmd_requestAuthorization.set_start(
                cscsToChange=cscs_to_change,
                authorizedUsers=authorized_users,
                nonAuthorizedCSCs=non_authorized_cscs,
                timeout=CMD_TIMEOUT,
            )

            self.assert_authorization(
                authorized_users.replace("+", ""), non_authorized_cscs.replace("+", "")
            )

    async def test_auth_list_monitoring(self):

        async with self.make_csc(
            config_dir=None,
            initial_state=salobj.State.STANDBY,
            simulation_mode=0,
        ), self.make_test_controllers():

            authorized_user = "user1@node1,user2@node2"
            non_authorized_cscs = "MTHexapod:1,MTHexapod:2,MTRotator"

            self.controller_test.evt_authList.set_put(
                authorizedUsers=authorized_user,
                nonAuthorizedCSCs=non_authorized_cscs,
            )

            self.controller_script.evt_authList.set_put(
                authorizedUsers=authorized_user,
                nonAuthorizedCSCs=non_authorized_cscs,
            )

            self.assertEqual(len(self.csc.authorization_model.authorization), 0)
            self.assertEqual(len(self.csc.authorization_model.authorization), 0)

            await salobj.set_summary_state(self.remote, salobj.State.ENABLED)

            self.assert_authorization(authorized_user, non_authorized_cscs)

            authorized_user = "user1@node1"
            non_authorized_cscs = "MTHexapod:1,MTRotator"

            self.controller_test.evt_authList.set_put(
                authorizedUsers=authorized_user,
                nonAuthorizedCSCs=non_authorized_cscs,
            )

            self.controller_script.evt_authList.set_put(
                authorizedUsers=authorized_user,
                nonAuthorizedCSCs=non_authorized_cscs,
            )

            await asyncio.sleep(self.csc.heartbeat_interval)

            self.assert_authorization(authorized_user, non_authorized_cscs)

            await salobj.set_summary_state(self.remote, salobj.State.DISABLED)

            self.controller_test.evt_authList.set_put(
                authorizedUsers="",
                nonAuthorizedCSCs="",
            )

            self.controller_script.evt_authList.set_put(
                authorizedUsers="",
                nonAuthorizedCSCs="",
            )

            await asyncio.sleep(self.csc.heartbeat_interval)

            self.assert_authorization(authorized_user, non_authorized_cscs)

    def assert_authorization(self, authorized_user, non_authorized_cscs):

        self.assertIn("Test:1", self.csc.authorization_model.authorization)
        self.assertEqual(
            set(authorized_user.split(",")),
            self.csc.authorization_model.authorization["Test:1"]["authorized_users"],
        )
        self.assertEqual(
            set(non_authorized_cscs.split(",")),
            self.csc.authorization_model.authorization["Test:1"]["non_authorized_cscs"],
        )

        self.assertIn("Script:1", self.csc.authorization_model.authorization)
        self.assertEqual(
            set(authorized_user.split(",")),
            self.csc.authorization_model.authorization["Script:1"]["authorized_users"],
        )
        self.assertEqual(
            set(non_authorized_cscs.split(",")),
            self.csc.authorization_model.authorization["Script:1"][
                "non_authorized_cscs"
            ],
        )

    @contextlib.asynccontextmanager
    async def make_test_controllers(self):

        async with salobj.Controller(
            "Test", index=1
        ) as self.controller_test, salobj.Controller(
            "Script", index=1
        ) as self.controller_script:
            yield

    def do_set_auth_list_for_component(self, data, component):

        getattr(self, f"controller_{component}").evt_authList.set_put(
            authorizedUsers=data.authorizedUsers,
            nonAuthorizedCSCs=data.nonAuthorizedCSCs,
        )


if __name__ == "__main__":
    unittest.main()
