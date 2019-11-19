from vtam import Logger
from vtam.utils.FastaInformation import FastaInformation
from vtam.utils.VariantReadCountLikeTable import VariantReadCountLikeTable
from vtam.utils.OptionManager import OptionManager
from vtam.utils.VTAMexception import VTAMexception
from wopmars.framework.database.tables.ToolWrapper import ToolWrapper

import itertools
import pandas
import sys


class FilterRenkonen(ToolWrapper):
    __mapper_args__ = {
        "polymorphic_identity": "vtam.wrapper.FilterRenkonen"
    }

    # Input file
    __input_file_fastainfo = "fastainfo"
    # Input table
    __input_table_marker = "Marker"
    __input_table_run = "Run"
    __input_table_biosample = "Biosample"
    __input_table_replicate = "Replicate"
    __input_table_chimera = "FilterChimera"
    # Output table
    __output_table_filter_renkonen = "FilterRenkonen"

    def specify_input_file(self):
        return [
            FilterRenkonen.__input_file_fastainfo,

        ]

    def specify_input_table(self):
        return [
            FilterRenkonen.__input_table_marker,
            FilterRenkonen.__input_table_run,
            FilterRenkonen.__input_table_biosample,
            FilterRenkonen.__input_table_replicate,
            FilterRenkonen.__input_table_chimera,
        ]

    def specify_output_table(self):
        return [
            FilterRenkonen.__output_table_filter_renkonen,
        ]

    def specify_params(self):
        return {
            "upper_renkonen_tail": "float",
            # "log_verbosity": "int",
            # "log_file": "str"
        }

    def run(self):
        session = self.session()
        engine = session._WopMarsSession__session.bind

        ##########################################################
        #
        # Wrapper inputs, outputs and parameters
        #
        ##########################################################
        #
        # Input file output
        input_file_fastainfo = self.input_file(FilterRenkonen.__input_file_fastainfo)
        #
        # Input table models
        marker_model = self.input_table(FilterRenkonen.__input_table_marker)
        run_model = self.input_table(FilterRenkonen.__input_table_run)
        biosample_model = self.input_table(FilterRenkonen.__input_table_biosample)
        replicate_model = self.input_table(FilterRenkonen.__input_table_replicate)
        input_filter_chimera_model = self.input_table(FilterRenkonen.__input_table_chimera)
        #
        # Options
        # PoolMarkers parameters
        upper_renkonen_tail = float(self.option("upper_renkonen_tail"))
        #
        # Output table models
        output_filter_renkonen_model = self.output_table(FilterRenkonen.__output_table_filter_renkonen)

        ##########################################################
        #
        # 1. Read fastainfo to get run_id, marker_id, biosample_id, replicate_id for current analysis
        #
        ##########################################################

        fasta_info = FastaInformation(input_file_fastainfo, engine, run_model, marker_model, biosample_model, replicate_model)
        fasta_info_record_list = fasta_info.get_fasta_information_record_list()

        ##########################################################
        #
        # 2. Delete marker/run/biosample/replicate from variant_read_count_model
        #
        ##########################################################

        variant_read_count_like_utils = VariantReadCountLikeTable(variant_read_count_like_model=output_filter_renkonen_model, engine=engine)
        variant_read_count_like_utils.delete_output_filter_model(fasta_info_record_list=fasta_info_record_list)

        ##########################################################
        #
        # variant_read_count_df
        #
        ##########################################################

        filter_id = None
        variant_read_count_df = fasta_info.get_variant_read_count_df(variant_read_count_like_model=input_filter_chimera_model, filter_id=filter_id)

        ##########################################################
        #
        # 4. Run Filter
        #
        ##########################################################

        filter_output_df = f12_filter_delete_renkonen(variant_read_count_df, upper_renkonen_tail)


        ##########################################################
        #
        # Write to DB
        #
        ##########################################################

        records = VariantReadCountLikeTable.filter_delete_df_to_dict(filter_output_df)
        with engine.connect() as conn:
            conn.execute(output_filter_renkonen_model.__table__.insert(), records)

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


def renkonen_distance(variant_read_count_df, run_id, marker_id, biosample_id, left_replicate_id, right_replicate_id):
    #  Compute sum of read_count per 'run_id', 'marker_id', 'biosample_id', 'replicate_id'
    variant_read_proportion_per_replicate_df = variant_read_count_df[
        ['run_id', 'marker_id', 'biosample_id', 'replicate_id', 'read_count']].groupby(
        by=['run_id', 'marker_id', 'biosample_id', 'replicate_id']).sum().reset_index()
    variant_read_proportion_per_replicate_df = variant_read_proportion_per_replicate_df.rename(
        columns={'read_count': 'read_count_sum_per_replicate'})

    # Merge variant read_count with read_count_sum_per_replicate
    variant_read_proportion_per_replicate_df = variant_read_count_df.merge(variant_read_proportion_per_replicate_df,
                                                                           left_on=['run_id', 'marker_id',
                                                                                    'biosample_id', 'replicate_id'],
                                                                           right_on=['run_id', 'marker_id',
                                                                                     'biosample_id', 'replicate_id'])

    variant_read_proportion_per_replicate_df['variant_read_count_propotion_per_replicate'] \
        = variant_read_proportion_per_replicate_df.read_count / variant_read_proportion_per_replicate_df.read_count_sum_per_replicate
    variant_read_proportion_per_replicate_df.drop('read_count', axis=1, inplace=True)
    variant_read_proportion_per_replicate_df.drop('read_count_sum_per_replicate', axis=1, inplace=True)
    #

    # Select the read proportion for the biosample_id, left_replicate
    left_variant_read_proportion_per_replicate_per_biosample_df = variant_read_proportion_per_replicate_df.loc[
        (variant_read_proportion_per_replicate_df.run_id == run_id)
        & (variant_read_proportion_per_replicate_df.marker_id == marker_id)
        & (variant_read_proportion_per_replicate_df.biosample_id == biosample_id)
        & (variant_read_proportion_per_replicate_df.replicate_id == left_replicate_id)
        ]

    # Select the read proportion for the biosample_id, left_replicate
    right_variant_read_proportion_per_replicate_per_biosample_df = variant_read_proportion_per_replicate_df.loc[
        (variant_read_proportion_per_replicate_df.run_id == run_id)
        & (variant_read_proportion_per_replicate_df.marker_id == marker_id)
        & (variant_read_proportion_per_replicate_df.biosample_id == biosample_id)
        & (variant_read_proportion_per_replicate_df.replicate_id == right_replicate_id)
        ]

    #  Merge left and right replicate
    variant_read_proportion_per_replicate_left_right = left_variant_read_proportion_per_replicate_per_biosample_df.merge( \
        right_variant_read_proportion_per_replicate_per_biosample_df,
        on=['run_id', 'marker_id', 'variant_id', 'biosample_id'])
    # rename columns
    variant_read_proportion_per_replicate_left_right = variant_read_proportion_per_replicate_left_right.rename(
        columns={'replicate_id_x': 'replicate_id_left'})
    variant_read_proportion_per_replicate_left_right = variant_read_proportion_per_replicate_left_right.rename(
        columns={'variant_read_count_propotion_per_replicate_x': 'variant_read_count_propotion_per_replicate_left'})
    variant_read_proportion_per_replicate_left_right = variant_read_proportion_per_replicate_left_right.rename(
        columns={'replicate_id_y': 'replicate_id_right'})
    variant_read_proportion_per_replicate_left_right = variant_read_proportion_per_replicate_left_right.rename(
        columns={'variant_read_count_propotion_per_replicate_y': 'variant_read_count_propotion_per_replicate_right'})

    # variant_read_proportion_per_replicate_left_right = variant_read_proportion_per_replicate_left_right[['variant_id','rp_of_variant_in_replicate1', 'rp_of_variant_in_replicate2']]

    variant_read_proportion_per_replicate_left_right['min_read_proportion'] = \
    variant_read_proportion_per_replicate_left_right[
        ['variant_read_count_propotion_per_replicate_left', 'variant_read_count_propotion_per_replicate_right']].apply(
        lambda row: row.min(), axis=1)


    distance_left_right = 1 - sum(variant_read_proportion_per_replicate_left_right['min_read_proportion'])
    return distance_left_right


def f12_filter_delete_renkonen(variant_read_count_df, upper_renkonen_tail):
    dfout = variant_read_count_df.copy()
    # dfout['filter_id'] = 12
    dfout['filter_delete'] = False
    #
    # group by on variant read count df  and aggregate by replicate_id to get all the replicate_id by biosample_id
    df2 = variant_read_count_df.groupby(['run_id', 'marker_id', 'biosample_id']).agg('replicate_id').apply(
        lambda x: list(set(x))).reset_index()
    df2['threshold_distance_number'] = df2['replicate_id'].apply(lambda x: (len(x) - 1) / 2)
    df2 = df2.loc[df2.threshold_distance_number != 0] # drop if threshold_distance_number == 0
    if df2.shape[0] == 0: # Only one replicate
        dfout['filter_delete'] = True
    else:
        df2['replicate_id_pairwise'] = df2.replicate_id.apply(lambda x: list(itertools.combinations(x, 2)))
        df2.drop('replicate_id', axis=1, inplace=True)
        df3 = pandas.DataFrame(
            data={'run_id': [], 'marker_id': [], 'biosample_id': [], 'left_replicate_id': [], 'right_replicate_id': [],
                  'renkonen_distance': []}, dtype='int')
        for row in df2.itertuples():
            run_id = row.run_id
            marker_id = row.marker_id
            biosample_id = row.biosample_id
            replicate_id_pairwise = row.replicate_id_pairwise
            for left_replicate_id, right_replicate_id in replicate_id_pairwise:
                df3 = pandas.concat(
                    [df3, pandas.DataFrame({'run_id': [run_id], 'marker_id': [marker_id], 'biosample_id': [biosample_id],
                                            'left_replicate_id': [left_replicate_id],
                                            'right_replicate_id': [right_replicate_id]})], axis=0, sort=True)
        # count the renkonen distance by pair of replicate for each biosample_id
        for row in df3.itertuples():
            run_id = row.run_id
            marker_id = row.marker_id
            biosample_id = row.biosample_id
            left_replicate_id = row.left_replicate_id
            right_replicate_id = row.right_replicate_id
            d = renkonen_distance(variant_read_count_df, run_id, marker_id, biosample_id, left_replicate_id,
                                  right_replicate_id)
            df3.loc[(df3.run_id == run_id) & (df3.marker_id == marker_id) & (df3.biosample_id == biosample_id)
                    & (df3.left_replicate_id == left_replicate_id) & (
                                df3.right_replicate_id == right_replicate_id), 'renkonen_distance'] = d
        # compare the renkonen distance to the upper_renkonen_tail
        df3['is_distance_gt_rthr'] = df3.renkonen_distance > upper_renkonen_tail
        # extract from the data frame df3 the combinaison of (replicate_left ,is_distance_gt_rthr) and (replicate_right ,is_distance_gt_rthr)
        df4 = pandas.DataFrame(
            data={'run_id': [], 'marker_id': [], 'biosample_id': [], 'replicate_id': [], 'is_distance_gt_rthr': []},
            dtype='int')
        df4 = df4.rename(columns={'replicate_id': 'left_replicate_id'})
        df4 = pandas.concat([df4, df3[['run_id', 'marker_id', 'biosample_id', 'left_replicate_id', 'is_distance_gt_rthr']]])
        df4 = df4.rename(columns={'left_replicate_id': 'right_replicate_id'})
        df4 = pandas.concat(
            [df4, df3[['run_id', 'marker_id', 'biosample_id', 'right_replicate_id', 'is_distance_gt_rthr']]], axis=0)
        df4 = df4.rename(columns={'right_replicate_id': 'replicate_id'})
        # group the data frame by 'run_id', 'marker_id', 'biosample_id', 'replicate_id' to count the sum  distance number for each replicate by biosample
        # merge with the df2 to get the threshold_distance_number
        df5 = df4.groupby(['run_id', 'marker_id', 'biosample_id', 'replicate_id']).sum().reset_index()
        df5 = df5.rename(columns={'is_distance_gt_rthr': 'distance_number'})
        dfout = dfout.merge(df2[['run_id', 'marker_id', 'biosample_id', 'threshold_distance_number']])
        dfout = dfout.merge(df5[['run_id', 'marker_id', 'biosample_id', 'replicate_id', 'distance_number']])
        #if  distance_number > threshold_distance_number do not pass the renkonen filter
        # df5['filter_delete'] = False
        dfout.loc[dfout.distance_number > dfout.threshold_distance_number, 'filter_delete'] = True
        #merge resulted data frame df5 with the variant_read_count_df
        # dfout = variant_read_count_df.merge(df5)
        dfout.drop(['distance_number', 'threshold_distance_number'], axis=1, inplace=True)
    #
    return dfout


