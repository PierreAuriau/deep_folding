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

"""Write skeletons from graph files

  Typical usage
  -------------
  You can use this program by first entering in the brainvisa environment
  (here brainvisa 5.0.0 installed with singularity) and launching the script
  from the terminal:
  >>> bv bash
  >>> python generate_skeletons.py


"""

import argparse
import glob
import re
import sys
from os.path import abspath
from os.path import basename
from os.path import dirname
from os.path import join

from deep_folding.brainvisa import exception_handler, DeepFoldingError
from deep_folding.brainvisa.utils.folder import create_folder
from deep_folding.brainvisa.utils.subjects import \
    get_number_subjects, is_it_a_subject
from deep_folding.brainvisa.utils.subjects import \
    select_subjects_int, select_good_qc
from deep_folding.brainvisa.utils.logs import setup_log
from deep_folding.brainvisa.utils.parallel import define_njobs
from deep_folding.brainvisa.utils.skeleton import \
    generate_skeleton_from_graph_file, generate_full_skeleton
from deep_folding.brainvisa.utils.quality_checks import \
    compare_number_aims_files_with_expected, \
    get_not_processed_subjects
from pqdm.processes import pqdm
from p_tqdm import p_map
from deep_folding.config.logs import set_file_logger

# Import constants
from deep_folding.brainvisa.utils.constants import \
    _ALL_SUBJECTS, _SRC_DIR_DEFAULT,\
    _SKELETON_DIR_DEFAULT, _SIDE_DEFAULT, \
    _JUNCTION_DEFAULT, _PATH_TO_GRAPH_DEFAULT, \
    _QC_PATH_DEFAULT

# Defines logger
log = set_file_logger(__file__)


def parse_args(argv):
    """Parses command-line arguments

    Args:
        argv: a list containing command line arguments

    Returns:
        args
    """

    # Parse command line arguments
    parser = argparse.ArgumentParser(
        prog=basename(__file__),
        description='Generates skeleton files from graphs')
    parser.add_argument(
        "-s", "--src_dir", type=str, default=_SRC_DIR_DEFAULT,
        help='Source directory where the graph data lies. '
             'Default is : ' + _SRC_DIR_DEFAULT)
    parser.add_argument(
        "-o", "--output_dir", type=str, default=_SKELETON_DIR_DEFAULT,
        help='Output directory where to put skeleton files.'
        'Default is : ' + _SKELETON_DIR_DEFAULT)
    parser.add_argument(
        "-i", "--side", type=str, default=_SIDE_DEFAULT,
        help='Hemisphere side. Default is : ' + _SIDE_DEFAULT)
    parser.add_argument(
        "-p", "--path_to_graph", type=str,
        default=_PATH_TO_GRAPH_DEFAULT,
        help='Relative path to graph. '
             'Default is ' + _PATH_TO_GRAPH_DEFAULT)
    parser.add_argument(
        "-q", "--quality_checks", type=str,
        default=_QC_PATH_DEFAULT,
        help='Path to quality check .csv. '
             'Default is ' + _QC_PATH_DEFAULT)
    parser.add_argument(
        "-j", "--junction", type=str, default=_JUNCTION_DEFAULT,
        help='junction rendering (either \'wide\' or \'thin\') '
             f"Default is {_JUNCTION_DEFAULT}")
    parser.add_argument(
        "-b", "--bids", default=False, action="store_true",
        help='If the database is organized according to BIDS rules.'
             'In particular, for databases having several images for each subject. ')
    parser.add_argument(
        "-a", "--parallel", default=False, action='store_true',
        help='if set (-a), launches computation in parallel')
    parser.add_argument(
        "-n", "--nb_subjects", type=str, default="all",
        help='Number of subjects to take into account, or \'all\'. '
             '0 subject is allowed, for debug purpose.'
             'Default is : all')
    parser.add_argument(
        '-v', '--verbose', action='count', default=0,
        help='Verbose mode: '
        'If no option is provided then logging.INFO is selected. '
        'If one option -v (or -vv) or more is provided '
        'then logging.DEBUG is selected.')

    args = parser.parse_args(argv)

    suffix = {"R": "right", "L": "left", "F": "full"}
    setup_log(args,
              log_dir=f"{args.output_dir}",
              prog_name=basename(__file__),
              suffix=suffix[args.side])

    params = vars(args)

    params['src_dir'] = abspath(args.src_dir)
    params['skeleton_dir'] = abspath(args.output_dir)
    # Checks if nb_subjects is either the string "all" or a positive integer
    params['nb_subjects'] = get_number_subjects(args.nb_subjects)

    return params


class GraphConvert2Skeleton:
    """Class to convert all graphs from a folder into skeletons

    It contains all information to scan a dataset for graphs
    and writes skeletons into target directory
    """

    def __init__(self, src_dir, skeleton_dir,
                 side, junction, parallel,
                 path_to_graph, bids, qc_path):
        self.src_dir = src_dir
        self.skeleton_dir = skeleton_dir
        self.side = side
        self.qc_path = qc_path
        self.junction = junction
        self.parallel = parallel
        self.path_to_graph = path_to_graph
        self.bids = bids
        self.skeleton_dir = f"{self.skeleton_dir}/{self.side}"
        create_folder(abspath(self.skeleton_dir))
        self.bids = bids

    def get_skeleton_filename(self, subject, graph_file):
        skeleton_file = f"{self.skeleton_dir}/" + \
                        f"{self.side}skeleton_generated_{subject}"
        if self.bids:
            session = re.search("ses-([^_/]+)", graph_file)
            acquisition = re.search("acq-([^_/]+)", graph_file)
            run = re.search("run-([^_/]+)", graph_file)
            if session:
                skeleton_file += f"_{session[0]}"
            if acquisition:
                skeleton_file += f"_{acquisition[0]}"
            if run:
                skeleton_file += f"_{run[0]}"
        skeleton_file += ".nii.gz"
        return skeleton_file

    def generate_one_skeleton(self, subject: str):
        """Generates and writes skeleton for one subject.
        """
        if self.side == "F":
            graph_path = f"{self.src_dir}/{subject}*/" + \
                         f"{self.path_to_graph}/?{subject}*.arg"
        else:
            graph_path = f"{self.src_dir}/{subject}*/" + \
                         f"{self.path_to_graph}/{self.side}{subject}*.arg"
        list_graph_file = glob.glob(graph_path)
        log.debug(f"list_graph_file = {list_graph_file}")
        try:
            if len(list_graph_file) == 0:
                raise FileNotFoundError(f"No graph file! "
                                        f"{graph_path} doesn't exist")
        except FileNotFoundError as e:
            log.error(f"Subject {subject} : {e}")
        for graph_file in list_graph_file:
            try:
                skeleton_file = self.get_skeleton_filename(subject, graph_file)
                if self.side == "F":
                    graph_file_left, graph_file_right, graph_to_remove = \
                        self.get_left_and_right_graph_files(graph_file, list_graph_file)
                    if graph_to_remove:
                        list_graph_file.remove(graph_to_remove)
                        generate_full_skeleton(graph_file_left,
                                               graph_file_right,
                                               skeleton_file,
                                               self.junction)
                else:
                    generate_skeleton_from_graph_file(graph_file,
                                                      skeleton_file,
                                                      self.junction)
                if not self.bids:
                    break
            except DeepFoldingError as e:
                log.error(f"Graph file {graph_file} : {e}")
                continue

    @staticmethod
    def get_left_and_right_graph_files(graph_file, list_graph_file):
        graph_name = basename(graph_file)
        if graph_name[0] == "L":
            graph_file_left = graph_file
            graph_file_right = join(dirname(graph_file), f"R{graph_name[1:]}")
            if graph_file_right not in list_graph_file:
                raise DeepFoldingError(f"Right graph is missing ({graph_file_right})")
            else:
                graph_to_remove = graph_file_right
        else:
            graph_file_right = graph_file
            graph_file_left = join(dirname(graph_file), f"L{graph_name[1:]}")
            if graph_file_left not in list_graph_file:
                raise DeepFoldingError(f"Left graph is missing ({graph_file_left})")
            else:
                graph_to_remove = graph_file_left
        return graph_file_left, graph_file_right, graph_to_remove

    def compute(self, number_subjects):
        """Loops over subjects and converts graphs into skeletons.
        """
        # Gets list of subjects
        filenames = glob.glob(f"{self.src_dir}/*")
        list_subjects = [basename(filename) for filename in filenames
                         if is_it_a_subject(filename)]
        log.info(f"Number of subjects before qc = {len(list_subjects)}")
        list_subjects = select_good_qc(list_subjects, self.qc_path)
        list_subjects = \
            get_not_processed_subjects(list_subjects, self.skeleton_dir)

        list_subjects = select_subjects_int(list_subjects, number_subjects)

        log.info(f"Expected number of subjects = {len(list_subjects)}")
        log.info(f"list_subjects[:5]= {list_subjects[:5]}")
        log.debug(f"list_subjects= {list_subjects}")

        # Performs computation on all subjects either serially or in parallel
        if self.parallel:
            log.info(
                "PARALLEL MODE: subjects are computed in parallel.")
            p_map(self.generate_one_skeleton,
                  list_subjects,
                  num_cpus=define_njobs())
        else:
            log.info(
                "SERIAL MODE: subjects are scanned serially, "
                "without parallelism")
            for sub in list_subjects:
                self.generate_one_skeleton(sub)

        # Checks if there is expected number of generated files
        if self.bids:
            list_graphs = \
                [g for g in glob.glob(f"{self.src_dir}/*/{self.path_to_graph}")
                 if not re.search('.minf$', g)]
            compare_number_aims_files_with_expected(self.skeleton_dir, list_graphs)
        else:
            compare_number_aims_files_with_expected(self.skeleton_dir, list_subjects)


def generate_skeletons(
        src_dir=_SRC_DIR_DEFAULT,
        skeleton_dir=_SKELETON_DIR_DEFAULT,
        path_to_graph=_PATH_TO_GRAPH_DEFAULT,
        side=_SIDE_DEFAULT,
        junction=_JUNCTION_DEFAULT,
        bids=False,
        parallel=False,
        number_subjects=_ALL_SUBJECTS,
        qc_path=_QC_PATH_DEFAULT):
    """Generates skeletons from graphs"""

    # Initialization
    conversion = GraphConvert2Skeleton(
        src_dir=src_dir,
        skeleton_dir=skeleton_dir,
        path_to_graph=path_to_graph,
        side=side,
        bids=bids,
        junction=junction,
        parallel=parallel,
        qc_path=qc_path
    )
    # Actual generation of skeletons from graphs
    conversion.compute(number_subjects=number_subjects)


@exception_handler
def main(argv):
    """Reads argument line and generates skeleton from graph

    Args:
        argv: a list containing command line arguments
    """
    # Parsing arguments
    params = parse_args(argv)

    # Actual API
    generate_skeletons(
        src_dir=params['src_dir'],
        skeleton_dir=params['skeleton_dir'],
        path_to_graph=params['path_to_graph'],
        side=params['side'],
        junction=params['junction'],
        bids=params['bids'],
        parallel=params['parallel'],
        number_subjects=params['nb_subjects'],
        qc_path=params['quality_checks'])


if __name__ == '__main__':
    # This permits to call main also from another python program
    # without having to make system calls
    main(argv=sys.argv[1:])
