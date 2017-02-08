# Copyright (c) 2015 SUSE Linux GmbH.  All rights reserved.
#
# This file is part of kiwi.
#
# kiwi is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# kiwi is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with kiwi.  If not, see <http://www.gnu.org/licenses/>
#
"""
usage: kiwi image info -h | --help
       kiwi image info --description=<directory>
           [--resolve-package-list]
           [--ignore-repos]
           [--add-repo=<source,type,alias,priority>...]
           [--obs-repo-internal]
       kiwi image info help

commands:
    info
        provide information about the specified image description

options:
    --add-repo=<source,type,alias,priority>
        add repository with given source, type, alias and priority
    --description=<directory>
        the description must be a directory containing a kiwi XML
        description and optional metadata files
    --ignore-repos
        ignore all repos from the XML configuration
    --obs-repo-internal
        when using obs:// repos resolve them using the SUSE internal
        buildservice. This only works if access to SUSE's internal
        buildservice is granted
    --resolve-package-list
        solve package dependencies and return a list of all
        packages including their attributes e.g size,
        shasum, etc...
"""
# project
from .base import CliTask
from ..help import Help
from ..utils.output import DataOutput
from ..solver.sat import Sat
from ..solver.repository import SolverRepository
from ..system.uri import Uri


class ImageInfoTask(CliTask):
    """
    Implements retrieval of in depth information for an image description

    Attributes

    * :attr:`manual`
        Instance of Help
    """
    def process(self):
        """
        Walks through the given info options and provide the requested data
        """
        self.manual = Help()
        if self.command_args.get('help') is True:
            return self.manual.show('kiwi::image::info')

        self.load_xml_description(
            self.command_args['--description']
        )

        if self.command_args['--ignore-repos']:
            self.xml_state.delete_repository_sections()

        if self.command_args['--add-repo']:
            for add_repo in self.command_args['--add-repo']:
                (repo_source, repo_type, repo_alias, repo_prio) = \
                    self.quadruple_token(add_repo)
                self.xml_state.add_repository(
                    repo_source, repo_type, repo_alias, repo_prio
                )

        self.runtime_checker.check_repositories_configured()

        if self.command_args['--obs-repo-internal']:
            # This build should use the internal SUSE buildservice
            # Be aware that the buildhost has to provide access
            self.xml_state.translate_obs_to_ibs_repositories()

        result = {
            'image': self.xml_state.xml_data.get_name()
        }

        if self.command_args['--resolve-package-list']:
            solver = self._setup_solver()
            package_list = self.xml_state.get_bootstrap_packages() + \
                self.xml_state.get_system_packages()
            solved_packages = solver.solve(package_list)
            package_info = {}
            for package, metadata in sorted(list(solved_packages.items())):
                if package in package_list:
                    status = 'listed_in_kiwi_description'
                else:
                    status = 'added_by_dependency_solver'
                package_info[package] = {
                    'source': metadata.uri,
                    'installsize_bytes': int(metadata.installsize_bytes),
                    'arch': metadata.arch,
                    'version': metadata.version,
                    'status': status
                }
            result['resolved-packages'] = package_info

        if self.global_args['--color-output']:
            DataOutput(result, style='color').display()
        else:
            DataOutput(result).display()

    def _setup_solver(self):
        solver = Sat()
        for xml_repo in self.xml_state.get_repository_sections():
            repo_source = xml_repo.get_source().get_path()
            repo_type = xml_repo.get_type()
            solver.add_repository(
                SolverRepository(Uri(repo_source, repo_type))
            )
        return solver
