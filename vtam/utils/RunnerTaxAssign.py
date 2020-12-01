import inspect
import os
import pandas
import pathlib

from vtam.utils.FileParams import FileParams

from vtam.utils.Logger import Logger
from vtam.utils.PathManager import PathManager
from vtam.utils.RunnerBlast import RunnerBlast
from vtam.utils.RunnerLTGselection import RunnerLTGselection
from vtam.utils.VTAMexception import VTAMexception


class RunnerTaxAssign(object):
    """Will assign variants to a taxon"""

    def __init__(self, sequence_list, taxonomy, blast_db_dir, blast_db_name,
             num_threads, params):
        """

        Parameters
        ----------
        sequence_list : list
            List of se
        param2 : str
            The second parameter.

        """

        # self.variant_df = variant_df
        # stores tax_id and old_tax_id
        # self.old_tax_id_df = taxonomy_df[['old_tax_id']].drop_duplicates()
        # self.taxonomy_df = taxonomy_df[[
        #     'parent_tax_id', 'rank', 'name_txt']].drop_duplicates()
        self.old_tax_id_df = taxonomy.old_tax_df
        self.taxonomy_df = taxonomy.df
        self.blast_db_dir = blast_db_dir
        self.this_temp_dir = os.path.join(PathManager.instance().get_tempdir(),
            os.path.basename(__file__))
        pathlib.Path(self.this_temp_dir).mkdir(exist_ok=True)

        self.num_threads = num_threads

        #######################################################################
        #
        # Parameters
        #
        #######################################################################

        params_dic = FileParams(params).get_params_dic()
        qcov_hsp_perc = params_dic['qcov_hsp_perc']

        self.ltg_rule_threshold = params_dic['ltg_rule_threshold']
        self.include_prop = params_dic['include_prop']
        self.min_number_of_taxa = params_dic['min_number_of_taxa']

        #######################################################################
        #
        # 2 Create FASTA file with Variants
        #
        #######################################################################

        Logger.instance().debug(
            "file: {}; line: {}; Create SortedReadFile from Variants".format(
                __file__, inspect.currentframe().f_lineno))
        variant_fasta = os.path.join(self.this_temp_dir, 'variant.fasta')
        with open(variant_fasta, 'w') as fout:
            for seq in sequence_list:
                fout.write(">{}\n{}\n".format(seq, seq))

        #######################################################################
        #
        # 3 Run local blast
        #
        #######################################################################

        runner_blast = RunnerBlast(variant_fasta, blast_db_dir, blast_db_name,
            num_threads, qcov_hsp_perc)
        # run blast
        blast_output_tsv = runner_blast.run_local_blast()
        # process blast results
        blast_output_df = RunnerBlast.process_blast_result(blast_output_tsv)

        #######################################################################
        #
        # Read target_tax_id
        # Compute lineages for each unique target_tax_id
        # Create a DF with these columns: tax_id and its lineage in wide format
        #
        #######################################################################

        Logger.instance().debug("file: {}; line: {}; Open taxonomy.tsv DB".format(
                __file__, inspect.currentframe().f_lineno))
        blast_output_df.target_tax_id = pandas.to_numeric(blast_output_df.target_tax_id)
        #
        Logger.instance().debug(
            "file: {}; line: {}; Annotate each target_tax_id with its lineage as columns in wide format".format(
                __file__, inspect.currentframe().f_lineno))
        lineage_list = []
        for target_tax_id_i, target_tax_id in enumerate(
                blast_output_df.target_tax_id.unique().tolist()):
            if target_tax_id_i % 100 == 0:
                Logger.instance().debug(
                    "Get lineage of {}-th tax id {} (Total {} tax ids)".format(
                        target_tax_id_i, target_tax_id, len(
                            blast_output_df.target_tax_id.unique().tolist())))
            # lineage_list.append(self.tax_id_to_taxonomy_lineage(tax_id=target_tax_id))
            lineage_list.append(taxonomy.create_lineage(tax_id=target_tax_id))
        tax_id_to_lineage_df = pandas.DataFrame(lineage_list)

        #######################################################################
        #
        # Merge tax lineages and the blast result
        #
        #######################################################################

        Logger.instance().debug(
            "file: {}; line: {}; Merge blast result including tax_id with their lineages".format(
                __file__, inspect.currentframe().f_lineno))
        # Merge local blast output with tax_id_to_lineage_df
        variantid_identity_lineage_df = blast_output_df.merge(
            tax_id_to_lineage_df, left_on='target_tax_id', right_on='tax_id')
        variantid_identity_lineage_df.drop('tax_id', axis=1, inplace=True)

        """(Pdb) variantid_identity_lineage_df.columns
Index(['variant_id', 'target_id', 'identity', 'evalue', 'coverage',
       'target_tax_id', 'no rank', 'species', 'genus', 'family', 'order',
       'class', 'subphylum', 'phylum', 'subkingdom', 'kingdom', 'superkingdom',
       'superfamily', 'infraorder', 'suborder', 'infraclass', 'subclass',
       'tribe', 'subfamily', 'cohort', 'subgenus', 'subspecies', 'parvorder',
       'superorder', 'subcohort', 'superclass', 'species group', 'subtribe',
       'section', 'varietas', 'species subgroup'],
      dtype='object')"""

        #######################################################################
        #
        #  blast_output_to_ltg_tax_id
        # this function returns a data frame containing the Ltg rank and Ltg Tax_id for each variant
        #
        #######################################################################

        Logger.instance().debug(
            "file: {}; line: {}; Main loop over variant and identity to"
            "compute the whole set of ltg_tax_id and ltg_rank for each variant_id"
            "to a dataframe".format(
                __file__, inspect.currentframe().f_lineno))
        runner_ltg_selection = RunnerLTGselection(variantid_identity_lineage_df=variantid_identity_lineage_df,
                                                  taxonomy_df=self.taxonomy_df, params=params)
        self.ltg_df = runner_ltg_selection.blast_output_to_ltg_tax_id()
