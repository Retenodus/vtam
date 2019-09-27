import inspect

import os
import shutil

from wopmars.framework.database.tables.ToolWrapper import ToolWrapper
from wopmars.utils.Logger import Logger
from wopmetabarcoding.utils.PathManager import PathFinder

from wopmetabarcoding.utils.VSearch import VSearch1
from wopmetabarcoding.utils.logger import logger
from wopmetabarcoding.utils.utilities import create_step_tmp_dir
from wopmetabarcoding.wrapper.SortReadsUtilities import \
    create_primer_tag_fasta_for_vsearch, discard_tag_primer_alignment_with_low_sequence_quality,  trim_reads, \
    convert_trimmed_tsv_to_fasta, annotate_reads

class SortReads(ToolWrapper):
    __mapper_args__ = {
        "polymorphic_identity": "wopmetabarcoding.wrapper.SortReads"
    }
    # Input
    # Input table
    __input_table_sample_information = "SampleInformation"
    __input_table_fasta = "Fasta"
    __input_table_marker = "Marker"
    #Input file
    __input_file_sample2fasta = "sample2fasta"
    # Output
    # Output file
    # Output table
    __output_file_sort_reads = 'sortreads'

    def specify_input_table(self):
        return [
            SortReads.__input_table_sample_information,
            SortReads.__input_table_fasta,
            SortReads.__input_table_marker,

        ]

    def specify_input_file(self):
        return[
            SortReads.__input_file_sample2fasta,
        ]

    def specify_output_file(self):
        return [
            SortReads.__output_file_sort_reads,
        ]

    def specify_params(self):
        """

        :return:
        """
        return {
            "min_id": "float",
            "minseqlength": "int",
            "overhang": "int"
        }

    def run(self):
        session = self.session()
        engine = session._WopMarsSession__session.bind
        this_step_tmp_dir = create_step_tmp_dir(__file__)

        ##########################################################
        #
        # Wrapper inputs, outputs and parameters
        #
        ##########################################################
        #
        # Input tables models
        sample_information_model = self.input_table(SortReads.__input_table_sample_information)
        fasta_model = self.input_table(SortReads.__input_table_fasta)
        marker_model = self.input_table(SortReads.__input_table_marker)
        #
        # Output input
        # Output tsv wit fields: read_name, fasta_id, run_id, marker_id, biosample_id, replicate_id
        sort_reads_tsv = self.output_file(SortReads.__output_file_sort_reads)
        #
        # Some variables
        tsv_file_list_with_read_annotations = [] # List of TSV files with read annotations
        # run_list = {}
        primer_tag_fasta = os.path.join(this_step_tmp_dir, 'primer_tag.fasta')
        checked_vsearch_output_tsv = os.path.join(this_step_tmp_dir, 'checked_vsearch_output.tsv')
        #
        marker2fasta2readannotationtsv_dict = {} # Dict of dicts, where for each marker, there are fasta and readannotationtsv
        ############################################
        #
        # For each fasta file path in the DB (Table Fasta)
        #
        # 1. Trimming (Forward and reverse): Remove primer and tag sequence from each read sequence (Each sequence in Fasta)
        # 2. Store read count of each variant in table 'VariantReadCount'
        # 3. Eliminate singleton: Variants found one time throughout all biosample-replicates
        ############################################
        fasta_sort_reads_tsv_list = []
        for fasta_obj in session.query(fasta_model).order_by('name').all():
            fasta_id = fasta_obj.id
            fasta_name = fasta_obj.name
            PathFinder.mkdir_p(os.path.join(this_step_tmp_dir, os.path.basename(fasta_name)))
            # Get marker of this fasta file
            marker_id = session.query(sample_information_model).filter(
                sample_information_model.fasta_id == fasta_id).first().marker_id
            marker_name = session.query(marker_model).filter(
                marker_model.id == marker_id).first().name
            logger.debug(
                "file: {}; line: {}; FASTA {} {}".format(__file__, inspect.currentframe().f_lineno, fasta_id, fasta_name))
            # file_id = fasta_obj.id
            sample_information_obj = session.query(sample_information_model).filter(sample_information_model.fasta_id==fasta_id).all()
            ############################################
            #
            # First (forward) trim: create_primer_tag_fasta_for_vsearch
            #
            # 1. Create fasta file for primer-tag sequences
            # 2. Run vsearch with 'db' parameter: primer_tag_fasta and 'usearch_global' parameter: fasta with the reads
            ############################################
            is_forward_strand = True
            #
            ############################################
            # Vsearch --db primer_tag_fasta --usearch_global merged_fasta
            # Vsearch --db primer_tag_fasta --usearch_global merged_fasta
            ############################################
            logger.debug(
                "file: {}; line: {}; FASTA {} {}; forward {}".format(__file__, inspect.currentframe().f_lineno, fasta_id, fasta_name, is_forward_strand))
            logger.debug(
                "file: {}; line: {}; FASTA {} {}; forward {}; FASTA for forward trimming: {}".format(__file__, inspect.currentframe().f_lineno, fasta_id, fasta_name, is_forward_strand, primer_tag_fasta))
            #
            # This create the primer + tag fasta file
            create_primer_tag_fasta_for_vsearch(sample_information_obj, is_forward_strand, primer_tag_fasta)
            logger.debug(
                "file: {}; line: {}; FASTA {} {}; forward {}; VSearch forward trimming".format(__file__, inspect.currentframe().f_lineno, fasta_id, fasta_name, is_forward_strand))
            vsearch_output_tsv = os.path.join(this_step_tmp_dir, os.path.basename(fasta_name), "vsearch_output_fwd.tsv")
            logger.debug(
                "file: {}; line: {}; FASTA {} {}; forward {}; vsearch_output_tsv: {}".format(__file__,
                        inspect.currentframe().f_lineno, fasta_id, fasta_name, is_forward_strand, vsearch_output_tsv))
            #
            ############################################
            # Run vsearch (Trim)
            # 
            # 1. Define vsearch parameters
            # 2. Run vsearch: output written to 'vsearch_output_tsv'
            ############################################
            vsearch_params = {'db': primer_tag_fasta,
                              'usearch_global': fasta_name,
                              'id': str(self.option("min_id")),
                              'maxhits': 1,
                              'maxrejects': 0,
                              'maxaccepts': 0,
                              'minseqlength': str(self.option("minseqlength")),
                              'userfields': "query+target+tl+qilo+qihi+tilo+tihi+qrow",
                              'userout': vsearch_output_tsv,
                              }
            vsearch1 = VSearch1(**vsearch_params)
            vsearch1.run()
            del vsearch1
            #
            ############################################
            # discard_tag_primer_alignment_with_low_sequence_quality
            ############################################
            logger.debug(
                "file: {}; line: {}; FASTA {} {}; forward {}; Eliminating non SRS conforms reads for forward trimming".format(__file__, inspect.currentframe().f_lineno, fasta_id, fasta_name, is_forward_strand))
            discard_tag_primer_alignment_with_low_sequence_quality(vsearch_output_tsv, checked_vsearch_output_tsv, self.option("overhang"))
            #
            ############################################
            # Trim reads and write to sqlite
            ############################################
            logger.debug(
                "file: {}; line: {}; FASTA {} {}; forward {}; Trimming reads for forward trimming".format(__file__, inspect.currentframe().f_lineno, fasta_id, fasta_name, is_forward_strand))
            trimmed_tsv = os.path.join(this_step_tmp_dir, os.path.basename(fasta_name), 'trimmed_fwd.tsv')
            temp_db_sqlite = os.path.join(this_step_tmp_dir, os.path.basename(fasta_name), 'trimmed_fwd.sqlite')
            logger.debug(
                "file: {}; line: {}; FASTA {} {}; forward {}; Trimming reads for forward trimming: {}".format(__file__, inspect.currentframe().f_lineno, fasta_id, fasta_name, is_forward_strand, temp_db_sqlite))
            trim_reads(checked_vsearch_output_tsv, fasta_name, trimmed_tsv, temp_db_sqlite)
            #
            ############################################
            # convert_trimmed_tsv_to_fasta
            ############################################
            Logger.instance().info("Writing fasta file for forward trimming.")
            trimmed_fasta = os.path.join(this_step_tmp_dir, os.path.basename(fasta_name), 'trimmed_fwd.fasta')
            logger.debug(
                "file: {}; line: {}; FASTA {} {}; forward {}; Writing fasta file for trimming.: {}".format(__file__, inspect.currentframe().f_lineno, fasta_id, fasta_name, is_forward_strand, trimmed_fasta))
            convert_trimmed_tsv_to_fasta(trimmed_tsv, trimmed_fasta)
            #
            ############################################
            #
            # Second (reverse) trim
            #
            ############################################
            #
            is_forward_strand = False
            #
            ############################################
            # Vsearch --db primer_tag_fasta --usearch_global merged_fasta
            ############################################
            logger.debug(
                "file: {}; line: {}; FASTA {} {}; forward {}".format(__file__, inspect.currentframe().f_lineno,
                                                                     fasta_id, fasta_name, is_forward_strand))
            # Logger.instance().info("Creating a fasta query file to align on the merged reads fasta for forward trimming.")
            logger.debug(
                "file: {}; line: {}; FASTA {} {}; forward {}; FASTA for forward trimming: {}".format(__file__,
                                                                                                  inspect.currentframe().f_lineno,
                                                                                                     fasta_id,
                                                                                                     fasta_name,
                                                                                                  is_forward_strand,
                                                                                                  primer_tag_fasta))
            create_primer_tag_fasta_for_vsearch(sample_information_obj, is_forward_strand, primer_tag_fasta)
            # Logger.instance().info("Processing Vsearch for forward trimming.")
            logger.debug(
                "file: {}; line: {}; FASTA {} {}; forward {}; VSearch forward trimming".format(__file__,
                                                                                            inspect.currentframe().f_lineno,
                                                                                               fasta_id, fasta_name,
                                                                                            is_forward_strand))
            #
            # self.vsearch_subprocess(merged_fasta, is_forward_strand, primer_tag_fasta, vsearch_output_tsv)
            vsearch_output_tsv = os.path.join(this_step_tmp_dir, os.path.basename(fasta_name), "vsearch_output_rev.tsv")

            logger.debug(
                "file: {}; line: {}; FASTA {} {}; forward {}; vsearch_output_tsv".format(__file__,
                                                                                      inspect.currentframe().f_lineno,
                                                                                         fasta_id, fasta_name, is_forward_strand))
            vsearch_params = {'db': primer_tag_fasta,
                              'usearch_global': trimmed_fasta,
                              'id': str(self.option("min_id")),
                              'maxhits': 1,
                              'maxrejects': 0,
                              'maxaccepts': 0,
                              'minseqlength': str(self.option("minseqlength")),
                              'userfields': "query+target+tl+qilo+qihi+tilo+tihi+qrow",
                              'userout': vsearch_output_tsv,
                              }
            vsearch1 = VSearch1(**vsearch_params)
            vsearch1.run()
            del vsearch1
            #
            ############################################
            # discard_tag_primer_alignment_with_low_sequence_quality
            ############################################
            logger.debug(
                "file: {}; line: {}; FASTA {} {}; forward {}; Eliminating non SRS conforms reads for forward trimming".format(
                    __file__, inspect.currentframe().f_lineno, fasta_id, fasta_name, is_forward_strand))
            discard_tag_primer_alignment_with_low_sequence_quality(vsearch_output_tsv, checked_vsearch_output_tsv,
                                                                   self.option("overhang"))
            #
            ############################################
            # Trim reads in reverse strand and write to sqlite
            ############################################
            logger.debug(
                "file: {}; line: {}; FASTA {} {}; forward {}; Trimming reads for reverse trimming".format(__file__,
                                                                                                       inspect.currentframe().f_lineno,
                                                                                                          fasta_id,
                                                                                                          fasta_name,
                                                                                                       is_forward_strand))
            trimmed_tsv = os.path.join(this_step_tmp_dir, os.path.basename(fasta_name), 'trimmed_rev.tsv')
            temp_db_sqlite = os.path.join(this_step_tmp_dir, os.path.basename(fasta_name), 'trimmed_rev.sqlite')
            logger.debug(
                "file: {}; line: {}; FASTA {} {}; forward {}; Trimming reads for reverse trimming: {}".format(__file__,
                                                                                                           inspect.currentframe().f_lineno,
                                                                                                              fasta_id,
                                                                                                              fasta_name,
                                                                                                           is_forward_strand,
                                                                                                           temp_db_sqlite))
            trim_reads(checked_vsearch_output_tsv, trimmed_fasta, trimmed_tsv, temp_db_sqlite)
            #
            Logger.instance().info("Annotating reads with Sample Information.")
            # One TSV file with read annotation per merged FASTA Fasta
            read_annotation_tsv = os.path.join(this_step_tmp_dir, os.path.basename(fasta_name), 'read_annotation.tsv')
            tsv_file_list_with_read_annotations.append(read_annotation_tsv)
            # run_list[read_annotation_tsv] = fasta_obj.run_id
            logger.debug(
                "file: {}; line: {}; trimmed_tsv {}".format(__file__, inspect.currentframe().f_lineno, trimmed_tsv))
            ################################################################
            # Count number of times a given variant (Sequence unique) is observed in fasta file
            # In other words, store in 'VariantReadCount' for each 'variant_id' -> 'read count'
            ################################################################
            # marker2fasta2readannotationtsv_dict[marker_name] = {}
            # marker2fasta2readannotationtsv_dict[marker_name][fasta_name] = read_annotation_tsv
            fasta_sort_reads_tsv = os.path.join(this_step_tmp_dir, os.path.basename(fasta_name), 'sortreads.tsv')
            fasta_sort_reads_tsv_list.append(fasta_sort_reads_tsv)
            annotate_reads(session, sample_information_model, trimmed_tsv, fasta_id=fasta_id, out_tsv=fasta_sort_reads_tsv)

        ########################################################
        #
        # Concatenate sortreads files of different fasta files
        #
        ########################################################
        with open(sort_reads_tsv, 'wb') as wfd:
            for f in fasta_sort_reads_tsv_list:
                with open(f, 'rb') as fd:
                    shutil.copyfileobj(fd, wfd)
