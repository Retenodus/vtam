import os
import pathlib
import shlex
import shutil
import subprocess
import sys
import tarfile
import unittest
import urllib.request

from vtam.utils import pip_install_vtam_for_tests
from vtam.utils.PathManager import PathManager
from vtam.utils.constants import sorted_tar_bz2_url
# from vtam.utils.MyProgressBar import MyProgressBar
from tqdm import tqdm
from vtam.utils import tqdm_hook


class TestCmdVariantReadCount(unittest.TestCase):

    """Will test main commands based on a complete test dataset"""

    @classmethod
    def setUpClass(cls):

        ########################################################################
        #
        # These tests need the vtam command in the path
        #
        ########################################################################

        pip_install_vtam_for_tests()

        cls.package_path = os.path.join(PathManager.get_package_path())
        cls.test_path = os.path.join(PathManager.get_test_path())
        cls.outdir_path = os.path.join(cls.test_path, 'outdir')
        cls.outdir_data_path = os.path.join(cls.outdir_path, 'data')
        shutil.rmtree(cls.outdir_path, ignore_errors=True)
        pathlib.Path(cls.outdir_data_path).mkdir(parents=True, exist_ok=True)

        ############################################################################################
        #
        # Download sorted reads dataset (Updated Mar 2022)
        #
        ############################################################################################

        sorted_tar_path = os.path.join(cls.outdir_data_path, "sorted.tar.bz2")
        # Test first in local dir, otherwise in the remote URLs
        if not os.path.isfile(sorted_tar_path) or pathlib.Path(sorted_tar_path).stat().st_size < 1000000:
            try:
                # urllib.request.urlretrieve(sorted_tar_gz_url1, sorted_tar_path, MyProgressBar())
                with tqdm(...) as t:
                    t.set_description(os.path.basename(sorted_tar_path))
                    urllib.request.urlretrieve(sorted_tar_bz2_url, sorted_tar_path, reporthook=tqdm_hook(t))
            except Exception as e:
                print(f"Could not download {sorted_tar_bz2_url}:\n {e} ")
                return

        tar = tarfile.open(sorted_tar_path, "r:gz")
        tar.extractall(path=cls.outdir_data_path)
        tar.close()

    def setUp(self):
        self.outdir_thistest_path = os.path.join(self.outdir_path, 'thistest')
        # during development of the test, this prevents errors
        pathlib.Path(self.outdir_thistest_path).mkdir(parents=True, exist_ok=True)
        os.environ['VTAM_LOG_VERBOSITY'] = str(10)

        ############################################################################################
        #
        # Fails
        #
        ############################################################################################

        self.asvtable_path = os.path.join(self.outdir_path, "asvtable_default.tsv")

        self.args = {}
        self.args['sortedinfo'] = os.path.join(os.path.dirname(__file__), "sortedinfo_bz2.tsv")
        self.args['sorteddir'] = os.path.join(self.outdir_data_path, 'sorted_bz2')
        self.args['optimize_lfn_variant_specific'] = os.path.join(
            self.test_path, "test_files_dryad.f40v5_small/run1_mfzr_zfzr/optimize_lfn_variant_specific.tsv")
        self.args['optimize_lfn_variant_replicate_specific'] = os.path.join(
            self.test_path, "test_files_dryad.f40v5_small/run1_mfzr_zfzr/optimize_lfn_variant_replicate_specific.tsv")
        self.args['params_lfn_variant'] = os.path.join(os.path.dirname(__file__), "params_lfn_variant.yml")
        self.args['params_lfn_variant_replicate'] = os.path.join(os.path.dirname(__file__), "params_lfn_variant_replicate.yml")

    def test_lfn_variant_replicate_cutoff_specific_fail1(self):

        ############################################################################################
        #
        # Fails
        #
        ############################################################################################

        cmd = "vtam filter --db db.sqlite --sortedinfo {sortedinfo} --sorteddir {sorteddir} " \
              "--asvtable asvtable_default.tsv  --until VariantReadCount " \
              "--lfn_variant_replicate --cutoff_specific {optimize_lfn_variant_specific}".format(**self.args)

        if sys.platform.startswith("win"):
            args = cmd
        else:
            args = shlex.split(cmd)
        result = subprocess.run(args=args, cwd=self.outdir_thistest_path)

        self.assertEqual(result.returncode, 1)

    def test_lfn_variant_replicate_cutoff_specific_fail2(self):

        ############################################################################################
        #
        # Wrong
        #
        ############################################################################################

        cmd = "vtam filter --db db.sqlite --sortedinfo {sortedinfo} --sorteddir {sorteddir} " \
              "--asvtable asvtable_default.tsv  --until VariantReadCount " \
              "--cutoff_specific {optimize_lfn_variant_replicate_specific}".format(**self.args)

        if sys.platform.startswith("win"):
            args = cmd
        else:
            args = shlex.split(cmd)
        result = subprocess.run(args=args, cwd=self.outdir_thistest_path)

        self.assertEqual(result.returncode, 1)

    def test_lfn_variant_replicate_cutoff_specific_succeeds1(self):

        ############################################################################################
        #
        # Succeeds
        #
        ############################################################################################

        cmd = "vtam filter --db db.sqlite --sortedinfo {sortedinfo} --sorteddir {sorteddir} " \
              "--asvtable asvtable_default.tsv --until VariantReadCount " \
              "--lfn_variant_replicate --cutoff_specific {optimize_lfn_variant_replicate_specific}".format(**self.args)

        if sys.platform.startswith("win"):
            args = cmd
        else:
            args = shlex.split(cmd)

        result = subprocess.run(args=args, cwd=self.outdir_thistest_path)
        self.assertEqual(result.returncode, 0)

    def test_lfn_variant_replicate_cutoff_specific_succeeds2(self):

        ############################################################################################
        #
        # Succeeds
        #
        ############################################################################################

        cmd = "vtam filter --db db.sqlite --sortedinfo {sortedinfo} --sorteddir {sorteddir} " \
              "--asvtable asvtable_default.tsv --until VariantReadCount " \
              "--cutoff_specific {optimize_lfn_variant_specific}".format(**self.args)

        if sys.platform.startswith("win"):
            args = cmd
        else:
            args = shlex.split(cmd)

        result = subprocess.run(args=args, cwd=self.outdir_thistest_path)

        self.assertEqual(result.returncode, 0)

    def test_read_fasta(self):
        cmd = "vtam filter --db db.sqlite --sortedinfo {sortedinfo} --sorteddir {sorteddir} " \
              "--asvtable asvtable_default.tsv --until VariantReadCount " \
              "--cutoff_specific {optimize_lfn_variant_specific}".format(**self.args)

        if sys.platform.startswith("win"):
            args = cmd
        else:
            args = shlex.split(cmd)

        result = subprocess.run(args=args, cwd=self.outdir_thistest_path)

        self.assertEqual(result.returncode, 0)

    def tearDown(self):

        shutil.rmtree(self.outdir_thistest_path, ignore_errors=True)

    @classmethod
    def tearDownClass(cls):

        shutil.rmtree(cls.outdir_path, ignore_errors=True)
