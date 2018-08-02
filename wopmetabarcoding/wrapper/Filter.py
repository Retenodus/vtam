import errno
from wopmars.utils.Logger import Logger
from wopmars.framework.database.tables.ToolWrapper import ToolWrapper
from wopmars.utils.Logger import Logger
from wopmetabarcoding.utils.PathFinder import PathFinder

from wopmetabarcoding.utils.constants import tempdir
from wopmetabarcoding.wrapper.FilterUtilities import FilterRunner
from sqlalchemy import select
import pandas, os, pickle


class Filter(ToolWrapper):
    __mapper_args__ = {
        "polymorphic_identity": "wopmetabarcoding.wrapper.Filter"
    }

    # Input tables:
    __input_table_marker = "Marker"
    __input_table_variant = "Variant"
    __input_table_variant_read_count = "VariantReadCount"
    __input_table_replicate = "Replicate"
    __output_table_passed_variant = "PassedVariant"
    # Input file
    __input_sortreads_samplecount_csv = "SortReads_sample_counts"
    __input_cutoff_file = "file_cutoff"
    __input_genetic_code_file = "genetic_code"
    # Output file
    __output_marker_variant_path = "marker_variant_path"


    def specify_input_table(self):
        return [
            Filter.__input_table_variant,
            Filter.__input_table_variant_read_count,
        ]

    def specify_input_file(self):
        return[
            # Filter.__input_sortreads_samplecount_csv,
            Filter.__input_cutoff_file,
            Filter.__input_genetic_code_file
        ]


    def specify_output_table(self):
        return [
            Filter.__output_table_passed_variant,
        ]

    def specify_output_file(self):
        return[
            Filter.__output_marker_variant_path
        ]

    def specify_params(self):
        return {
            "lfn_per_replicate_threshold": "float",
            "lfn_per_variant_threshold": "float",
            "lfn_per_replicate_series_threshold": "float",
            "lfn_read_count_threshold": "float",
            "repeatability_threshold": "int",
            "pcr_error_var_prop": "float",
            "renkonen_number_of_replicate": "int",
            "renkonen_renkonen_tail": "float"
        }

    def run(self):
        session = self.session()
        engine = session._WopMarsSession__session.bind
        conn = engine.connect()
        #
        # # Input file path
        # # sortreads_samplecount = self.input_file(Filter.__input_sortreads_samplecount_csv)
        cutoff_file_tsv = self.input_file(Filter.__input_cutoff_file)
        genetic_code_tsv = self.input_file(Filter.__input_genetic_code_file)
        #
        # Input table models
        variant_model = self.input_table(Filter.__input_table_variant)
        variant_read_count_model = self.input_table(Filter.__input_table_variant_read_count)
        #
        # Output table models
        passed_variant_model = self.output_table(Filter.__output_table_passed_variant)
        with engine.connect() as conn:
            conn.execute(passed_variant_model.__table__.delete())
        #
        # Create variant_read_count_df to run the filters with:
        # variant_id, biosample_id, replicate_id, read_count, variant_sequence
        variant_model_table = variant_model.__table__
        variant_read_count_model_table = variant_read_count_model.__table__
        stmt_marker_id = select([variant_read_count_model_table.c.marker_id]).distinct()
        # Execute filter in a per_marker basis
        with engine.connect() as conn:
            for row in conn.execute(stmt_marker_id).fetchall():
                marker_id = row[0]
                #
                # Create wrapper outdir in a per marker basis
                tempdir_marker = os.path.join(tempdir, "FilterUtilities", "marker_id_{}".format(marker_id))
                PathFinder.mkdir_p(tempdir_marker)
                #
                # Create variant_read_count DF for given marker
                stmt_variant_read_count = select([variant_read_count_model_table.c.variant_id,
                                                               variant_read_count_model_table.c.biosample_id,
                                                               variant_read_count_model_table.c.replicate_id,
                                                               variant_read_count_model_table.c.read_count])\
                    .where(variant_read_count_model_table.c.marker_id == marker_id)
                variant_read_count_list = []
                for row2 in conn.execute(stmt_variant_read_count).fetchall():
                    variant_read_count_list.append(row2)
                variant_read_count_df = pandas.DataFrame.from_records(variant_read_count_list, columns=['variant_id', 'biosample_id', 'replicate_id', 'read_count'])
                #
                # Create variant DF for given marker
                stmt_variant_read_count = select([variant_model_table.c.id, variant_model_table.c.sequence])\
                    .where(variant_read_count_model_table.c.marker_id == marker_id)\
                    .where(variant_read_count_model_table.c.variant_id == variant_model_table.c.id)
                variant_list = []
                for row2 in conn.execute(stmt_variant_read_count).fetchall():
                    variant_list.append(row2)
                variant_df = pandas.DataFrame.from_records(variant_list, columns=['id', 'sequence'])
                #
                filter_obj = FilterRunner(variant_df, variant_read_count_df)
                #
                # Filter parameters
                lfn_per_replicate_threshold = self.option("lfn_per_replicate_threshold")
                lfn_per_variant_threshold = self.option("lfn_per_variant_threshold")
                lfn_per_replicate_series_threshold = self.option("lfn_per_replicate_series_threshold")
                lfn_read_count_threshold = self.option("lfn_read_count_threshold")
                #
                Logger.instance().info("Launching LFN filter:")
                #
                ############################################
                # Filter 1: f1_lfn1_per_replicate
                ############################################
                filter_obj.f1_lfn1_per_replicate(lfn_per_replicate_threshold)
                #
                ############################################
                # Filter 2: f2_lfn2_per_variant
                # Filter 3: f3_lfn2_per_replicate_series
                ############################################
                f2_lfn2_per_variant = True
                if f2_lfn2_per_variant:
                    filter_obj.f2_lfn2_per_variant(lfn_per_variant_threshold)
                else:
                    filter_obj.f3_lfn2_per_replicate_series(lfn_per_replicate_series_threshold)
                #
                ############################################
                # Filter 4: f4_lfn3_read_count
                ############################################
                filter_obj.f4_lfn3_read_count(lfn_read_count_threshold)
                #
                ############################################
                # Filter 5: f5_lfn4_per_variant_with_cutoff
                # Filter 6: f6_lfn4_per_replicate_series_with_cutoff
                ############################################
                f5_lfn4_per_variant_with_cutoff = True
                if f5_lfn4_per_variant_with_cutoff:
                    # TODO: Default cutoff must be chosen
                    filter_obj.f5_lfn4_per_variant_with_cutoff(cutoff_file_tsv, engine, variant_model)
                else:
                    # TODO: Default cutoff must be chosen
                    filter_obj.f6_lfn4_per_replicate_series_with_cutoff(cutoff_file_tsv)
                #
                ############################################
                # Filter 7: Repeatability: f7_min_repln
                # Filter 8: Repeatability: f8_min_replp
                ############################################
                repln = True
                if repln:
                    filter_obj.f7_min_repln(2)
                else:
                    filter_obj.f8_min_replp(3)
                #
                ###########################################
                # Filter 9: PCR error
                ###########################################
                # filter_obj.f9_pcr_error(self.option("pcr_error_var_prop"), pcr_error_by_sample=True,
                #                                                      fasta_dir = tempdir_marker)
                #
                ############################################
                # Filter 10: Chimera
                ############################################
                # filter_obj.f10_pass_chimera(chimera_by_sample_replicate=True, engine=engine, variant_model=variant_model, fasta_dir=tempdir_marker)
                #
                ############################################
                # Filter 11: Renkonen
                ############################################
                # filter_obj.f11_pass_renkonen(self.option("renkonen_number_of_replicate"), self.option("renkonen_renkonen_tail"))
                #
                ############################################
                # Filter 12: Indel
                ############################################
                filter_obj.f12_indel()
                #
                ############################################
                # Filter: Stop codon
                ############################################
                #     df_codon_stop_per_genetic_code = self.codon_stop_dataframe(genetic_code_tsv)
                #     Logger.instance().info("Launching pseudogene detection with codon stop filter:")
                #     filter_obj.codon_stop(df_codon_stop_per_genetic_code, 2, False)
                #     filter_obj.consensus()
                #     variant2sample2replicate2count_df = filter_obj.filtered_variants()
                #
                ################################
                # Insert into db
                ################################
                filter_obj.passed_variant_df['variant_id'] = filter_obj.passed_variant_df.index
                records = list(filter_obj.passed_variant_df.T.to_dict().values())
                with engine.connect() as conn:
                    conn.execute(passed_variant_model.__table__.insert(), records)


