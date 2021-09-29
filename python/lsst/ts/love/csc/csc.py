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

__all__ = ["CSC"]

import asyncio
import functools

from lsst.ts import salobj

from . import __version__
from .config_schema import CONFIG_SCHEMA
from .authorization_model import AuthorizationModel
from .utils import get_available_components


class CSC(salobj.ConfigurableCsc):
    """Commandable SAL Component for LOVE.

    This CSC is in charge of managing the auth list.
    """

    valid_simulation_modes: tuple = (0,)
    version: str = __version__

    def __init__(
        self,
        config_dir=None,
        initial_state=salobj.State.STANDBY,
        simulation_mode=0,
        components_to_handle=None,
    ) -> None:
        super().__init__(
            name="LOVE",
            index=0,
            config_schema=CONFIG_SCHEMA,
            config_dir=config_dir,
            initial_state=initial_state,
            simulation_mode=simulation_mode,
        )

        self.config = None

        self.timeout_short = 5.0

        self.authorization_model = AuthorizationModel()

        self._remotes = dict()

        self._create_remotes_for_components(
            components_to_handle
            if components_to_handle is not None
            else (get_available_components() - {"LOVE"})
        )

    async def end_enable(self, data):
        await self._set_auth_list_callbacks()

    async def end_disable(self, data):
        await self._unset_auth_list_callbacks()

    async def do_requestAuthorization(self, data) -> None:
        """"""
        self.assert_enabled()

        self.cmd_requestAuthorization.ack_in_progress(
            data, timeout=self.timeout_request_authorization + self.timeout_short
        )

        await asyncio.wait_for(
            self.process_request(data), timeout=self.timeout_request_authorization
        )

    async def configure(self, config) -> None:
        """Configure CSC.

        Parameters
        ----------
        config : `types.SimpleNamespace`
        """
        self.config = config
        self.authorization_model.set_authorization_mode(
            auto=self.config.auto_authorization
        )

    @staticmethod
    def get_config_pkg():
        return "ts_config_ocs"

    async def process_request(self, data):
        """Process requests to edit the auth list.

        Parameters
        ----------
        data : `cmd_requestAuthorization.DataType()`
            Payload received by requestAuthorization command.
        """

        async for set_auth_list in self.authorization_model.process_request(data):

            self.log.debug(
                f'set {set_auth_list["component"]} to: {set_auth_list["auth_list"]}'
            )

            component, index = salobj.name_to_name_index(set_auth_list["component"])

            if index > 0:
                set_auth_list["auth_list"][f"{component}ID"] = index

            await self._remotes[component].cmd_setAuthList.set_start(
                **set_auth_list["auth_list"], timeout=self.timeout_short
            )

    def _create_remotes_for_components(self, components):
        """Create remotes for components.

        Parameters
        ----------
        components : `set`
            Names of the components to create remote for.

        Raises
        ------
        RuntimeError
            If one or more of the input components are not available.
        """

        available_components = get_available_components() - {"LOVE"}

        if components != components.intersection(available_components):
            raise RuntimeError(
                "The following components are not available: "
                f"{components.difference(available_components)} "
                "They are either mispelled or their idl files were not built."
            )

        self.log.info(f"Creating remotes for {len(components)} components.")

        for component in components:
            if component not in self._remotes:
                self.log.debug(f"Setting up remote for {component}")
                self._remotes[component] = salobj.Remote(
                    domain=self.domain, name=component, include=["authList"]
                )
            else:
                self.log.debug(f"Remote for {component} already created.")

    async def _set_auth_list_callbacks(self):

        for component in self._remotes:
            self.log.debug(f"Set callback for {component}")
            try:
                component_auth_list = await self._remotes[component].evt_authList.aget(
                    timeout=self.timeout_short
                )
                self._handle_auth_list_for_component(
                    data=component_auth_list, component=component
                )
            except asyncio.TimeoutError:
                self.log.debug(f"No authList information for {component}.")
            finally:
                self._remotes[component].evt_authList.callback = functools.partial(
                    self._handle_auth_list_for_component, component=component
                )

    async def _unset_auth_list_callbacks(self):
        for component in self._remotes:
            self._remotes[component].evt_authList.callback = None

    def _handle_auth_list_for_component(self, data, component):

        if hasattr(data, f"{component}ID"):
            index = getattr(data, f"{component}ID")
            component_name = f"{component}:{index}"
        else:
            component_name = component

        self.log.debug(
            f"set authorization: {component_name}::{data.authorizedUsers}::{data.nonAuthorizedCSCs}"
        )

        self.authorization_model.set_authorization(
            component_name,
            set(data.authorizedUsers.split(",")) - {""},
            set(data.nonAuthorizedCSCs.split(",")) - {""},
        )

    @property
    def timeout_request_authorization(self):
        return (
            self.config.timeout_request_authorization
            if self.config is not None
            else 60.0
        )
