
from wopmars.framework.database.tables.ToolWrapper import ToolWrapper
from wopmetabarcoding.wrapper.FilterPCRError import f10_get_maximal_pcr_error_value, f10_pcr_error_run_vsearch
from sqlalchemy import select
import pandas

from wopmetabarcoding.utils.utilities import create_step_tmp_dir


class OptimizePCRError(ToolWrapper):

    __mapper_args__ = {
        "polymorphic_identity": "wopmetabarcoding.wrapper.OptimizePCRError"
    }

    # Input file
    __input_file_positive_variants = "positive_variants"
    # Input table
    __input_table_run = "Run"
    __input_table_marker = "Marker"
    __input_table_variant = "Variant"
    __input_table_biosample = "Biosample"
    __input_table_variant_read_count = "VariantReadCount"
    # Output file
    __output_file_optimize_pcr_error = "optimize_pcr_error"

    #


    def specify_input_file(self):
        return[
            OptimizePCRError.__input_file_positive_variants,
        ]

    def specify_input_table(self):
        return [
            OptimizePCRError.__input_table_marker,
            OptimizePCRError.__input_table_run,
            OptimizePCRError.__input_table_variant,
            OptimizePCRError.__input_table_biosample,
            OptimizePCRError.__input_table_variant_read_count,
        ]


    def specify_output_file(self):
        return [
            OptimizePCRError.__output_file_optimize_pcr_error,
        ]

    def specify_params(self):
        return {
        }

    def run(self):
        session = self.session()
        engine = session._WopMarsSession__session.bind

        ##########################################################
        #
        # Wrapper inputs, outputs and parameters
        #
        ##########################################################
        ## Input file path
        input_file_positive_variants = self.input_file(OptimizePCRError.__input_file_positive_variants)
        #
        run_model = self.input_table(OptimizePCRError.__input_table_run)
        marker_model = self.input_table(OptimizePCRError.__input_table_marker)
        variant_model = self.input_table(OptimizePCRError.__input_table_variant)
        biosample_model = self.input_table(OptimizePCRError.__input_table_biosample)
        variant_read_count_model = self.input_table(OptimizePCRError.__input_table_variant_read_count)
        #
        # Output file path
        output_file_optimize_pcr_error = self.output_file(OptimizePCRError.__output_file_optimize_pcr_error)
        ################
        ##########################################################
        #
        # 1-Read positive_variants.tsv
        #
        ##########################################################
        positive_variant_df = pandas.read_csv(input_file_positive_variants, sep="\t", header=0, \
                                              names=['marker_name', 'run_name', 'biosample_name', 'variant_id',
                                                     'variant_sequence'], index_col=False)

        ##########################################################
        #
        # 2. Select run_id, marker_id, variant_id, biosample, replicate where variant, biosample, etc in positive_variants_df
        # 
        #
        ##########################################################
        variant_read_count_list = []
        with engine.connect() as conn:
            for row in positive_variant_df.itertuples():
                run_name = row.run_name
                marker_name = row.marker_name
                biosample_name = row.biosample_name
                variant_id = row.variant_id
                variant_sequence = row.variant_sequence
                stmt_select = select([
                    run_model.__table__.c.id,
                    marker_model.__table__.c.id,
                    variant_read_count_model.__table__.c.variant_id,
                    biosample_model.__table__.c.id,
                    variant_read_count_model.__table__.c.replicate_id,
                    variant_read_count_model.__table__.c.read_count, ]) \
                    .where(run_model.__table__.c.name == run_name) \
                    .where(variant_read_count_model.__table__.c.run_id == run_model.__table__.c.id) \
                    .where(marker_model.__table__.c.name == marker_name) \
                    .where(variant_read_count_model.__table__.c.marker_id == marker_model.__table__.c.id) \
                    .where(biosample_model.__table__.c.name == biosample_name) \
                    .where(variant_read_count_model.__table__.c.biosample_id == biosample_model.__table__.c.id) \
                    .where(variant_read_count_model.__table__.c.variant_id == variant_id) \
                    .distinct()
                variant_read_count_list = variant_read_count_list + conn.execute(stmt_select).fetchall()

        optimized_pcr_error_df = pandas.DataFrame.from_records(variant_read_count_list,
                                                                columns=['run_id', 'marker_id', 'variant_id', 'biosample_id',
                                                                'replicate_id', 'N_ijk'])

        # .where(variant_model.__table__.c.id == variant_read_count_model.__table__.c.variant_id) \
        #     .where(variant_model.__table__.c.sequence == variant_sequence) \
        # test if empty

        optimized_pcr_error_df.drop_duplicates(inplace=True)


        ##############
        #
        # Select all variants from Variant table
        #
        #############

        variant_list = []
        with engine.connect() as conn:
            stmt_select = select([
                variant_model.__table__.c.id,
                variant_model.__table__.c.sequence,])
            variant_list = variant_list + conn.execute(stmt_select).fetchall()

        variant_df = pandas.DataFrame.from_records(variant_list,
                                                               columns=['id', 'sequence'])
        ##############
        #
        # create variant_vsearch_db_df from variant_df based on the positive_variant_df.variant_id
        #
        #############
        variant_vsearch_db_df = variant_df.loc[variant_df.id.isin(positive_variant_df.variant_id.unique().tolist())][
            ['id', 'sequence']].drop_duplicates()
        variant_vsearch_db_df.rename(columns={'variant_id': 'id', 'variant_sequence': 'sequence'}, inplace=True)


        ##############
        #
        # run  f10_pcr_error_run_vsearch &  read_count_unexpected_expected_ratio_max
        #
        #############

        vsearch_output_df = f10_pcr_error_run_vsearch(variant_db_df=variant_vsearch_db_df, variant_usearch_global_df=variant_df, tmp_dir=create_step_tmp_dir(__file__))

        ##############
        #
        #  getting variant read count df  havinf the same biosample_name of the positifs variant
        #
        #############

        variant_read_count_list = []
        with engine.connect() as conn:
            for row in positive_variant_df.itertuples():
                run_name = row.run_name
                marker_name = row.marker_name
                biosample_name = row.biosample_name
                stmt_select = select([
                    run_model.__table__.c.id,
                    marker_model.__table__.c.id,
                    variant_read_count_model.__table__.c.variant_id,
                    biosample_model.__table__.c.id,
                    variant_read_count_model.__table__.c.replicate_id,
                    variant_read_count_model.__table__.c.read_count, ]) \
                    .where(run_model.__table__.c.name == run_name) \
                    .where(variant_read_count_model.__table__.c.run_id == run_model.__table__.c.id) \
                    .where(marker_model.__table__.c.name == marker_name) \
                    .where(variant_read_count_model.__table__.c.marker_id == marker_model.__table__.c.id) \
                    .where(biosample_model.__table__.c.name == biosample_name) \
                    .distinct()
                variant_read_count_list = variant_read_count_list + conn.execute(stmt_select).fetchall()

        variant_read_count_df = pandas.DataFrame.from_records(variant_read_count_list,
                                                               columns=['run_id', 'marker_id', 'variant_id',
                                                                        'biosample_id',
                                                                        'replicate_id', 'N_ijk'])

        read_count_unexpected_expected_ratio_max = f10_get_maximal_pcr_error_value(variant_read_count_df, vsearch_output_df)
        #

        df = pandas.DataFrame({"optimal_pcr_error_param": [read_count_unexpected_expected_ratio_max]})



        ##########################################################
        #
        # 7. Write TSV file
        #
        ##########################################################
        df.to_csv(output_file_optimize_pcr_error, header=True, sep='\t')



        #
        # 1. Read positive_variants.tsv
        # 2. Select run_id, marker_id, variant_id, biosample, replicate where variant, biosample, etc in positive_variants_df
        # 3. Get read_count: N_ijk
        # 4. Compute ratio per_sum_biosample_replicate: N_ijk / N_jk
        # 5. Compute ratio per_sum_variant: N_ijk / N_i
        # 6. Compute ratio per_sum_variant_replicate: N_ijk / N_ij
        # 7. Output run_name, marker_name, variant, positive biosample j, replicate k. N_ijk, N_jk , N_ijk /N_jk, N_ijk / N_i, N_ijk / N_ij

