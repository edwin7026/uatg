import ruamel
from ruamel.yaml import YAML
import os
from getpass import getuser
from datetime import datetime
from yapsy.PluginManager import PluginManager


def yapsy_test(yaml_dict, test_file_dir="bpu/"):
    """specify the location where the python test files are located for a
    particular module with the folder following / , Then load the plugins from
    the plugin directory and create the asm test files in a new directory.
    eg. module_class  = branch_predictor's object
        test_file_dir = bpu/
    """

    manager = PluginManager()
    manager.setPluginPlaces([test_file_dir])
    manager.collectPlugins()
    os.makedirs(test_file_dir + "tests/", exist_ok = True)
    # Loop around and find the plugins and writes the contents from the plugins into an asm file
    for plugin in manager.getAllPlugins():
        name = (str(plugin.plugin_object).split(".", 1))
        test_code = plugin.plugin_object.generate_asm(yaml_dict)
        if test_code is not None:
            f = open('bpu/tests/' + ((name[1].split(" ", 1))[0]) + '.S', "w")
            asm = asm_header + test_code + asm_footer
            f.write(asm)
            f.close()
        else:
            pass


def create_plugins(work_dir):
    files = os.listdir(work_dir)
    for i in files:
        if (('.py' in i) and (not i.startswith('.'))):
            module_name = i[0:-3]
            f = open(work_dir + '/' + module_name + '.yapsy-plugin', "w")
            f.write("[Core]\nName=" + module_name + "\nModule=" + module_name)
            f.close()


def load_yaml(foo):
    yaml = YAML(typ="rt")
    yaml.default_flow_style = False
    yaml.allow_unicode = True
    try:
        with open(foo, "r") as file:
            return yaml.load(file)
    except ruamel.yaml.constructor.DuplicateKeyError as msg:
        print("error")


def main():
    inp = "../target/default.yaml"  # yaml file containing the configuration details
    inp_yaml = load_yaml(inp)

    isa = inp_yaml['ISA']

    bpu = inp_yaml['branch_predictor']

    username = getuser()
    time = ((str(datetime.now())).split("."))[0]

    global asm_header
    global asm_footer

    asm_header = "## Licensing information can be found at LICENSE.incore \n" \
                 + "## Test generated by user - " + str(
        username) + " at " + time + "\n"

    asm_header = asm_header + "\n#include \"model_test.h\"\n#include \"arch_test.h\"\n" \
                 + "RVTEST_ISA(\"" + isa + "\")\n\n" + ".section .text.init" \
                 + "\n.globl rvtest_entry_point\nrvtest_entry_point:\n" \
                 + "RVMODEL_BOOT\nRVTEST_CODE_BEGIN\n\n"

    asm_footer = "\nRVTEST_CODE_END\nRVMODEL_HALT\n\nRVTEST_DATA_BEGIN" \
                 + "\n.align 4\nrvtest_data:\n.word 0xbabecafe\nRVTEST_DATA_END\n" \
                 + "\nRVMODEL_DATA_BEGIN\nRVMODEL_DATA_END\n"

    create_plugins('bpu/')
    yapsy_test(yaml_dict=bpu, test_file_dir="bpu/")
    cwd = os.getcwd()

    ## add the path to the river_core to a file named 'path.txt' within the framework
    ## the first line will be used as the path to river_core
    fi = open("path.txt", "r")
    river_path = (fi.readline()).strip('\n')
    fi.close()

    os.chdir(river_path)  # change dir to river_core
    os.system("river_core compile -t mywork/test_list.yaml")
    # run tests in river_core
    os.chdir(cwd)  # get back to present dir
    os.system("python log_parser.py")  # parse the logs and check for matching


if __name__ == "__main__":
    main()
