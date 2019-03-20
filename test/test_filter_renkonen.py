
from unittest import TestCase
from wopmetabarcoding.utils.PathFinder import PathFinder
import itertools
import os
from wopmetabarcoding.utils.constants import tempdir
import pandas
from wopmetabarcoding.wrapper.FilterRenkonen import renkonen_distance


class TestFilterRenkonen(TestCase):
    def setUp(self):
        self.variant_read_count_df = pandas.DataFrame({
            'run_id': [1] * 12,
            'marker_id': [1] * 12,
            'variant_id': [6] * 2 + [1] * 2 + [2] * 2 + [3] * 2 + [4] * 2 + [5] * 2,
            'biosample_id': [1] * 12,
            'replicate_id': [1, 2] * 6,
            'read_count': [
                25, 25, 350, 360, 335, 325, 350, 350, 325, 325, 35, 25
            ],
        })

        self.tempdir = os.path.join(tempdir, "FilterUtilities", self.__class__.__name__)
        PathFinder.mkdir_p(self.tempdir)

    def test_renkonen_distance(self):
        # Dj,k=1,k=2 = 1 – Sum i ( min(Ni,j,k=1 / Nj,k=1 , Ni,j,k=1 / Nk=2 ) )
        # Input
        variant_read_count_df = pandas.DataFrame({
            'run_id': [1] * 6,
            'marker_id': [1] * 6,
            'variant_id': [1] * 3 + [2] * 3,
            'biosample_id': [1] * 6,
            'replicate_id': [1, 2, 3] * 2,
            'read_count': [
                5180, 5254, 9378, 193, 99, 209
            ],
        })
        # Output
        # biosample_id 1, replicate_id 1, replicate_id 2, renkonen_similarity and distance 0.982573959807409 and 0.017426040192591
        # biosample_id 1, replicate_id 1, replicate_id 3, renkonen_similarity and distance 0.985880012193912 and 0.014119987806088

        # Compute sum of read_count per 'run_id', 'marker_id', 'biosample_id', 'replicate_id'
        variant_read_proportion_per_replicate_df = variant_read_count_df[
            ['run_id', 'marker_id', 'biosample_id', 'replicate_id', 'read_count']].groupby(
            by=['run_id', 'marker_id', 'biosample_id', 'replicate_id']).sum().reset_index()
        variant_read_proportion_per_replicate_df = variant_read_proportion_per_replicate_df.rename(columns={'read_count': 'read_count_sum_per_replicate'})

        # Merge variant read_count with read_count_sum_per_replicate
        variant_read_proportion_per_replicate_df = variant_read_count_df.merge(variant_read_proportion_per_replicate_df,
                                    left_on=['run_id', 'marker_id', 'biosample_id', 'replicate_id'],
                                        right_on=['run_id', 'marker_id', 'biosample_id', 'replicate_id'])

        variant_read_proportion_per_replicate_df['variant_read_count_propotion_per_replicate']\
            = variant_read_proportion_per_replicate_df.read_count / variant_read_proportion_per_replicate_df.read_count_sum_per_replicate
        variant_read_proportion_per_replicate_df.drop('read_count', axis=1, inplace=True)
        variant_read_proportion_per_replicate_df.drop('read_count_sum_per_replicate', axis=1, inplace=True)
        #

        # # Select the read proportion for the biosample_id, left_replicate
        # left_variant_read_proportion_per_replicate_per_biosample_df = variant_read_proportion_per_replicate_df.loc[
        #                                 (variant_read_proportion_per_replicate_df.run_id == run_id)
        #                                 & (variant_read_proportion_per_replicate_df.marker_id == marker_id)
        #                                 & (variant_read_proportion_per_replicate_df.biosample_id == biosample_id)
        #                                 & (variant_read_proportion_per_replicate_df.replicate_id == left_replicate_id)
        # ]
        #
        # # Select the read proportion for the biosample_id, left_replicate
        # right_variant_read_proportion_per_replicate_per_biosample_df = variant_read_proportion_per_replicate_df.loc[
        #                                 (variant_read_proportion_per_replicate_df.run_id == run_id)
        #                                 & (variant_read_proportion_per_replicate_df.marker_id == marker_id)
        #                                 & (variant_read_proportion_per_replicate_df.biosample_id == biosample_id)
        #                                 & (variant_read_proportion_per_replicate_df.replicate_id == right_replicate_id)
        # ]
        #
        # #Distance
        # # variant_read_proportion_per_replicate1_per_biosample_df = \
        # #     left_variant_read_proportion_per_replicate_per_biosample_df.loc[
        # #         left_variant_read_proportion_per_replicate_per_biosample_df.replicate_id == 1, ['variant_id', 'replicate_id', 'variant_read_count_propotion_per_replicate']]
        # #
        # # variant_read_proportion_per_replicate2_per_biosample_df = \
        # #     left_variant_read_proportion_per_replicate_per_biosample_df.loc[
        # #         left_variant_read_proportion_per_replicate_per_biosample_df.replicate_id == 2, ['variant_id', 'replicate_id', 'variant_read_count_propotion_per_replicate']]
        # #
        # # variant_read_proportion_per_replicate3_per_biosample_df = \
        # #     left_variant_read_proportion_per_replicate_per_biosample_df.loc[
        # #         left_variant_read_proportion_per_replicate_per_biosample_df.replicate_id == 3, ['variant_id', 'replicate_id',
        # #                                                                                    'variant_read_count_propotion_per_replicate']]
        #
        # # Merge left and right replicate
        # variant_read_proportion_per_replicate_left_right = left_variant_read_proportion_per_replicate_per_biosample_df.merge(\
        #                 right_variant_read_proportion_per_replicate_per_biosample_df,
        #                 on=['run_id', 'marker_id', 'variant_id', 'biosample_id'])
        # # rename columns
        # variant_read_proportion_per_replicate_left_right = variant_read_proportion_per_replicate_left_right.rename(
        #     columns={'replicate_id_x': 'replicate_id_left'})
        # variant_read_proportion_per_replicate_left_right = variant_read_proportion_per_replicate_left_right.rename(
        #     columns={'variant_read_count_propotion_per_replicate_x': 'variant_read_count_propotion_per_replicate_left'})
        # variant_read_proportion_per_replicate_left_right = variant_read_proportion_per_replicate_left_right.rename(
        #     columns={'replicate_id_y': 'replicate_id_right'})
        # variant_read_proportion_per_replicate_left_right = variant_read_proportion_per_replicate_left_right.rename(
        #     columns={'variant_read_count_propotion_per_replicate_y': 'variant_read_count_propotion_per_replicate_right'})
        # # variant_read_proportion_per_replicate_left_right.columns = ['variant_id', 'replicate_id1',
        # #                                                      'rp_of_variant_in_replicate1',
        # #                                                      'replicate_id2',
        # #                                                      'rp_of_variant_in_replicate2']
        #
        # # variant_read_proportion_per_replicate_left_right = variant_read_proportion_per_replicate_left_right[['variant_id','rp_of_variant_in_replicate1', 'rp_of_variant_in_replicate2']]
        #
        # variant_read_proportion_per_replicate_left_right['min_read_proportion'] = variant_read_proportion_per_replicate_left_right[
        #                                           ['variant_read_count_propotion_per_replicate_left', 'variant_read_count_propotion_per_replicate_right']].apply(lambda row: row.min(), axis=1)
        #
        # distance_left_right = 1 - sum(variant_read_proportion_per_replicate_left_right['min_read_proportion'])
        #
        run_id = 1
        marker_id = 1
        biosample_id = 1
        left_replicate_id = 1
        right_replicate_id = 2
        #
        distance_left_right_12 = renkonen_distance(variant_read_count_df,run_id,marker_id,biosample_id,left_replicate_id,right_replicate_id)
        right_replicate_id = 3
        distance_left_right_13= renkonen_distance(variant_read_count_df,run_id,marker_id,biosample_id,left_replicate_id,right_replicate_id)
        import pdb;
        pdb.set_trace()


    def test_delete_replicate(self):
        # TODO
        pass



    def test_f11_filter_renkonen(self):
            """

            :return: None
            """
            #

            # logger.debug(
            #     "file: {}; line: {}; {}".format(__file__, inspect.currentframe().f_lineno, this_filter_name))


            ########################################################
            # proportion of the reads of variant i per replicate j (Ni,j=1/Nj=1)
            ########################################################

            renkonen_tail = 0.013
            number_of_replicate = 2
            passsed_variant_ids= []
            variant_read_proportion_per_replicate_df = self.variant_read_count_df[['run_id', 'marker_id', 'biosample_id', 'replicate_id', 'read_count']].groupby(
                                                                                            by=['run_id', 'marker_id', 'biosample_id', 'replicate_id']).sum().reset_index()

            # # Merge the column with the total reads by sample replicates for calculate the ratio
            # variant_read_proportion_per_replicate_df = self.variant_read_count_df.merge(variant_read_proportion_per_replicate_df, left_on=['biosample_id', 'replicate_id'],
            #                                                                             right_on=['biosample_id', 'replicate_id'])
            # variant_read_proportion_per_replicate_df.columns = ['run_id', 'marker_id', 'variant_id', 'biosample_id', 'replicate_id','rc_per_v_per_b_per_r',
            #                                                        'rc_per_b_r']
            #
            #
            # variant_read_proportion_per_replicate_df['rp_of_variant_in_replicate'] = variant_read_proportion_per_replicate_df.rc_per_v_per_b_per_r / variant_read_proportion_per_replicate_df.rc_per_b_r
            #
            # # for biosample_id in self.variant_read_count_df.biosample_id.unique():
            # # replicate_combinatorics = itertools.permutations(self.variant_read_count_df.replicate_id.unique().tolist(), 2)
            # biosample_id = 1
            # replicate_id1 = 1
            # replicate_id2 = 2
            # variant_read_proportion_per_replicate_per_biosample_df = variant_read_proportion_per_replicate_df.loc[
            #                                                                 variant_read_proportion_per_replicate_df.biosample_id == biosample_id]
            #
            # ########################################################
            # # 2. Calculate renkonen distance index (D) for all pairs of replicates of the same sample
            # ########################################################
            # variant_read_proportion_per_replicate1_per_biosample_df = variant_read_proportion_per_replicate_per_biosample_df.loc[
            #     variant_read_proportion_per_replicate_per_biosample_df.replicate_id == replicate_id1, ['variant_id', 'replicate_id', 'rp_of_variant_in_replicate']]
            # variant_read_proportion_per_replicate2_per_biosample_df = variant_read_proportion_per_replicate_per_biosample_df.loc[
            #     variant_read_proportion_per_replicate_per_biosample_df.replicate_id == replicate_id2, ['variant_id', 'replicate_id', 'rp_of_variant_in_replicate']]
            # variant_read_proportion_per_replicate_1_2 = variant_read_proportion_per_replicate1_per_biosample_df.merge(variant_read_proportion_per_replicate2_per_biosample_df,
            #                                                                                                           on='variant_id')
            # variant_read_proportion_per_replicate_1_2.columns = ['variant_id', 'replicate_id1',
            #                                                      'rp_of_variant_in_replicate1',
            #                                                      'replicate_id2',
            #                                                      'rp_of_variant_in_replicate_2']
            #
            # variant_read_proportion_per_replicate_1_2 = variant_read_proportion_per_replicate_1_2[['variant_id','rp_of_variant_in_replicate1', 'rp_of_variant_in_replicate_2']]
            #
            #
            # variant_read_proportion_per_replicate_1_2['min_read_proportion'] = variant_read_proportion_per_replicate_1_2[
            #     ['rp_of_variant_in_replicate1', 'rp_of_variant_in_replicate_2']].apply(lambda row: row.min(), axis=1)
            #
            # columns_name = ['repl_i', 'repl_j', 'distance']
            # df_read_count_per_sample_replicate = self.variant_read_count_df.groupby(by=['replicate_id'])['read_count'].sum()
            # df_read_count_per_sample_replicate = df_read_count_per_sample_replicate.to_frame()
            # df_read_count_per_sample_replicate.columns = ['replicate_count']
            # df_read_count_per_sample_replicate = self.variant_read_count_df.merge(df_read_count_per_sample_replicate, left_on='replicate_id', right_index=True)
            # df_read_count_per_sample_replicate['proportion'] = df_read_count_per_sample_replicate['read_count'] / df_read_count_per_sample_replicate['replicate_count']
            #
            # # df_replicate = df_read_count_per_sample_replicate.groupby(by=['biosample'])['sample_replicate'].to_frame()
            # samples = df_read_count_per_sample_replicate['biosample_id']
            # samples = list(set(samples.tolist()))
            # #
            # for sample in samples:
            #     df_permutation_distance = pandas.DataFrame(columns=columns_name)
            #     df_replicate = df_read_count_per_sample_replicate.loc[df_read_count_per_sample_replicate['biosample_id'] == sample]
            #     replicates = list(set(df_replicate['replicate_id'].tolist()))
            #     for combi in itertools.permutations(replicates, 2):
            #         combi = list(combi)
            #         df_repli = df_replicate.loc[df_replicate['replicate_id'] == combi[0]]
            #         # import pdb;
            #         # pdb.set_trace()
            #         data_repli = df_repli[['variant_id', 'replicate_id', 'proportion']]
            #         df_replj = df_replicate.loc[df_replicate['replicate_id'] == combi[1]]
            #         data_replj = df_replj[['variant_id', 'replicate_id', 'proportion']]
            #         df_replij = data_repli.append(data_replj)
            #         group_repl = df_replij.groupby(by=['variant_id'])['proportion'].min()
            #         distance = 1 - group_repl.sum()
            #         query = [combi[0], combi[1], distance]
            #         df_permutation_distance.loc[len(df_permutation_distance)] = query
            #     # df_calc = df_permutation_distance.loc[df_permutation_distance['repl_i'] == combi[0]]
            #     indices_to_drop = list(
            #         df_permutation_distance.loc[df_permutation_distance.distance > renkonen_tail].index.tolist()
            #     )
            #     df_permutation_distance.drop(indices_to_drop, inplace=True)
            #     repl_list = list(set(df_permutation_distance['repl_i'].tolist()))
            #     for repl_i in repl_list:
            #         df_calc = df_permutation_distance.loc[df_permutation_distance['repl_i'] == repl_i]
            #         if len(df_calc) > ((number_of_replicate -1) / 2):
            #             index = self.variant_read_count_df.loc[self.variant_read_count_df['replicate_id'] == repl_i].index.tolist()
            #             passsed_variant_ids = sorted(list(set(index + passsed_variant_ids)))
            # # import pdb;
            # # pdb.set_trace()
            # return passsed_variant_ids