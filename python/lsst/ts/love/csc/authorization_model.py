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

import logging

from .utils import parse_auth_request


class AuthorizationModel:
    """Handle CSC authorization.

    Attributes
    ----------
    authorization : `dict`
        Dictionary with the current state of the system auth list.
    """

    def __init__(self, log=None) -> None:

        self.log = (
            logging.getLogger(type(self).__name__)
            if log is None
            else log.getChild(type(self).__name__)
        )
        self.authorization = dict()
        self._auto_accept_request = True

    def get_authorization(self, component, authorized_users, non_authorized_cscs):
        """Get the result of authorizing users/cscs to control a component.

        This method returns what would be the result of applying a certain
        authorization to a component in the list. It does not implement the
        authorization. To apply it, use set_authorization with the return
        value of this method.

        Parameters
        ----------
        component : `str`
            Name of the component to authorize.
        authorized_users : `str`
            Comma seperated list of users to authorize.
        non_authorized_cscs : `str`
            Comma seperated list of cscs to unauthorize.

        Returns
        -------
        component_authorization : `dict`
            Dictionary with the result of applying the authorization.
        """

        component_authorization = self.get_component_authorization(component)

        authorize_users_to_add, authorize_users_to_remove = parse_auth_request(
            authorized_users
        )

        non_authorized_cscs_to_add, non_authorized_cscs_to_remove = parse_auth_request(
            non_authorized_cscs
        )

        component_authorization["authorized_users"] = component_authorization[
            "authorized_users"
        ].union(authorize_users_to_add)
        component_authorization["authorized_users"] -= authorize_users_to_remove

        component_authorization["non_authorized_cscs"] = component_authorization[
            "non_authorized_cscs"
        ].union(non_authorized_cscs_to_add)
        component_authorization["non_authorized_cscs"] -= non_authorized_cscs_to_remove

        return component_authorization

    def set_authorization(self, component, authorized_users, non_authorized_cscs):
        """Set authorization for a component with the input values.

        Parameters
        ----------
        component : `str`
            Name of the component to set authorization.
        authorized_users : `list` of `str`
            List of strings with the name of the users to authorize.
        non_authorized_cscs : `list` of `str`
            List of strings with the name of CSCs to remove authorization.
        """
        self._handle_enter_component_in_auth_list(component=component)

        self.authorization[component]["authorized_users"] = set(authorized_users)
        self.authorization[component]["non_authorized_cscs"] = set(non_authorized_cscs)

        self._handle_exit_component_in_auth_list(component=component)

    def set_authorization_mode(self, auto):
        """Set authorization mode.

        Parameters
        ----------
        auto : `bool`
            Set automatic mode?
        """

        self._auto_accept_request = auto

    def get_component_authorization(self, component):
        return self.authorization.get(
            component, dict(authorized_users=set(), non_authorized_cscs=set())
        )

    async def process_request(self, data):
        """Process request to change authorization.

        Parameters
        ----------
        data : `object`
            DDS-like object with the request to change authorization.

        Yields
        ------
        set_auth_list : `dict`
            Dictionary with the name of the component and payload for the new
            auth list.
        """

        if not self._auto_accept_request:
            raise NotImplementedError("Non-automatic mode not implemented yet.")

        for component in data.cscsToChange.split(","):

            component_authorizaton = self.get_authorization(
                component=component,
                authorized_users=data.authorizedUsers,
                non_authorized_cscs=data.nonAuthorizedCSCs,
            )

            self.log.debug(f"Component authorization: {component_authorizaton}")

            set_auth_list = dict(
                component=component,
                auth_list=dict(
                    authorizedUsers=",".join(
                        component_authorizaton["authorized_users"]
                    ),
                    nonAuthorizedCSCs=",".join(
                        component_authorizaton["non_authorized_cscs"]
                    ),
                ),
            )

            yield set_auth_list

    def _handle_enter_component_in_auth_list(self, component):
        if component not in self.authorization:
            self.authorization[component] = dict(
                authorized_users=set(), non_authorized_cscs=set()
            )

    def _handle_exit_component_in_auth_list(self, component):
        if (
            component in self.authorization
            and len(self.authorization[component]["authorized_users"]) == 0
            and len(self.authorization[component]["non_authorized_cscs"]) == 0
        ):
            self.authorization.pop(component)
