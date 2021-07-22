# This program generates a assembly code which fills the ghr with zeros
from yapsy.IPlugin import IPlugin
import regex_formats as rf
import re
from configparser import ConfigParser


class gshare_fa_ghr_zeros_01(IPlugin):

    def __init__(self):
        self.ghr_width = 8
        self._history_len = 8

    def execute(self, _bpu_dict):
        self._history_len = _bpu_dict['history_len']
        self._en_bpu = _bpu_dict['instantiate']

        if self._en_bpu and self._history_len:
            return True
        else:
            return False

    def generate_asm(self):
        """
          the for loop iterates ghr_width + 2 times printing an
          assembly program which contains ghr_width + 2 branches which
          will are *NOT TAKEN*. This fills the ghr with zeros
        """
        loop_count = self._history_len + 2
        asm = "\n\n## test: gshare_fa_ghr_zeros_01 ##\n\n"
        asm += "  addi t0,x0,1\n"

        for i in range(1, loop_count):
            asm = asm + "branch_" + str(i) + ":\n"
            asm = asm + "  beq t0,x0,branch_" + str(i) + "\n"
            asm = asm + "  addi t0,t0,1\n"

        return asm

    def check_log(self, log_file_path):
        """
          check if all the ghr values are zero throughout the test
        """
        f = open(log_file_path, "r")
        log_file = f.read()
        f.close()

        new_ghr_result = re.findall(rf.new_ghr_pattern, log_file)
        for i in new_ghr_result:
            if self.ghr_width * "0" in i:
                pass
            else:
                return False
        return True

    def generate_covergroups(self, config_file):
        """
           returns the covergroups for this test
        """
        config = ConfigParser()
        config.read(config_file)
        rg_ghr = config['bpu']['bpu_rg_ghr']

        sv = """covergroup bpu_rg_ghr_cg; 
option.per_instance=1;
///coverpoint label can be any name that relates the signal
coverpoint_label: coverpoint {0} {{\n""".format(rg_ghr)
        sv = sv + "    bins cp1 = {" + str(self._history_len) + "{1'b0}};\n"
        sv = sv + "    bins cp2 = {" + str(self._history_len) + "{1'b1}};\n"
        sv = sv + "    bins cp3 = {" + str(int(
            self._history_len / 2)) + "{2'b01}};\n"
        sv = sv + "    bins cp4 = {" + str(int(
            self._history_len / 2)) + "{2'b10}};\n}\nendgroup\n\n"


        return (sv)
