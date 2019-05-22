import errno
import inspect
import os
import sqlite3
from wopmars.framework.database.tables.ToolWrapper import ToolWrapper
from sqlalchemy import select
import pandas
from wopmetabarcoding.utils.constants import rank_hierarchy, identity_list
from wopmetabarcoding.utils.logger import logger
from wopmetabarcoding.wrapper.TaxAssignUtilities import f04_1_tax_id_to_taxonomy_lineage
from wopmetabarcoding.utils.constants import rank_hierarchy_otu_table


class MakeOtuTable(ToolWrapper):
    __mapper_args__ = {
        "polymorphic_identity": "wopmetabarcoding.wrapper.MakeOtuTable"}

    # Input file
    taxonomy_sqlite_path = os.path.join(os.environ['DIR_DATA_NON_GIT'], 'taxonomy.sqlite')
    __input_file_sample2fasta = "sample2fasta"
    __input_file_taxonomy = "taxonomy"
    # Input table
    __input_table_marker = "Marker"
    __input_table_run = "Run"
    __input_table_biosample = "Biosample"
    __input_table_replicate = "Replicate"
    __input_table_filter_codon_stop = "FilterCodonStop"
    __input_table_variant = "Variant"
    __input_table_tax_assign = "TaxAssign"

    # Output table
    __output_table_otu = "OTUTable"

    def specify_input_file(self):
        return[
            MakeOtuTable.__input_file_sample2fasta,
            MakeOtuTable.__input_file_taxonomy,
        ]

    def specify_input_table(self):
        return [
            MakeOtuTable.__input_table_marker,
            MakeOtuTable.__input_table_run,
            MakeOtuTable.__input_table_biosample,
            MakeOtuTable.__input_table_replicate,
            MakeOtuTable.__input_table_variant,
            MakeOtuTable.__input_table_filter_codon_stop,
            MakeOtuTable.__input_table_tax_assign,
        ]

    def specify_output_file(self):
        return[
            MakeOtuTable.__output_table_otu,

        ]

    def specify_params(self):
        return {

        }

    def run(self):
        session = self.session()
        engine = session._WopMarsSession__session.bind

        ##########################################################
        #
        # 1. Wrapper inputs, outputs and parameters
        #
        ##########################################################
        #
        # Input file path
        taxonomy_sqlite_path = self.input_file(MakeOtuTable.__input_file_taxonomy)
        input_file_sample2fasta = self.input_file(MakeOtuTable.__input_file_sample2fasta)
        #
        # Input table models
        marker_model = self.input_table(MakeOtuTable.__input_table_marker)
        run_model = self.input_table(MakeOtuTable.__input_table_run)
        biosample_model = self.input_table(MakeOtuTable.__input_table_biosample)
        replicate_model = self.input_table(MakeOtuTable.__input_table_replicate)
        filter_codon_stop_model = self.input_table(MakeOtuTable.__input_table_filter_codon_stop)
        variant_model = self.input_table(MakeOtuTable.__input_table_variant)
        tax_assign_model = self.input_table(MakeOtuTable.__input_table_tax_assign)
        # Output table models
        otu_table_tsv_path = self.output_file(MakeOtuTable.__output_table_otu)
        #
        # Options


        # ##########################################################
        # #
        # # 2. Read sample2fasta to get run_id, marker_id, biosample_id, replicate_id for current analysis
        # #
        # ##########################################################
        # sample2fasta_df = pandas.read_csv(input_file_sample2fasta, sep="\t", header=None,\
        #     names=['tag_forward', 'primer_forward', 'tag_reverse', 'primer_reverse', 'marker_name', 'biosample_name',\
        #     'replicate_name', 'run_name', 'fastq_fwd', 'fastq_rev', 'fasta'])
        # sample_instance_list = []
        # for row in sample2fasta_df.itertuples():
        #     marker_name = row.marker_name
        #     run_name = row.run_name
        #     biosample_name = row.biosample_name
        #     replicate_name = row.replicate_name
        #     with engine.connect() as conn:
        #         # get run_id ###########
        #         stmt_select_run_id = select([run_model.__table__.c.id]).where(run_model.__table__.c.name==run_name)
        #         run_id = conn.execute(stmt_select_run_id).first()[0]
        #         # get marker_id ###########
        #         stmt_select_marker_id = select([marker_model.__table__.c.id]).where(marker_model.__table__.c.name==marker_name)
        #         marker_id = conn.execute(stmt_select_marker_id).first()[0]
        #         # get biosample_id ###########
        #         stmt_select_biosample_id = select([biosample_model.__table__.c.id]).where(biosample_model.__table__.c.name==biosample_name)
        #         biosample_id = conn.execute(stmt_select_biosample_id).first()[0]
        #         # get replicate_id ###########
        #         stmt_select_replicate_id = select([replicate_model.__table__.c.id]).where(replicate_model.__table__.c.name==replicate_name)
        #         replicate_id = conn.execute(stmt_select_replicate_id).first()[0]
        #         # add this sample_instance ###########
        #         sample_instance_list.append({'run_id': run_id, 'marker_id': marker_id, 'biosample_id':biosample_id, 'replicate_id':replicate_id})

        ##########################################################
        #
        # 3a. Select variants from this run/markerbiosample/replicate combination
        # 3b. Delete variants from this run/markerbiosample/replicate combination
        #
        ##########################################################
        #
        # 3a. Select variants from this run/markerbiosample/replicate combination
        #
        # variant_id_delete_list = []
        # for sample_instance in sample_instance_list:
        #     stmt_select_variant_id_delete = select([filter_codon_stop_model.__table__.c.variant_id])\
        #         .where(filter_codon_stop_model.__table__.c.run_id == sample_instance['run_id'])\
        #         .where(filter_codon_stop_model.__table__.c.marker_id == sample_instance['marker_id'])\
        #         .where(filter_codon_stop_model.__table__.c.biosample_id == sample_instance['biosample_id'])\
        #         .where(filter_codon_stop_model.__table__.c.replicate_id == sample_instance['replicate_id'])
        #     # Select to DataFrame
        #     with engine.connect() as conn:
        #         for row in conn.execute(stmt_select_variant_id_delete).fetchall():
        #             variant_id = row[0]
        #             if not variant_id in variant_id_delete_list:
        #                 variant_id_delete_list.append(row)
        # #
        # # 3b. Delete variants from this run/markerbiosample/replicate combination
        # #
        # variant_instance_list = [{'variant_id': variant_id} for variant_id in variant_id_delete_list]
        # with engine.connect() as conn:
        #     conn.execute(tax_assign_model.__table__.delete(), variant_instance_list)

        #
        ##########################################################
        #
        # Get variants that passed the filter
        #
        ##########################################################
        logger.debug(
            "file: {}; line: {}; Get variants and sequences that passed the filters".format(__file__, inspect.currentframe().f_lineno,'TaxAssign'))

        filter_codon_stop_model_table = filter_codon_stop_model.__table__
        variant_model_table = variant_model.__table__
        stmt_filter_codon_stop = select([filter_codon_stop_model_table.c.variant_id, variant_model_table.c.sequence]) \
            .where(filter_codon_stop_model_table.c.variant_id == variant_model_table.c.id) \
            .where(filter_codon_stop_model_table.c.filter_delete == 0).distinct().order_by("variant_id")
        # Select to DataFrame
        variant_list = []
        with engine.connect() as conn:
            for row in conn.execute(stmt_filter_codon_stop).fetchall():
                variant_list.append(row)
        variant_df = pandas.DataFrame.from_records(variant_list, columns=['variant_id', 'variant_sequence'])

        ##########################################################
        #
        # Getting table to data frame
        #
        ##########################################################

        #####
        #
        # table run
        #
        #####
        run_model_table = run_model.__table__
        stmt_run = select([run_model_table.c.id,
                           run_model_table.c.name])

        # Select to DataFrame
        run_list = []
        with engine.connect() as conn:
            for row in conn.execute(stmt_run).fetchall():
                run_list.append(row)
        run_df = pandas.DataFrame.from_records(run_list,
                                               columns=['id', 'name'])

        #####
        #
        # table biosample
        #
        #####
        biosample_model_table = biosample_model.__table__
        stmt_biosample = select([biosample_model_table.c.id,
                                 biosample_model_table.c.name])

        # Select to DataFrame
        biosample_list = []
        with engine.connect() as conn:
            for row in conn.execute(stmt_biosample).fetchall():
                biosample_list.append(row)
        biosample_df = pandas.DataFrame.from_records(biosample_list,
                                                     columns=['id', 'name'])


        #####
        #
        # table marker
        #
        #####
        marker_model_table = marker_model.__table__
        stmt_marker = select([marker_model_table.c.id,
                              marker_model_table.c.name])

        # Select to DataFrame
        marker_list = []
        with engine.connect() as conn:
            for row in conn.execute(stmt_marker).fetchall():
                marker_list.append(row)
        marker_df = pandas.DataFrame.from_records(marker_list,
                                                  columns=['id', 'name'])


        #####
        #
        # ltg_tax_assign
        #
        #####

        tax_assign_model_table = tax_assign_model.__table__
        stmt_ltg_tax_assign = select([tax_assign_model_table.c.variant_id,
                               tax_assign_model_table.c.identity,
                               tax_assign_model_table.c.ltg_rank,
                               tax_assign_model_table.c.ltg_tax_id])

        # Select to DataFrame
        tax_assign_list = []
        with engine.connect() as conn:
            for row in conn.execute(stmt_ltg_tax_assign).fetchall():
                tax_assign_list.append(row)
        ltg_tax_assign_df = pandas.DataFrame.from_records(tax_assign_list,
                                                          columns=['variant_id', 'identity','ltg_rank','ltg_tax_id'])

        #####
        #
        # filter_codon_stop_model_table
        #
        #####

        filter_codon_stop_model_table = filter_codon_stop_model.__table__
        stmt_filter_codon_stop = select([filter_codon_stop_model_table.c.run_id,
                               filter_codon_stop_model_table.c.marker_id,
                               filter_codon_stop_model_table.c.variant_id,
                               filter_codon_stop_model_table.c.biosample_id,
                               filter_codon_stop_model_table.c.replicate_id,
                               filter_codon_stop_model_table.c.read_count])\
            .where(filter_codon_stop_model_table.c.filter_delete == 0).distinct().order_by("variant_id")
        # Select to DataFrame
        filter_codon_stop_list = []
        with engine.connect() as conn:
            for row in conn.execute(stmt_filter_codon_stop).fetchall():
                filter_codon_stop_list.append(row)
        filter_codon_stop_df = pandas.DataFrame.from_records(filter_codon_stop_list, columns=['run_id', 'marker_id', 'variant_id', 'biosample_id', 'replicate_id', 'read_count'])

        #####
        #
        # taxonomy_db to df
        #
        #####

        con = sqlite3.connect(taxonomy_sqlite_path)
        sql = """SELECT *  FROM taxonomy """
        taxonomy_db_df = pandas.read_sql(sql=sql, con=con)
        con.close()

        #

        #####
        #
        # make Otu table & write it to a tsv file
        #
        #####



        otu_df = f16_otu_table_maker(run_df, marker_df, variant_df, biosample_df, filter_codon_stop_df, ltg_tax_assign_df,
                            taxonomy_db_df)

        otu_df.to_csv(otu_table_tsv_path, sep='\t', index=False, header=True)

def f16_otu_table_maker(run_df,marker_df,variant_df,biosample_df,filter_codon_stop_df,ltg_tax_assign_df,taxonomy_db_df):
    """
    otu table maker
    """
    # Initialize out_df
    otu_df = variant_df.copy()
    #
    # Add Variant Sequence length
    variant_df_tmp = variant_df.copy()
    variant_df_tmp['sequence_length'] = variant_df_tmp['variant_sequence'].str.len()
    otu_df = otu_df.merge(variant_df_tmp, on=['variant_id', 'variant_sequence'])
    #
    # Add read_count_sum_per_variant
    read_count_sum_per_variant = filter_codon_stop_df.groupby('variant_id').sum().reset_index()[
        ['variant_id', 'read_count']]
    otu_df = otu_df.merge(read_count_sum_per_variant, on='variant_id')
    #
    # Merge variants and read_count per biosample
    # otu_df = variant_df.merge(filter_codon_stop_df, on='variant_id')
    #
    ############################
    #
    # Prepare biosamples data
    #
    ############################
    #
    # Sum read counts over replicates of each biosample
    otu_biosamples_df = filter_codon_stop_df.groupby(['run_id', 'marker_id', 'variant_id', 'biosample_id'])[
        'read_count'].sum().reset_index()
    #
    # Replace biosample ids with their name
    otu_biosamples_df = otu_biosamples_df.merge(biosample_df, left_on='biosample_id', right_on='id')
    otu_biosamples_df.drop(['biosample_id', 'id'], axis=1, inplace=True)
    otu_biosamples_df = otu_biosamples_df.rename(columns={'name': 'biosample_name'})
    #
    # Replace marker ids with their name
    otu_biosamples_df = otu_biosamples_df.merge(marker_df, left_on='marker_id', right_on='id')
    otu_biosamples_df.drop(['marker_id', 'id'], axis=1, inplace=True)
    otu_biosamples_df = otu_biosamples_df.rename(columns={'name': 'marker_name'})
    #
    # Replace run ids with their name
    otu_biosamples_df = otu_biosamples_df.merge(run_df, left_on='run_id', right_on='id')
    otu_biosamples_df.drop(['run_id', 'id'], axis=1, inplace=True)
    otu_biosamples_df = otu_biosamples_df.rename(columns={'name': 'run_name'})
    #
    # Pivot biosamples
    otu_biosamples_df = otu_biosamples_df.pivot_table(index=['run_name', 'marker_name', 'variant_id'],
                                                      columns="biosample_name",
                                                      values='read_count', fill_value=0).reset_index()
    #
    ############################
    #
    # Merge variant and biosample information
    #
    ############################
    otu_df = otu_df.merge(otu_biosamples_df, on='variant_id')
    #
    #
    # Merge ltg tax assign results
    otu_df = otu_df.merge(ltg_tax_assign_df, on='variant_id')
    list_lineage = []
    for tax_id in otu_df['ltg_tax_id'].unique().tolist():
        dic_lineage = f04_1_tax_id_to_taxonomy_lineage(tax_id, taxonomy_db_df, give_tax_name=True)
        list_lineage.append(dic_lineage)
    lineage_df = pandas.DataFrame(data=list_lineage)
    lineage_list_df_columns_sorted = list(filter(lambda x: x in lineage_df.columns.tolist(), rank_hierarchy_otu_table))
    lineage_list_df_columns_sorted = lineage_list_df_columns_sorted + ['tax_id']
    lineage_df = lineage_df[lineage_list_df_columns_sorted]

    # Merge Otu_df with the lineage df
    otu_df = otu_df.merge(lineage_df, left_on='ltg_tax_id', right_on='tax_id')
    otu_df.drop('tax_id', axis=1, inplace=True)


    ##########################
    #
    # Reorganize columns
    #
    ##########################
    otu_df_columns = otu_df.columns.tolist()
    # move items to given positions
    otu_df_columns.insert(1, otu_df_columns.pop(otu_df_columns.index('marker_name')))
    otu_df_columns.insert(2, otu_df_columns.pop(otu_df_columns.index('run_name')))
    otu_df_columns.insert(3, otu_df_columns.pop(otu_df_columns.index('sequence_length')))
    otu_df_columns.insert(4, otu_df_columns.pop(otu_df_columns.index('read_count')))
    #
    # append at the end
    otu_df_columns = otu_df_columns + [otu_df_columns.pop(otu_df_columns.index('ltg_tax_id'))]
    otu_df_columns = otu_df_columns + [otu_df_columns.pop(otu_df_columns.index('identity'))]
    otu_df_columns = otu_df_columns + [otu_df_columns.pop(otu_df_columns.index('ltg_rank'))]
    otu_df_columns = otu_df_columns + [otu_df_columns.pop(otu_df_columns.index('variant_sequence'))]
    #
    # reorder
    otu_df = otu_df[otu_df_columns]

    return otu_df