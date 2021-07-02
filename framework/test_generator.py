import ruamel
from ruamel.yaml import YAML
import os
from shutil import rmtree
from getpass import getuser
from datetime import datetime
from yapsy.PluginManager import PluginManager
from termcolor import colored


def load_yaml(foo):
    yaml = YAML(typ="rt")
    yaml.default_flow_style = False
    yaml.allow_unicode = True
    try:
        with open(foo, "r") as file:
            return yaml.load(file)
    except ruamel.yaml.constructor.DuplicateKeyError as msg:
        print("error: ", msg)


def create_plugins(plugins_path):
    files = os.listdir(plugins_path)
    for i in files:
        if ('.py' in i) and (not i.startswith('.')):
            module_name = i[0:-3]
            f = open(plugins_path + '/' + module_name + '.yapsy-plugin', "w")
            f.write("[Core]\nName=" + module_name + "\nModule=" + module_name)
            f.close()


def generate_tests(yaml_dict, test_file_dir="bpu/"):
    """specify the location where the python test files are located for a
    particular module with the folder following / , Then load the plugins from
    the plugin directory and create the asm test files in a new directory.
    eg. module_class  = branch_predictor's object
        test_file_dir = bpu/
    """

    manager = PluginManager()
    manager.setPluginPlaces([test_file_dir])
    manager.collectPlugins()

    # To-Do : find a way to send yaml_dict to the class.

    dir_path = os.path.join(test_file_dir, 'tests')
    if (os.path.isdir(dir_path)) and os.path.exists(dir_path):
        rmtree(test_file_dir + "tests/")

    os.mkdir(test_file_dir + "tests/")
    # Loop around and find the plugins and writes the contents from the
    # plugins into an asm file
    for plugin in manager.getAllPlugins():
        _check = plugin.plugin_object.execute(yaml_dict)
        if _check:
            asm_body = plugin.plugin_object.generate_asm()
            name = (str(plugin.plugin_object).split(".", 1))
            test_name = ((name[1].split(" ", 1))[0])
            os.mkdir('bpu/tests/' + test_name)
            f = open('bpu/tests/' + test_name + '/' + test_name + '.S', "w")
            asm = asm_header + asm_body + asm_footer
            f.write(asm)
            f.close()
        else:
            print("skipped ",
                  (((str(plugin.plugin_object).split(".", 1))[1]).split(" ",
                                                                        1))[0])


def validate_tests(yaml_dict, test_file_dir="bpu/"):
    manager = PluginManager()
    manager.setPluginPlaces([test_file_dir])
    manager.collectPlugins()
    _pass_ct = 0
    _fail_ct = 0
    _tot_ct = 1
    print("\n\n\n")
    for plugin in manager.getAllPlugins():
        _name = (str(plugin.plugin_object).split(".", 1))
        _test_name = ((_name[1].split(" ", 1))[0])
        _check = plugin.plugin_object.execute(yaml_dict)
        if _check:
            _result = plugin.plugin_object.check_log(
                log_file_path=test_file_dir + 'tests/' + _test_name + '/log')
            if _result:
                print(
                    colored(
                        str(_tot_ct) + ".\tMinimal test:" + _test_name +
                        " has passed", 'green'))
                _pass_ct += 1
                _tot_ct += 1
            else:
                print(
                    colored(
                        str(_tot_ct) + ".\tMinimal test:" + _test_name +
                        " has failed", 'red'))
                _fail_ct += 1
                _tot_ct += 1
        else:
            print(
                colored(".\tNo asm generated for " + _test_name + ". Skipping",
                        'white'))

    print("\n\nMinimal Verification Results\n" + "=" * 28)
    print("Total Tests : ", _tot_ct - 1)

    if _tot_ct - 1:
        print(
            colored(
                "Tests Passed : {} - [{} %]".format(
                    _pass_ct, 100 * _pass_ct // (_tot_ct - 1)), 'green'))
        print(
            colored(
                "Tests Failed : {} - [{} %]".format(
                    _fail_ct, 100 * _fail_ct // (_tot_ct - 1)), 'red'))
    else:
        print(colored("No tests were created", 'yellow'))


def generate_yaml(yaml_dict, work_dir="bpu/"):
    """
      updates the test_list.yaml file of rivercore with the location of the 
      tests generated by test_generator as well the directory to dump the logs
    """

    manager = PluginManager()
    manager.setPluginPlaces([work_dir])
    manager.collectPlugins()

    _path = river_path + "/mywork/"
    _data = ""
    _generated_tests = 0

    # To-Do -> Create Yaml the proper way. Do not use strings!!

    for plugin in manager.getAllPlugins():
        _check = plugin.plugin_object.execute(yaml_dict)
        _name = (((str(plugin.plugin_object).split(".", 1))[1]).split(" ",
                                                                      1))[0]
        _current_dir = os.getcwd() + '/'
        _path_to_tests = _current_dir + work_dir + 'tests/' + _name + '/'
        if _check:
            _data += _name + ":\n"
            _data += "  asm_file: " + _path_to_tests + _name + ".S\n"
            _data += "  cc: riscv64-unknown-elf-gcc\n"
            _data += "  cc_args: \' -mcmodel=medany -static -std=gnu99 -O2 " \
                     "-fno-common -fno-builtin-printf -fvisibility=hidden \'\n"
            _data += "  compile_macros: [XLEN=64]\n"
            _data += "  extra_compile: []\n"
            _data += "  generator: micro_arch_test_v0.0.1\n"
            _data += "  include: [" + _current_dir + "../env/ , " + \
                     _current_dir + "../target/" + "]\n"
            _data += "  linker_args: -static -nostdlib -nostartfiles" \
                     "-lm -lgcc -T\n"
            _data += "  linker_file: " + _current_dir + "../target/link.ld\n"
            _data += "  mabi: lp64\n"
            _data += "  march: rv64imafdc\n"
            _data += "  isa: rv64imafdc\n"
            _data += "  result: Unknown\n"
            _data += "  work_dir: " + _path_to_tests + "\n\n"
            _generated_tests = _generated_tests + 1
        else:
            print('No test generated for ' + _name +
                  ', skipping it in test_list')

    with open(_path + 'test_list.yaml', 'w') as outfile:
        outfile.write(_data)
    return _generated_tests


def main():
    global asm_header
    global asm_footer
    global river_path

    inp = "../target/dut_config.yaml"  # yaml file with configuration details
    inp_yaml = load_yaml(inp)

    # first line in path should be river cores's directory
    fi = open("path.txt", "r")
    river_path = (fi.readline()).strip('\n')
    fi.close()

    isa = inp_yaml['ISA']
    bpu = inp_yaml['branch_predictor']

    username = getuser()
    time = ((str(datetime.now())).split("."))[0]

    asm_header = "## Licensing information can be found at LICENSE.incore \n" \
                 + "## Test generated by user - " + str(username) + " at " \
                 + time + "\n"
    asm_header += "\n#include \"model_test.h\"\n#include \"arch_" \
                  + "test.h\"\nRVTEST_ISA(\"" + isa + "\")\n\n" \
                  + ".section .text.init\n.globl rvtest_entry_point" \
                  + "\nrvtest_entry_point:\nRVMODEL_BOOT\n" \
                  + "RVTEST_CODE_BEGIN\n\n"
    asm_footer = "\nRVTEST_CODE_END\nRVMODEL_HALT\n\nRVTEST_DATA_BEGIN" \
                 + "\n.align 4\nrvtest_data:\n.word 0xbabecafe\n" \
                 + "RVTEST_DATA_END\n\nRVMODEL_DATA_BEGIN\nRVMODEL_DATA_END\n"

    create_plugins(plugins_path='bpu/')
    generate_tests(yaml_dict=bpu, test_file_dir="bpu/")
    generated = generate_yaml(yaml_dict=bpu, work_dir="bpu/")
    if generated:
        print(colored("Invoking RiVer core", 'yellow'))
        cwd = os.getcwd()
        os.chdir(river_path)  # change dir to river_core
        os.system("river_core compile -t mywork/test_list.yaml")
        # run tests in river_core
        os.chdir(cwd)  # get back to present dir
    else:
        print(
            colored("No tests were created, not invoking RiVer Core", 'yellow'))
    validate_tests(yaml_dict=bpu, test_file_dir='bpu/')


if __name__ == "__main__":
    main()
