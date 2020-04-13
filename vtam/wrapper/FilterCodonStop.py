from Bio.Alphabet import IUPAC
from Bio.Seq import Seq
from sqlalchemy import bindparam

from vtam.utils.SampleInformationUtils import FastaInformationTSV
from vtam.utils.VariantReadCountLikeTable import VariantReadCountLikeTable
from vtam.utils.Logger import Logger
from vtam.utils.VTAMexception import VTAMexception
from wopmars.models.ToolWrapper import ToolWrapper

import Bio
import sys


class FilterCodonStop(ToolWrapper):
    __mapper_args__ = {
        "polymorphic_identity": "vtam.wrapper.FilterCodonStop"
    }

    # Input file
    __input_file_readinfo = "readinfo"
    # Input table
    __input_table_marker = "Marker"
    __input_table_run = "Run"
    __input_table_biosample = "Biosample"
    __input_table_filter_indel = "FilterIndel"
    __input_table_Variant = "Variant"
    # Output table
    __output_table_filter_codon_stop = "FilterCodonStop"



    def specify_input_file(self):
        return[
            FilterCodonStop.__input_file_readinfo,
        ]

    def specify_input_table(self):
        return [
            FilterCodonStop.__input_table_marker,
            FilterCodonStop.__input_table_run,
            FilterCodonStop.__input_table_biosample,
            FilterCodonStop.__input_table_filter_indel,
            FilterCodonStop.__input_table_Variant,
        ]


    def specify_output_table(self):
        return [
            FilterCodonStop.__output_table_filter_codon_stop,

        ]

    def specify_params(self):
        return {
            "genetic_table_number": "int",
            "skip_filter_codon_stop": "int",
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
        fasta_info_tsv = self.input_file(FilterCodonStop.__input_file_readinfo)
        #
        # Input table models
        marker_model = self.input_table(FilterCodonStop.__input_table_marker)
        run_model = self.input_table(FilterCodonStop.__input_table_run)
        biosample_model = self.input_table(FilterCodonStop.__input_table_biosample)
        variant_model = self.input_table(FilterCodonStop.__input_table_Variant)
        input_filter_indel_model = self.input_table(FilterCodonStop.__input_table_filter_indel)
        #
        # Options
        genetic_table_number = int(self.option("genetic_table_number"))
        skip_filter_codon_stop = bool(int(self.option("genetic_table_number")))
        #
        # Output table models
        output_filter_codon_stop_model = self.output_table(FilterCodonStop.__output_table_filter_codon_stop)

        ##########################################################
        #
        # 1. Read readinfo to get run_id, marker_id, biosample_id, replicate for current analysis
        #
        ##########################################################

        fasta_info_tsv = FastaInformationTSV(engine=engine, fasta_info_tsv=fasta_info_tsv)

        ##########################################################
        #
        # 2. Delete marker/run/biosample/replicate from variant_read_count_model
        #
        ##########################################################

        variant_read_count_like_utils = VariantReadCountLikeTable(variant_read_count_like_model=output_filter_codon_stop_model, engine=engine)
        variant_read_count_like_utils.delete_from_db(sample_record_list=fasta_info_tsv.sample_record_list)

        ##########################################################
        #
        # variant_read_count_input_df
        #
        ##########################################################

        variant_read_count_df = fasta_info_tsv.get_variant_read_count_df(
            variant_read_count_like_model=input_filter_indel_model, filter_id=None)
        variant_df = fasta_info_tsv.get_variant_df(variant_read_count_like_model=input_filter_indel_model,
                                               variant_model=variant_model)

        ##########################################################
        #
        # 4. Run Filter or not according to skip_filter_codon_stop
        #
        ##########################################################

        if skip_filter_codon_stop:  # do not run filter

            filter_output_df = variant_read_count_df.copy()
            filter_output_df['filter_delete'] = False

        else:  # run filter
            filter_output_df = f14_filter_codon_stop(variant_read_count_df, variant_df, genetic_table_number)

        ##########################################################
        #
        # Write to DB
        #
        ##########################################################

        record_list = VariantReadCountLikeTable.filter_delete_df_to_dict(filter_output_df)
        with engine.connect() as conn:

            # Insert new instances
            conn.execute(output_filter_codon_stop_model.__table__.insert(), record_list)

        ################################################################################################################
        #
        # Touch output tables, to update modification date
        #
        ################################################################################################################

        for output_table_i in self.specify_output_table():
            declarative_meta_i = self.output_table(output_table_i)
            obj = session.query(declarative_meta_i).order_by(declarative_meta_i.id.desc()).first()
            session.query(declarative_meta_i).filter_by(id=obj.id).update({'id': obj.id})
            session.commit()

        ##########################################################
        #
        # Exit vtam if all variants deleted
        #
        ##########################################################

        if filter_output_df.filter_delete.sum() == filter_output_df.shape[0]:
            Logger.instance().warning(VTAMexception("This filter has deleted all the variants: {}. "
                                                    "The analysis will stop here.".format(self.__class__.__name__)))
            sys.exit(0)


def f14_filter_codon_stop(variant_read_count_df, variant_df, genetic_table_number=5):
    """
    filter chimera
    """
    df = variant_df.copy()
    df2 = variant_read_count_df.copy()
    df2['filter_delete'] = False
    #
    df['orf1_codon_stop_nb'] = 0
    df['orf2_codon_stop_nb'] = 0
    df['orf3_codon_stop_nb'] = 0
    df['min_nb_codon_stop'] = 1
    #

    #
    orf_frame_index = 1  #  1-based
    #

    for row in df.iterrows():
        id = row[1].id
        sequence = row[1].sequence
        #
        sequence_orf1 = sequence[orf_frame_index - 1:] # get 1st orf sequence
        sequence_orf1 = sequence_orf1[0:len(sequence_orf1) - (len(sequence_orf1) % 3)] # trimming for module 3
        orf1_nb_codon_stop = str(Seq(sequence_orf1, IUPAC.unambiguous_dna).translate(
            Bio.Data.CodonTable.generic_by_id[genetic_table_number])).count('*')
        df.loc[df.id == id, 'orf1_codon_stop_nb'] = orf1_nb_codon_stop
        #
        sequence_orf2 = sequence[orf_frame_index:] # get 2nd orf sequence
        sequence_orf2 = sequence_orf2[0:len(sequence_orf2) - (len(sequence_orf2) % 3)] # trimming for module 3
        orf2_nb_codon_stop = str(Seq(sequence_orf2, IUPAC.unambiguous_dna).translate(
            Bio.Data.CodonTable.generic_by_id[genetic_table_number])).count('*')
        df.loc[df.id == id, 'orf2_codon_stop_nb'] = orf2_nb_codon_stop
        #
        #
        sequence_orf3 = sequence[orf_frame_index + 1:] # get 2nd orf sequence
        sequence_orf3 = sequence_orf3[0:len(sequence_orf3) - (len(sequence_orf3) % 3)] # trimming for module 3
        orf3_nb_codon_stop = str(Seq(sequence_orf3, IUPAC.unambiguous_dna).translate(
            Bio.Data.CodonTable.generic_by_id[genetic_table_number])).count('*')
        df.loc[df.id == id, 'orf3_codon_stop_nb'] = orf3_nb_codon_stop
        # if min_nb_codon_stop =0 so the variant is OK
        minimum = min(orf1_nb_codon_stop, orf2_nb_codon_stop, orf3_nb_codon_stop)
        if (minimum == 0) :
           df.loc[df.id == id,'min_nb_codon_stop'] = 0

    #
    #list of variant id that are Not OK
    list_variant_not_ok = df.id[df['min_nb_codon_stop'] == 1].tolist()
    df2.loc[df2.variant_id.isin(list_variant_not_ok),'filter_delete'] = 1

    return df2