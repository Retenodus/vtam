from sqlalchemy import select

from vtam.utils.FastaInformation import FastaInformation
from vtam.utils.SampleInformationDfAnalyzer import SampleInformationDfAnalyzer
from vtam.utils.VariantReadCountLikeTable import VariantReadCountLikeTable
from vtam.utils.Logger import Logger
from vtam.utils.OptionManager import OptionManager
from vtam.utils.VTAMexception import VTAMexception
from wopmars.models.ToolWrapper import ToolWrapper

import pandas
import sys


class FilterIndel(ToolWrapper):
    __mapper_args__ = {
        "polymorphic_identity": "vtam.wrapper.FilterIndel"
    }

    # Input file
    __input_file_fastainfo = "fastainfo"
    # Input table
    __input_table_marker = "Marker"
    __input_table_run = "Run"
    __input_table_biosample = "Biosample"
    __input_table_filter_renkonen = "FilterRenkonen"
    __input_table_Variant = "Variant"
    # Output table
    __output_table_filter_indel = "FilterIndel"



    def specify_input_file(self):
        return[
            FilterIndel.__input_file_fastainfo,

        ]

    def specify_input_table(self):
        return [
            FilterIndel.__input_table_marker,
            FilterIndel.__input_table_run,
            FilterIndel.__input_table_biosample,
            FilterIndel.__input_table_filter_renkonen,
            FilterIndel.__input_table_Variant,
        ]


    def specify_output_table(self):
        return [
            FilterIndel.__output_table_filter_indel,
        ]

    def specify_params(self):
        return {
            "skip_filter_indel": "int",
        }



    def run(self):
        session = self.session
        engine = session._session().get_bind()

        ##########################################################
        #
        # Wrapper inputs, outputs and parameters
        #
        ##########################################################
        #
        # Input file output
        input_file_fastainfo = self.input_file(FilterIndel.__input_file_fastainfo)
        #
        # Input table models
        marker_model = self.input_table(FilterIndel.__input_table_marker)
        run_model = self.input_table(FilterIndel.__input_table_run)
        biosample_model = self.input_table(FilterIndel.__input_table_biosample)
        variant_model = self.input_table(FilterIndel.__input_table_Variant)
        input_filter_renkonen_model = self.input_table(FilterIndel.__input_table_filter_renkonen)
        #
        # Options
        skip_filter_indel = bool(self.option("skip_filter_indel"))
        #
        # Output table models
        output_filter_indel_model = self.output_table(FilterIndel.__output_table_filter_indel)

        ##########################################################
        #
        # 1. Read fastainfo to get run_id, marker_id, biosample_id, replicate for current analysis
        #
        ##########################################################

        fasta_info_obj = FastaInformation(input_file_fastainfo, engine, run_model, marker_model, biosample_model)
        sample_information_df = fasta_info_obj.get_sample_information_df()
        # sample_info_record_list = fasta_information_obj.get_fasta_information_record_list()
        sample_info_record_list = list(sample_information_df.T.to_dict().values())

        ##########################################################
        #
        # 2. Delete marker/run/biosample/replicate from variant_read_count_model
        #
        ##########################################################

        variant_read_count_like_utils = VariantReadCountLikeTable(variant_read_count_like_model=output_filter_indel_model, engine=engine)
        variant_read_count_like_utils.delete_output_filter_model(fasta_info_record_list=sample_info_record_list)

        ##########################################################
        #
        # variant_read_count_df
        #
        ##########################################################

        filter_id = None
        sample_information_df = fasta_info_obj.get_sample_information_df(add_tag_primer_fasta=False)
        sample_information_df_analyzer = SampleInformationDfAnalyzer(engine, sample_information_df)
        variant_read_count_df = sample_information_df_analyzer.get_variant_read_count_df(variant_read_count_like_model
                                                                     =input_filter_renkonen_model, filter_id=filter_id)

        ##########################################################
        #
        #
        ##########################################################

        # else:
        # run_id, marker_id, variant_id, biosample_id, replicate, read_count, filter_delete
        variant_model_table = variant_model.__table__
        stmt_variant = select([variant_model_table.c.id,
                               variant_model_table.c.sequence])

        # Select to DataFrame
        variant_filter_lfn_passed_list = []
        with engine.connect() as conn:
            for row in conn.execute(stmt_variant).fetchall():
                variant_filter_lfn_passed_list.append(row)
        variant_df = pandas.DataFrame.from_records(variant_filter_lfn_passed_list,
                                                              columns=['id', 'sequence'])

        ##########################################################
        #
        # 4. Run Filter or not according to skip_filter_indel
        #
        ##########################################################

        if skip_filter_indel:  # do not run filter

            filter_output_df = variant_read_count_df.copy()
            filter_output_df['filter_delete'] = False

        else:  # run filter

            filter_output_df = f13_filter_indel(variant_read_count_df, variant_df)

        ##########################################################
        #
        # Write to DB
        #
        ##########################################################

        records = VariantReadCountLikeTable.filter_delete_df_to_dict(filter_output_df)
        with engine.connect() as conn:
            conn.execute(output_filter_indel_model.__table__.insert(), records)

        ##########################################################
        #
        # Exit vtam if all variants delete
        #
        ##########################################################

        try:
            assert not filter_output_df.filter_delete.sum() == filter_output_df.shape[0]
        except AssertionError:
            Logger.instance().warning(VTAMexception("This filter has deleted all the variants: {}. The analysis will stop here.".format(self.__class__.__name__)))
            sys.exit(0)




def f13_filter_indel(variant_read_count_df, variant_df):
    """
    filter chimera
    """

    df_out = variant_read_count_df.copy()
    df_out['filter_delete'] = False
    #
    df = variant_df.copy()
    df['sequence_length_module_3'] = variant_df.sequence.apply(lambda x: len(x) % 3) # compute module for each variant
    majority_sequence_length_module_3 = df.sequence_length_module_3.mode() # most common remaining of modulo 3
    # select id of variant that do not pass on a list
    df = df.loc[df['sequence_length_module_3'] != majority_sequence_length_module_3.values[0]]
    do_not_pass_variant_id_list = df.id.tolist()
    #
    for id in do_not_pass_variant_id_list:
        df_out.loc[df_out['variant_id'] == id, 'filter_delete'] = True
    #
    return df_out


