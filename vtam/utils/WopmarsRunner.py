import os
import pathlib
import tempfile

import jinja2

from vtam.utils.PathManager import PathManager
from vtam.utils.Singleton import Singleton
from vtam.utils.constants import parameters_numerical


class WopmarsRunner(Singleton):

    def __init__(self, command, parameters):
        """

        :param command: takes one of three values: merge, asv or optimize
        :param parameters: dictionnary (OptionManager.instance()) with command
        """
        self.command = command
        ##################################
        #
        # Load default numerical parameters and overwrite with custom parameters
        #
        ##################################
        self.parameters = parameters_numerical.copy()
        for k in parameters:
            self.parameters[k] = parameters[k]
        #
        self.wopfile_path = None
        self.tempdir = PathManager.instance().get_tempdir()


    def create_wopfile(self, path=None):
        """

        :param wopfile_path: Path of output wopfile
        :return: tuple (wopfile_path, wopfile_content)
        """
        #####################
        #
        # Get Wopfile template output
        # Create Wopfile output
        #
        #####################
        wopfile_path = path
        if wopfile_path is None:
            wopfile_path = tempfile.NamedTemporaryFile().name
        self.wopfile_path = wopfile_path
        #####################
        #
        # Create Wopfile content
        #
        #####################
        template_dir = os.path.join(os.path.dirname(__file__), '../../data')
        jinja2_env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir))
        template = None
        if self.command == 'merge':
            template = jinja2_env.get_template('wopfile_merge.yml')
            if not self.parameters['outdir'] is None:
                wopfile_path = os.path.join(self.parameters['outdir'], 'wopfile_merge.yml')
            else:
                wopfile_path = os.path.join(self.tempdir, 'wopfile_merge.yml')
        elif self.command in ['asv', 'optimize', 'taxassign']:
            # Add output to sortreads file
            if self.command == 'asv':
                self.parameters['sortreads'] = os.path.join(self.parameters['outdir'], "sortreads.tsv")
                self.parameters['update_taxassign'] = 0
                self.parameters['asvtable'] = os.path.join(self.parameters['outdir'], "asvtable.tsv")
                self.parameters['pooled_markers'] = os.path.join(self.parameters['outdir'], "pooled_markers.tsv")
                template = jinja2_env.get_template('wopfile_asv.yml')
                # Create wopfile
                wopfile_path = os.path.join(self.parameters['outdir'], 'wopfile_asv.yml')
            elif self.command == 'taxassign':
                self.parameters['update_taxassign'] = 1
                template = jinja2_env.get_template('wopfile_taxassign.yml')
                # Create wopfile
            elif self.command == 'optimize':
                self.parameters['sortreads'] = os.path.join(self.parameters['outdir'], "sortreads.tsv")
                #
                self.parameters['optimize_lfn_biosample_replicate'] \
                    = os.path.join(self.parameters['outdir'], "optimize_lfn_biosample_replicate.tsv")
                self.parameters['optimize_lfn_read_count_and_lfn_variant'] \
                    = os.path.join(self.parameters['outdir'], "optimize_lfn_read_count_and_lfn_variant.tsv")
                self.parameters['optimize_lfn_variant_specific'] \
                    = os.path.join(self.parameters['outdir'], "optimize_lfn_variant_specific.tsv")
                self.parameters['optimize_pcr_error'] \
                    = os.path.join(self.parameters['outdir'], "optimize_pcr_error.tsv")
                self.parameters['optimize_lfn_read_count_and_lfn_variant_replicate'] \
                    = os.path.join(self.parameters['outdir'], "optimize_lfn_read_count_and_lfn_variant_replicate.tsv")
                self.parameters['optimize_lfn_variant_replicate_specific'] \
                    = os.path.join(self.parameters['outdir'], "optimize_lfn_variant_replicate_specific.tsv")
                #
                template = jinja2_env.get_template('wopfile_optimize.yml')
                wopfile_path = os.path.join(self.parameters['outdir'], 'wopfile_optimize.yml')
        wopfile_content = template.render(self.parameters)
        ################
        #
        # Write to wopfile
        #
        ################
        pathlib.Path(os.path.dirname(wopfile_path)).mkdir(exist_ok=True)
        with open(wopfile_path, "w") as fout:
            fout.write(wopfile_content)
        return wopfile_path, wopfile_content


    def get_wopmars_command(self):
        """

        :param wopfile_out_path: Path of output wopfile
        :return: string with output output of wopfile
        """

        ###################
        #
        # Base wopmars command
        #
        ###################
        if self.wopfile_path is None:
            self.wopfile_path = os.path.join(self.tempdir, 'Wopfile_{}.yml'.format(self.command))
            self.wopfile_path, wopfile_content = self.create_wopfile(path=self.wopfile_path)
        wopmars_command_template = "wopmars -w {wopfile_path} -D sqlite:///{db} "
        wopmars_command = wopmars_command_template\
            .format(wopfile_path=self.wopfile_path, **self.parameters)
        if self.parameters['dryrun']:
            wopmars_command += " -n"
        if self.parameters['forceall']:
            wopmars_command += " -F"
        if self.parameters['log_verbosity'] > 0: # -v then pass this verbosity to wopmars
            wopmars_command += " -v"
            if self.parameters['log_verbosity'] > 1: # -vv or higher, then do no pass it through environmental variables
                os.environ['VTAM_LOG_VERBOSITY'] = str(self.parameters['log_verbosity'])
        if not self.parameters['log_file'] is None:
            wopmars_command += " --log " + self.parameters['log_file']
        if not self.parameters['sourcerule'] is None:
            wopmars_command += " --sourcerule {sourcerule}".format(**self.parameters)
        if not self.parameters['targetrule'] is None:
            wopmars_command += " --targetrule {targetrule}".format(**self.parameters)
        wopmars_command = wopmars_command.format(**self.parameters)
        return wopmars_command
