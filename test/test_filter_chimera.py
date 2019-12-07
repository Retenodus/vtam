import multiprocessing
import pathlib
from unittest import TestCase
from vtam.utils.PathManager import PathManager
from vtam.utils.FilterChimeraRunner import FilterChimeraRunner
import os
import pandas

class TestFilterChimera(TestCase):


    def setUp(self):
        """>parent1;size=650
TGTTCTTTATTTATTATTTGCTGGTTTTGCTGGTGTTTTAGCTGTAACTTTATCATTATTAATTAGATTACAATTAGTTGCTACTGGGTATGGATGATTAGCTTTGAATTATCAATTTTATAACACTATTGTAACTGCTCATGGATTATTAATAGTATTTTTTCTCCTTATGCCTGCTTTAATAGGTGGTTTTGGTAATTGAATAGTTCCTGTTCTAATTGGTTCTATTGATATGGCTTACCCTAGATTAAATAATATTAGTTTTTGATTATTGCCCCCTAGTTTATTATAATTAGTTGG
>parent2;size=700
AACTATGTACACAAATTTTAGTATATTGGCAGGGATAGTAGGAACTTTACTATCGTTAGTTATCAGAATGGAATTATCAA
CAGGAAACATGTTAGATGGAGACGGTCAACAATATAACGTAATCGTAACCGCACATGGATTAATAATGATATTCTTCGTGGTTATGCCGGCAATGTTAGGAGGATTTGCAAACTGGTTCATACCAATAATGGTAGGATCACCAGATGTAGCTTTTCCAAGATTAAACAACATTAGCTTATGGTTAATATTATTGCCCCCTAGTTTATTATTATTAGTTGG
>Chimera1;size=50
TGTTCTTTATTTATTATTTGCTGGTTTTGCTGGTGTTTTAGCTGTAACTTTATCATTATTAATTAGATTACAATTAGTTGCTACTGGGTATGGATGATTAGCTTTGAATTATCAATTTTATAACACTATTGTAACTGCTCATGGATTATTATTCTTCGTGGTTATGCCGGCAATGTTAGGAGGATTTGCAAACTGGTTCATACCAATAATGGTAGGATCACCAGATGTAGCTTTTCCAAGATTAAACAACATTAGCTTATGGTTAATATTATTGCCCCCTAGTTTATTATTATTAGTTGG
>Chimera2;size=300
TGTTCTTTATTTATTATTTGCTGGTTTTGCTGGTGTTTTAGCTGTAACTTTATCATTATTAATTAGATTACAATTAGTTG
CAGGAAACATGTTAGATGGAGACGGTCAACAATATAACGTAATCGTAACCGCACATGGATTAATAATGATATTCTTCGTGGTTATGCCGGCAATGTTAGGAGGATTTGCAAACTGGTTCATACCAATAATGGTAGGATCACCAGATGTAGCTTTTCCAAGATTAAACAACATTAGCTTATGGTTAATATTATTGCCCCCTAGTTTATTATTATTAGTTGG
>Chimera3;size=50
TGTTCTTTATTTATTATTTGCTGGTTTTGCTGGTGTTTTAGCTGTAACTTTATCATTATTAATTAGATTACAATTAGTTGCTACTGGGTATGGATGATTAGCTTTGAATTATCAATTTTATAACACTATTGTAACTGCTCATGGATTATTAATAGTATTTTTTCTCCTTATGCCTGCTTTAATAGGTGGTTTTGGTAATTGAATAGTTCCTGTTCTAATTGGTTCTATTGATATGGCTTACCCTAGATTAAATAATATTAGTTTTTGATTATTGCCCCCTAGTTTATTATTATTAGTTGG"""

        """(vtam_appli) gonzalez@milan:~/tmp/vsearch_uchime$ vsearch --uchime_denovo i.fa --borderline borderline.fa --nonchimeras nonchimeras.fa --chimeras chimeras.fa
vsearch v2.7.0_linux_x86_64, 15.5GB RAM, 8 cores
https://github.com/torognes/vsearch

Reading file i.fa 100%  
1500 nt in 5 seqs, min 300, max 300, avg 300
Masking 100% 
Sorting by abundance 100%
Counting k-mers 100% 
Detecting chimeras 100%  
Found 2 (40.0%) chimeras, 2 (40.0%) non-chimeras,
and 1 (20.0%) borderline sequences in 5 unique sequences.
Taking abundance information into account, this corresponds to
350 (20.0%) chimeras, 1350 (77.1%) non-chimeras,
and 50 (2.9%) borderline sequences in 1750 total sequences"""

        # Input from min_replicate_number
        # Variants 1 and 2 are ok but 3-5 are chimeras
        self.variant_df = pandas.DataFrame(data={
            'sequence': [
                'TGTTCTTTATTTATTATTTGCTGGTTTTGCTGGTGTTTTAGCTGTAACTTTATCATTATTAATTAGATTACAATTAGTTGCTACTGGGTATGGATGATTAGCTTTGAATTATCAATTTTATAACACTATTGTAACTGCTCATGGATTATTAATAGTATTTTTTCTCCTTATGCCTGCTTTAATAGGTGGTTTTGGTAATTGAATAGTTCCTGTTCTAATTGGTTCTATTGATATGGCTTACCCTAGATTAAATAATATTAGTTTTTGATTATTGCCCCCTAGTTTATTATAATTAGTTGG',
                'AACTATGTACACAAATTTTAGTATATTGGCAGGGATAGTAGGAACTTTACTATCGTTAGTTATCAGAATGGAATTATCAACAGGAAACATGTTAGATGGAGACGGTCAACAATATAACGTAATCGTAACCGCACATGGATTAATAATGATATTCTTCGTGGTTATGCCGGCAATGTTAGGAGGATTTGCAAACTGGTTCATACCAATAATGGTAGGATCACCAGATGTAGCTTTTCCAAGATTAAACAACATTAGCTTATGGTTAATATTATTGCCCCCTAGTTTATTATTATTAGTTGG',
                'TGTTCTTTATTTATTATTTGCTGGTTTTGCTGGTGTTTTAGCTGTAACTTTATCATTATTAATTAGATTACAATTAGTTGCTACTGGGTATGGATGATTAGCTTTGAATTATCAATTTTATAACACTATTGTAACTGCTCATGGATTATTATTCTTCGTGGTTATGCCGGCAATGTTAGGAGGATTTGCAAACTGGTTCATACCAATAATGGTAGGATCACCAGATGTAGCTTTTCCAAGATTAAACAACATTAGCTTATGGTTAATATTATTGCCCCCTAGTTTATTATTATTAGTTGG',
                'TGTTCTTTATTTATTATTTGCTGGTTTTGCTGGTGTTTTAGCTGTAACTTTATCATTATTAATTAGATTACAATTAGTTGCAGGAAACATGTTAGATGGAGACGGTCAACAATATAACGTAATCGTAACCGCACATGGATTAATAATGATATTCTTCGTGGTTATGCCGGCAATGTTAGGAGGATTTGCAAACTGGTTCATACCAATAATGGTAGGATCACCAGATGTAGCTTTTCCAAGATTAAACAACATTAGCTTATGGTTAATATTATTGCCCCCTAGTTTATTATTATTAGTTGG',
                'TGTTCTTTATTTATTATTTGCTGGTTTTGCTGGTGTTTTAGCTGTAACTTTATCATTATTAATTAGATTACAATTAGTTGCTACTGGGTATGGATGATTAGCTTTGAATTATCAATTTTATAACACTATTGTAACTGCTCATGGATTATTAATAGTATTTTTTCTCCTTATGCCTGCTTTAATAGGTGGTTTTGGTAATTGAATAGTTCCTGTTCTAATTGGTTCTATTGATATGGCTTACCCTAGATTAAATAATATTAGTTTTTGATTATTGCCCCCTAGTTTATTATTATTAGTTGG',

                         ],
        }, index=list(range(1,6)),)
        #
        self.variant_read_count_df = pandas.DataFrame({
            'run_id': [1] * 5,
            'marker_id': [1] * 5,
            'biosample_id': [1] * 5,
            'replicate_id': [1] * 5,
            'variant_id': list(range(1,6)),
            'read_count':[650, 700, 50, 350, 50],
        })
        self.this_tempdir = os.path.join(PathManager.instance().get_tempdir(), os.path.basename(__file__))
        pathlib.Path(self.this_tempdir).mkdir(parents=True, exist_ok=True)
        os.environ['VTAM_THREADS'] = str(multiprocessing.cpu_count())

    def test_filter_chimera_runner(self):
        filter_chimera_runner = FilterChimeraRunner(variant_df=self.variant_df, variant_read_count_df=self.variant_read_count_df)
        filter_output_df, filter_borderline_output_df = filter_chimera_runner.run(tmp_dir=self.this_tempdir)

        filter_output_df_bak_str = """   run_id  marker_id  biosample_id  replicate_id  variant_id  read_count  filter_delete
0       1          1             1             1           1         650          False
1       1          1             1             1           2         700          False
2       1          1             1             1           3          50           True
3       1          1             1             1           4         350          False
4       1          1             1             1           5          50          False"""
        self.assertTrue(filter_output_df_bak_str==filter_output_df.to_string())

        filter_output_df_bak_str = """   run_id  marker_id  biosample_id  replicate_id  variant_id  read_count  filter_delete
0       1          1             1             1           1         650          False
1       1          1             1             1           2         700          False
2       1          1             1             1           3          50          False
3       1          1             1             1           4         350          False
4       1          1             1             1           5          50           True"""
        self.assertTrue(filter_output_df_bak_str==filter_borderline_output_df.to_string())
