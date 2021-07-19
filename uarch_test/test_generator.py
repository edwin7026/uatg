import os
import glob
from shutil import rmtree
from getpass import getuser
from datetime import datetime
import ruamel.yaml as yaml
import uarch_test
from uarch_test.utils import load_yaml, create_plugins, create_linker, create_model_test_h, generate_test_list
from yapsy.PluginManager import PluginManager
from uarch_test.log import logger
from uarch_test.__init__ import __version__
'''
File directories naming convention:
    uarch_dir = 'modules/'                 uarch_test/modules/
    module_dir = uarch_dir + module + '/'  uarch_test/modules/branch_predictor/ 
'''


def generate_tests(work_dir,
                   linker_dir,
                   modules,
                   inp,
                   test_list,
                   verbose='debug'):
    """
    specify the location where the python test files are located for a
    particular module with the folder following / , Then load the plugins from
    the plugin directory and create the asm test files in a new directory.
    eg. module_class  = branch_predictor's object
    """
    uarch_dir = os.path.dirname(uarch_test.__file__)

    if work_dir:
        pass
    else:
        work_dir = os.path.abspath((os.path.join(uarch_dir, '../work/')))

    os.makedirs(work_dir, exist_ok=True)

    logger.level(verbose)
    logger.info('****** Micro Architectural Tests *******')
    logger.info('Version : {0}'.format(__version__))
    logger.info('Copyright (c) 2021, InCore Semiconductors Pvt. Ltd.')
    logger.info('All Rights Reserved.')
    logger.info('****** Generating Tests and CoverPoints******')
    if (test_list):
        logger.info(
            'Test List will be generated by uarch_test. You can find it in the work dir'
        )
    else:
        logger.info('Test list will not be generated by uarch_test')
    logger.info('uArch_test dir is {0}'.format(uarch_dir))
    logger.info('work_dir is {0}'.format(work_dir))

    inp_yaml = load_yaml(inp)
    isa = inp_yaml['ISA']

    if (modules == ['all']):
        logger.debug('Checking {0} for modules'.format(
            os.path.join(uarch_dir, 'modules')))
        modules = [
            f.name
            for f in os.scandir(os.path.join(uarch_dir, 'modules'))
            if f.is_dir()
        ]
    logger.debug('The modules are {0}'.format(modules))

    test_list_dict = {}

    for module in modules:
        module_dir = os.path.join(uarch_dir, 'modules', module)
        work_tests_dir = os.path.join(work_dir, module)
        print(work_tests_dir)

        module_params = inp_yaml[module]

        logger.debug('Directory for {0} is {1}'.format(module, module_dir))

        logger.info('Starting plugin Creation for {0}'.format(module))

        create_plugins(plugins_path=module_dir)

        logger.info('Created plugins for {0}'.format(module))

        username = getuser()
        time = ((str(datetime.now())).split("."))[0]

        asm_header = '## Licensing information can be found at LICENSE.incore ' \
                     '\n## Test generated by user - {0} at {1}\n\n#include ' \
                     '\"model_test.h\" \n#include \"arch_test.h\" \nRVTEST_ISA(' \
                     '\"{2}\")\n\n.section .text.init\n.globl ' \
                     'rvtest_entry_point\nrvtest_entry_point:\nRVMODEL_BOOT' \
                     '\nRVTEST_CODE_BEGIN\n\n'.format(str(username), time, isa)

        asm_footer = '\nRVTEST_CODE_END\nRVMODEL_HALT\n\nRVTEST_DATA_BEGIN\n' \
                     '.align 4\nrvtest_data:\n.word ' \
                     '0xbabecafe\nRVTEST_DATA_END\n\nRVMODEL_DATA_BEGIN' \
                     '\nRVMODEL_DATA_END\n '

        manager = PluginManager()
        manager.setPluginPlaces([module_dir
                                ])  # plugins are stored in module_dir
        manager.collectPlugins()

        # check if prior test files are present and remove them. create new dir.
        if (os.path.isdir(work_tests_dir)) and \
                os.path.exists(work_tests_dir):
            rmtree(work_tests_dir)
        os.mkdir(work_tests_dir)

        logger.debug('Generating assembly tests for {0}'.format(module))

        # Loop around and find the plugins and writes the contents from the
        # plugins into an asm file
        for plugin in manager.getAllPlugins():
            _check = plugin.plugin_object.execute(module_params)
            _name = (str(plugin.plugin_object).split(".", 1))
            _test_name = ((_name[1].split(" ", 1))[0])
            if _check:
                _asm_body = plugin.plugin_object.generate_asm()
                _asm = asm_header + _asm_body + asm_footer
                os.mkdir(os.path.join(work_tests_dir, _test_name))
                with open(
                        os.path.join(work_tests_dir, _test_name,
                                     _test_name + '.S'), "w") as f:
                    f.write(_asm)
                logger.debug('Generating test for {0}'.format(_test_name))
            else:
                logger.critical('Skipped {0}'.format(_test_name))
        logger.debug(
            'Finished Generating Assembly Tests for {0}'.format(module))
        logger.debug('Generating CoverPoints for {0}'.format(module))
        generate_sv(module=module,
                    module_params=module_params,
                    work_dir=work_dir,
                    verbose=verbose)
        logger.debug('Finished Generating Coverpoints for {0}'.format(module))
        if (test_list):
            logger.info('Creating test_list for the {0}'.format(module))
            test_list_dict.update(
                generate_test_list(work_tests_dir, uarch_dir, test_list_dict))

    logger.info('****** Finished Generating Tests and CoverPoints ******')

    if (linker_dir) and os.path.isfile(os.path.join(linker_dir, 'link.ld')):
        logger.debug('Using user specified linker')
    else:
        create_linker(target_dir=work_dir)
        logger.debug('Creating a linker file at {0}'.format(work_dir))

    if (linker_dir) and os.path.isfile(os.path.join(linker_dir,
                                                    'model_test.h')):
        logger.debug('Using user specified model_test file')
    else:
        create_model_test_h(target_dir=work_dir)
        logger.debug('Creating Model_test.h file at {0}'.format(work_dir))

    if (test_list):
        with open(work_dir + '/' + 'test_list.yaml', 'w') as outfile:
            yaml.dump(test_list_dict, outfile)


def generate_sv(module, work_dir, module_params, verbose='debug'):
    """specify the location where the python test files are located for a
    particular module with the folder following / , Then load the plugins from
    the plugin directory and create the covergroups (System Verilog) for the test files in a new directory.
    """
    logger.level(verbose)
    uarch_dir = os.path.dirname(uarch_test.__file__)

    module_dir = os.path.join(uarch_dir, 'modules', module)
    work_tests_dir = os.path.join(work_dir, module)

    manager = PluginManager()
    manager.setPluginPlaces([module_dir])
    manager.collectPlugins()

    for plugin in manager.getAllPlugins():
        _check = plugin.plugin_object.execute(module_params)
        _name = (str(plugin.plugin_object).split(".", 1))
        _test_name = ((_name[1].split(" ", 1))[0])
        if _check:
            try:
                _sv = plugin.plugin_object.generate_covergroups()
                # TODO: Check what the name of the SV file should be
                # TODO: Include the creation of TbTop and Interface SV files
                with open(os.path.join(work_tests_dir + 'coverpoints.sv'),
                          "a") as f:
                    logger.info('Generating coverpoints SV file for {0}'.format(
                        _test_name))
                    f.write(_sv)

            except AttributeError:
                logger.warn(
                    'Skipping coverpoint generation for {0} as there is no gen_covergroup method'
                    .format(_test_name))
                pass

        else:
            logger.critical(
                'Skipped {0} as this test is not created for the current DUT configuration'
                .format(_test_name))


def validate_tests(modules, inp, work_dir, verbose='debug'):
    """
       Parses the log returned from the DUT for finding if the tests were successful
    """

    logger.level(verbose)
    uarch_dir = os.path.dirname(uarch_test.__file__)
    inp_yaml = load_yaml(inp)
    logger.info('****** Validating Test results, Minimal log checking ******')

    if (modules == ['all']):
        logger.debug('Checking {0} for modules'.format(
            os.path.join(uarch_dir, 'modules')))
        modules = [
            f.name
            for f in os.scandir(os.path.join(uarch_dir, 'modules'))
            if f.is_dir()
        ]
    if work_dir:
        pass
    else:
        work_dir = os.path.abspath((os.path.join(uarch_dir, '../work/')))

    _pass_ct = 0
    _fail_ct = 0
    _tot_ct = 1

    for module in modules:
        module_dir = os.path.join(uarch_dir, 'modules', module)
        module_tests_dir = os.path.join(module_dir, 'tests')
        work_tests_dir = os.path.join(work_dir, module)

        module_params = inp_yaml[module]

        manager = PluginManager()
        manager.setPluginPlaces([module_dir])
        manager.collectPlugins()

        logger.debug('Minimal Log Checking for {0}'.format(module))

        for plugin in manager.getAllPlugins():
            _name = (str(plugin.plugin_object).split(".", 1))
            _test_name = ((_name[1].split(" ", 1))[0])
            _check = plugin.plugin_object.execute(module_params)
            if _check:
                _result = plugin.plugin_object.check_log(
                    log_file_path=os.path.join(work_tests_dir, _test_name,
                                               'log'))
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
                logger.warn(
                    'No asm generated for {0}. Skipping'.format(_test_name))
        logger.debug('Minimal log Checking for {0} complete'.format(module))

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

    logger.info('****** Finished Validating Test results ******')


def clean_dirs(work_dir, verbose='debug'):
    """
    This function cleans unwanted files. Presently it removes __pycache__,
    tests/ directory inside modules and yapsy plugins.
    """
    logger.level(verbose)
    uarch_dir = os.path.dirname(uarch_test.__file__)
    if work_dir:
        pass
    else:
        work_dir = os.path.abspath((os.path.join(uarch_dir, '../work/')))

    module_dir = os.path.join(work_dir, '**')
    #module_tests_dir = os.path.join(module_dir, 'tests')

    logger.info('****** Cleaning ******')
    yapsy_dir = os.path.join(module_dir, '*.yapsy-plugin')
    pycache_dir = os.path.join(module_dir, '__pycache__')

    tf = glob.glob(module_dir)
    pf = glob.glob(pycache_dir) + glob.glob(
        os.path.join(uarch_dir, '__pycache__'))
    yf = glob.glob(yapsy_dir)
    for i in tf + pf:
        if (os.path.isdir(i)):
            rmtree(i)
        else:
            os.remove(i)

    for i in yf:
        os.remove(i)
    logger.info("Generated Test files/folders removed")
