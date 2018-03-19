##############################################################################
# Copyright (c) 2013-2017, Lawrence Livermore National Security, LLC.
# Produced at the Lawrence Livermore National Laboratory.
#
# This file is part of Spack.
# Created by Todd Gamblin, tgamblin@llnl.gov, All rights reserved.
# LLNL-CODE-647188
#
# For details, see https://github.com/spack/spack
# Please also see the NOTICE and LICENSE files for our notice and the LGPL.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License (as
# published by the Free Software Foundation) version 2.1, February 1999.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the IMPLIED WARRANTY OF
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the terms and
# conditions of the GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
##############################################################################
from spack import *

import numbers
import os


def is_integral(x):
    """Any integer value"""
    try:
        return isinstance(int(x), numbers.Integral) and \
            not isinstance(x, bool) and int(x) > 0
    except ValueError:
        return False


class Nek5000(Package):
    """A fast and scalable high-order solver for computational fluid
       dynamics"""

    homepage = "https://nek5000.mcs.anl.gov/"
    url      = "https://github.com/Nek5000/Nek5000"

    tags = ['cfd', 'flow', 'hpc', 'solver', 'navier-stokes',
            'spectral-elements', 'fluid']

    version('17.0', '6a13bfad2ce023897010dd88f54a0a87',
            url="https://github.com/Nek5000/Nek5000/releases/download/"
                    "v17.0/Nek5000-v17.0.tar.gz")
    version('develop', git='https://github.com/Nek5000/Nek5000.git',
        branch='master')

    # MPI, Profiling and Visit variants
    variant('mpi',       default=True, description='Build with MPI.')
    variant('profiling', default=True, description='Build with profiling data.')
    variant('visit',     default=False, description='Build with Visit.')

    # Variant for MAXNEL, we need to read this from user
    variant(
        'MAXNEL',
        default=150000,
        description='Maximum number of elements for Nek5000 tools.',
        values=is_integral
    )

    # Variants for Nek tools
    variant('genbox',   default=True, description='Build genbox tool.')
    variant('int_tp',   default=True, description='Build int_tp tool.')
    variant('n2to3',    default=True, description='Build n2to3 tool.')
    variant('postnek',  default=True, description='Build postnek tool.')
    variant('reatore2', default=True, description='Build reatore2 tool.')
    variant('genmap',   default=True, description='Build genmap tool.')
    variant('nekmerge', default=True, description='Build nekmerge tool.')
    variant('prenek',   default=True, description='Build prenek tool.')

    # Dependencies
    depends_on('mpi', when="+mpi")
    depends_on('visit', when="+visit")

    @run_before('install')
    def fortran_check(self):
        if not self.compiler.f77:
            msg = 'Cannot build Nek5000 without a Fortran 77 compiler.'
            raise RuntimeError(msg)

    @run_after('install')
    def test_install(self):
        currentDir = os.getcwd()
        eddyDir = 'short_tests/eddy'
        os.chdir(eddyDir)

        os.system(join_path(self.prefix.bin, 'makenek') + ' eddy_uv')
        if not os.path.isfile(join_path(os.getcwd(), 'nek5000')):
            msg = 'Cannot build example: short_tests/eddy.'
            raise RuntimeError(msg)

        os.chdir(currentDir)

    def install(self, spec, prefix):
        toolsDir   = 'tools'
        binDir     = 'bin'

        # Do not use the Spack compiler wrappers.
        # Use directly the compilers:
        FC  = self.compiler.f77
        CC  = self.compiler.cc

        fflags = ' '.join(spec.compiler_flags['fflags'])
        cflags = ' '.join(spec.compiler_flags['cflags'])

        # Build the tools, maketools copy them to Nek5000/bin by default.
        # We will then install Nek5000/bin under prefix after that.
        with working_dir(toolsDir):
            # Update the maketools script to use correct compilers
            filter_file(r'^#FC\s*=.*', 'FC="{0}"'.format(FC), 'maketools')
            filter_file(r'^#CC\s*=.*', 'CC="{0}"'.format(CC), 'maketools')
            if fflags:
                filter_file(r'^#FFLAGS=.*', 'FFLAGS="{0}"'.format(fflags),
                            'maketools')
            if cflags:
                filter_file(r'^#CFLAGS=.*', 'CFLAGS="{0}"'.format(cflags),
                            'maketools')

            maxnel = self.spec.variants['MAXNEL'].value
            filter_file(r'^#MAXNEL\s*=.*', 'MAXNEL=' + maxnel, 'maketools')

            makeTools = Executable('./maketools')

            # Build the tools
            if '+genbox' in spec:
                makeTools('genbox')
            if '+int_tp' in spec and self.version == Version('17.0.0-beta2'):
                makeTools('int_tp')
            if '+n2to3' in spec:
                makeTools('n2to3')
            if '+postnek' in spec:
                makeTools('postnek')
            if '+reatore2' in spec:
                makeTools('reatore2')
            if '+genmap' in spec:
                makeTools('genmap')
            if '+nekmerge' in spec:
                makeTools('nekmerge')
            if '+prenek' in spec:
                makeTools('prenek')

        with working_dir(binDir):
            if '+mpi' in spec:
                FC  = spec['mpi'].mpif77
                CC  = spec['mpi'].mpicc
            else:
                filter_file(r'^#MPI=0', 'MPI=0', 'makenek')

            if '+profiling' not in spec:
                filter_file(r'^#PROFILING=0', 'PROFILING=0', 'makenek')

            if '+visit' in spec:
                filter_file(r'^#VISIT=1', 'VISIT=1', 'makenek')
                filter_file(r'^#VISIT_INSTALL=.*', 'VISIT_INSTALL=\"' +
                            spec['visit'].prefix.bin + '\"', 'makenek')

            # Update the makenek to use correct compilers and
            # Nek5000 source.
            if self.version >= Version('17.0'):
                filter_file(r'^#FC\s*=.*', 'FC="{0}"'.format(FC), 'makenek')
                filter_file(r'^#CC\s*=.*', 'CC="{0}"'.format(CC), 'makenek')
                filter_file(r'^#SOURCE_ROOT\s*=\"\$H.*',  'SOURCE_ROOT=\"' +
                            prefix.bin.Nek5000 + '\"',  'makenek')
                if fflags:
                    filter_file(r'^#FFLAGS=.*', 'FFLAGS="{0}"'.format(fflags),
                                'maketools')
                if cflags:
                    filter_file(r'^#CFLAGS=.*', 'CFLAGS="{0}"'.format(cflags),
                                'maketools')

        # Install Nek5000/bin in prefix/bin
        install_tree(binDir, prefix.bin)

        # Copy Nek5000 source to prefix/bin
        install_tree('../Nek5000', prefix.bin.Nek5000)
