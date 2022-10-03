#!python
# -*- coding: utf-8 -*-
#
#  This software and supporting documentation are distributed by
#      Institut Federatif de Recherche 49
#      CEA/NeuroSpin, Batiment 145,
#      91191 Gif-sur-Yvette cedex
#      France
#
# This software is governed by the CeCILL license version 2 under
# French law and abiding by the rules of distribution of free software.
# You can  use, modify and/or redistribute the software under the
# terms of the CeCILL license version 2 as circulated by CEA, CNRS
# and INRIA at the following URL "http://www.cecill.info".
#
# As a counterpart to the access to the source code and  rights to copy,
# modify and redistribute granted by the license, users are provided only
# with a limited warranty  and the software's author,  the holder of the
# economic rights,  and the successive licensors  have only  limited
# liability.
#
# In this respect, the user's attention is drawn to the risks associated
# with loading,  using,  modifying and/or developing or reproducing the
# software by the user in light of its specific status of free software,
# that may mean  that it is complicated to manipulate,  and  that  also
# therefore means  that it is reserved for developers  and  experienced
# professionals having in-depth computer knowledge. Users are therefore
# encouraged to load and test the software's suitability as regards their
# requirements in conditions enabling the security of their systems and/or
# data to be ensured and,  more generally, to use and operate it in the
# same conditions as regards security.
#
# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL license version 2 and that you accept its terms.

"""
    Utilities to perform quality checks
"""

import glob
import re

from deep_folding.config.logs import set_file_logger
# Defines logger
log = set_file_logger(__file__)


def compare_number_aims_files_with_expected(output_dir: str,
                                            list_subjects: list):
    """Compares number of generated files and expected number"""

    all_files = glob.glob(f"{output_dir}/*")

    generated_files = [f for f in all_files 
                         if not re.search('.minf$', f)]
    log.debug(f"Output directory = {output_dir}")
    log.debug(f"Generated_files = {generated_files}")

    nb_generated_files = len(generated_files)
    nb_expected_files = len(list_subjects)

    log.info(f"\n\tNumber of generated files = {nb_generated_files}")
    log.info(f"\n\tNumber of expected files = {nb_expected_files}")

    if nb_generated_files != nb_expected_files:
        log.warning("Number of generated files != number of expected files")
        if nb_generated_files < nb_expected_files:
            compare_subjects_with_expectd(generated_files, list_subjects)


def compare_subjects_with_expected(generated_files: list,
                                   list_subjects: list):
    """ Compare the sujbects from generated files and from list of subjects"""

    # Find a subject and its generated file to make the connection
    is_generated = False
    i = -1
    while not is_generated:
        i += 1
        sbj = list_subjects[i]
        for file in generated_files:
            match = re.search(sbj, file)
            if match:
                index = match.span(0)
                is_generated = True
                break

    # List all subjects with a generated file
    generated_subjects = [file[index[0]:index[1]] for file in generated_files]

    not_generated_subjects = set(list_subjects) - set(generated_subjects)

    log.warning(f"Subjects without generated file : {not_generated_subjects}")


def compare_output_folders(output_dir1, output_dir2):
    """ Compare the content of two output folders"""
    dcmp = dircmp(output_dir1, output_dir2)

    def compare_files(dcmp):
        for name in dcmp.left_only:
            fileordir = "file" if os.path.isfile(join(dcmp.left, name)) else "subdirectory"
            log.warning(f"The {fileordir} {name} is only in the directory {dcmp.left}")
        for name in dcmp.right_only:
            fileordir = "file" if os.path.isfile(join(dcmp.right, name)) else "subdirectory"
            log.warning(f"The {fileordir} {name} is only in the directory {dcmp.right}")
        for name in dcmp.diff_files:
            log.warning(f"The file {name} is not the same in {dcmp.left} and {dcmp.right}")
        for sub_dcmp in dcmp.subdirs.values():
            compare_files(sub_dcmp)

    compare_files(dcmp=dcmp)
