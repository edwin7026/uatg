import ruamel
from ruamel.yaml import YAML
import os
from shutil import rmtree
from getpass import getuser
from datetime import datetime
from yapsy.PluginManager import PluginManager
from uarch_test.log import logger
from uarch_test.__init__ import __version__


def load_yaml(foo):
    yaml = YAML(typ="rt")
    yaml.default_flow_style = False
    yaml.allow_unicode = True
    try:
        with open(foo, "r") as file:
            return yaml.load(file)
    except ruamel.yaml.constructor.DuplicateKeyError as msg:
        logger.error('error: {0}'.format(msg))


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
        _name = (str(plugin.plugin_object).split(".", 1))
        _test_name = ((_name[1].split(" ", 1))[0])
        if _check:
            _asm_body = plugin.plugin_object.generate_asm()
            _asm = asm_header + _asm_body + asm_footer
            os.mkdir('tests/bpu/tests/' + _test_name)
            with open('tests/bpu/tests/' + _test_name + '/' + _test_name + '.S',
                      "w") as f:
                f.write(_asm)
        else:
            logger.critical('Skipped {0}'.format(_test_name))


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
            _data += "  include: [" + _current_dir + "env/ , " + \
                     _current_dir + "target/" + "]\n"
            _data += "  linker_args: -static -nostdlib -nostartfiles" \
                     " -lm -lgcc -T\n"
            _data += "  linker_file: " + _current_dir + "target/link.ld\n"
            _data += "  mabi: lp64\n"
            _data += "  march: rv64imafdc\n"
            _data += "  isa: rv64imafdc\n"
            _data += "  result: Unknown\n"
            _data += "  work_dir: " + _path_to_tests + "\n\n"
            _generated_tests = _generated_tests + 1
        else:
            logger.critical(
                'No test generated for {0}, skipping it in test_list'.format(
                    _name))

    with open(_path + 'test_list.yaml', 'w') as outfile:
        outfile.write(_data)
    return _generated_tests


def validate_tests(yaml_dict, test_file_dir="bpu/", clean=False):
    manager = PluginManager()
    manager.setPluginPlaces([test_file_dir])
    manager.collectPlugins()
    _pass_ct = 0
    _fail_ct = 0
    _tot_ct = 1
    print("\n")
    for plugin in manager.getAllPlugins():
        _name = (str(plugin.plugin_object).split(".", 1))
        _test_name = ((_name[1].split(" ", 1))[0])
        _check = plugin.plugin_object.execute(yaml_dict)
        if _check:
            _result = plugin.plugin_object.check_log(
                log_file_path=test_file_dir + 'tests/' + _test_name + '/log')
            if _result:
                logger.info('{0}. Minimal test: {1} has passed.'.format(
                    _tot_ct, _test_name))
                _pass_ct += 1
                _tot_ct += 1
            else:
                logger.critical('{0}. Minimal test: {1} has failed.'.format(
                    _tot_ct, _test_name))
                _fail_ct += 1
                _tot_ct += 1
        else:
            logger.warn('No asm generated for {0}. Skipping'.format(_test_name))

    print('\n\n')
    logger.info("Minimal Verification Results")
    logger.info("=" * 28)
    logger.info("Total Tests : {0}".format(_tot_ct - 1))

    if _tot_ct - 1:
        logger.info("Tests Passed : {0} - [{1} %]".format(
            _pass_ct, 100 * _pass_ct // (_tot_ct - 1)))
        logger.warn("Tests Failed : {0} - [{1} %]".format(
            _fail_ct, 100 * _fail_ct // (_tot_ct - 1)))
    else:
        logger.warn("No tests were created")

    if clean:
        files = os.listdir(test_file_dir)
        plugins = [file for file in files if file.endswith(".yapsy-plugin")]
        for file in plugins:
            path_to_file = os.path.join(test_file_dir, file)
            os.remove(path_to_file)
        logger.info("Plugins Cleaned")
        for i in os.listdir(test_file_dir + "__pycache__"):
            os.remove(os.path.join(test_file_dir + "__pycache__", i))
        os.rmdir(test_file_dir + "__pycache__")

        logger.info("Python files Cleaned")


def generate_sv(yaml_dict, test_file_dir="bpu/"):
    """specify the location where the python test files are located for a
    particular module with the folder following / , Then load the plugins from
    the plugin directory and create the covergroups (System Verilog) for the test files in a new directory.
    test_file_dir = bpu/
    """

    manager = PluginManager()
    manager.setPluginPlaces([test_file_dir])
    manager.collectPlugins()

    # Loop around and find the plugins and writes the contents from the
    # plugins into a System Verilog file
    _sv = ""
    for plugin in manager.getAllPlugins():
        _check = plugin.plugin_object.execute(yaml_dict)
        _name = (str(plugin.plugin_object).split(".", 1))
        _test_name = ((_name[1].split(" ", 1))[0])
        if _check:
            try:
                #_sv += _sv
                _sv = plugin.plugin_object.generate_covergroups()
                logger.warn('Generating cvg {0}'.format(_test_name))
                with open('tests/bpu/tests/covergroup.sv', "a") as f:
                    logger.info('Generating for {0}'.format(_test_name))
                    f.write(_sv)

                # To-Do -> Check what the name of the SV file should be
                # To-Do -> Include the creation of TbTop and Interface SV files
                
            except AttributeError:
                logger.warn('Skipping {0}'.format(_test_name))
                pass

        else:
            logger.critical('Skipped {0}'.format(_test_name))
    # to do -> dump interface along with covergroups

def main():

    logger.level('debug')
    logger.info('****** Micro Architectural Tests *******')
    logger.info('Version : {0}'.format(__version__))
    logger.info('Copyright (c) 2021, InCore Semiconductors Pvt. Ltd.')
    logger.info('All Rights Reserved.')
    logger.info('****** Generating Tests ******')

    inp = "target/dut_config.yaml"  # yaml file with configuration details
    inp_yaml = load_yaml(inp)

    global asm_header
    global asm_footer

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

    create_plugins(plugins_path='tests/bpu/')
    generate_tests(yaml_dict=bpu, test_file_dir="tests/bpu/")
    logger.warn("Yaml was not created, and the tests were not validated")
    generate_sv(yaml_dict=bpu, test_file_dir="tests/bpu/")

    #if generate_yaml(yaml_dict=bpu, work_dir="tests/bpu/"):
    #    logger.info('Generated test_list.yaml')
    #else:
    #    logger.warn('No tests were created, test_list.yaml not generated')
    #validate_tests(yaml_dict=bpu, test_file_dir='tests/bpu/', clean=True)


if __name__ == "__main__":
    main()
