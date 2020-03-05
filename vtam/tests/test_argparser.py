# -*- coding: utf-8 -*-
import os
import shutil

from pathlib import Path
from unittest import TestCase
from vtam.utils.ArgParser import ArgParser
from vtam.utils.PathManager import PathManager


class TestArgParser(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.parser = ArgParser.get_main_arg_parser()

        foopaths = {}
        foopaths['filedoesnotexist'] = "filedoesnotexist"
        foopaths['dirdoesnotexist'] = "dirdoesnotexist"
        foopaths['fileisempty'] = os.path.relpath("../test_files/emptyfile", PathManager.get_package_path())
        foopaths['filenottsv'] = os.path.relpath(__file__, PathManager.get_package_path())
        foopaths['readinfo_tsv'] = os.path.relpath(os.path.join(PathManager.get_test_path(), "test_files",
                                                                "readinfo.tsv"), PathManager.get_package_path())
        foopaths['foodir'] = os.path.relpath(os.path.dirname(__file__), PathManager.get_package_path())
        foopaths['outdir'] = os.path.relpath(os.path.join(PathManager.get_test_path(),
                                                                             'output'), PathManager.get_package_path())
        foopaths['emptydir'] = os.path.relpath(os.path.join(foopaths['outdir'], 'emptydir'),
                                               PathManager.get_package_path())
        Path(os.path.join(foopaths['emptydir'])).mkdir(parents=True, exist_ok=True)
        foopaths['blastdb'] = os.path.relpath(os.path.join(PathManager.get_test_path(), 'test_files', 'blastdb'),
                                              PathManager.get_package_path())
        cls.foopaths = foopaths

    def test_arg_parser_filter(self):

        # Ok
        args = "filter --readinfo {readinfo_tsv} --readdir {foodir} --outdir {foodir}".format(**self.foopaths).split()
        self.assertTrue(self.parser.parse_args(args), 0)

        ################################################################################################################
        #
        # raises SystemExit
        #
        ################################################################################################################

        args = ["filter"]
        with self.assertRaises(SystemExit):
            self.parser.parse_args(args)

        args = "filter --readinfo {filedoesnotexist} --readdir {foodir} --outdir {foodir}".format(**self.foopaths).split()
        with self.assertRaises(SystemExit):
            self.parser.parse_args(args)

        args = "filter --readinfo {filenottsv} --readdir {foodir} --outdir {foodir}".format(**self.foopaths).split()
        with self.assertRaises(SystemExit):
            self.parser.parse_args(args)

        args = "filter --readinfo {readinfo_tsv} --readdir {emptydir} --outdir {foodir}".format(**self.foopaths).split()
        with self.assertRaises(SystemExit):
            self.parser.parse_args(args)

        args = "filter --readinfo {readinfo_tsv} --readdir {dirdoesnotexist} --outdir {foodir}".format(**self.foopaths).split()
        with self.assertRaises(SystemExit):
            self.parser.parse_args(args)

    def tearDown(self):
        shutil.rmtree(self.foopaths['outdir'], ignore_errors=True)