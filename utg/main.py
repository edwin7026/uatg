# See LICENSE.incore for details
"""Console script for utg."""

import click
from configparser import ConfigParser
from utg.log import logger
from utg.test_generator import generate_tests, clean_dirs, validate_tests, \
    generate_sv
from utg.__init__ import __version__
from utg.utils import list_of_modules, info, load_yaml, clean_modules
from utg.utils import create_dut_config, create_config_file, create_alias_file


@click.group()
@click.version_option(version=__version__)
def cli():
    """RISC-V Micro-Architectural Test Generator"""


# -----------------


@click.version_option(version=__version__)
@click.option('--module_dir',
              '-md',
              multiple=False,
              required=False,
              type=click.Path(exists=True, resolve_path=True, readable=True),
              help="Absolute Path to the directory containing the python files"
              " which generates the assembly tests. "
              "Required Parameter")
@click.option('--work_dir',
              '-wd',
              multiple=False,
              required=True,
              type=click.Path(exists=True, resolve_path=True, readable=True),
              help="Path to the working directory where generated files will be"
              " stored.")
@click.option('--verbose',
              '-v',
              default='info',
              help='Set verbose level for debugging',
              type=click.Choice(['info', 'error', 'debug'],
                                case_sensitive=False))
@cli.command()
def clean(module_dir, work_dir, verbose):
    """
    Removes ASM, SV and other generated files from the work directory, and
    removes .yapsy plugins from module directory.\n
    Requires: -wd, --work_dir\n
    Optional: -md, --module_dir; -v, --verbose
    """
    logger.level(verbose)
    info(__version__)
    logger.debug('Invoking clean_dirs')
    clean_dirs(work_dir=work_dir, modules_dir=module_dir, verbose=verbose)


# -------------------------


@click.version_option(version=__version__)
@click.option('--alias_file',
              '-af',
              multiple=False,
              required=False,
              type=click.Path(exists=True, resolve_path=True, readable=True),
              help="Path to the aliasing file containing containing BSV alias "
              "names.")
@click.option('--dut_config',
              '-dc',
              multiple=False,
              required=True,
              type=click.Path(exists=True, resolve_path=True, readable=True),
              help="Path to the yaml file containing DUT configuration. "
              "Needed to generate/validate tests")
@click.option('--module_dir',
              '-md',
              multiple=False,
              required=True,
              type=click.Path(exists=True, resolve_path=True, readable=True),
              help="Absolute Path to the directory containing the python files"
              " which generates the assembly tests. "
              "Required Parameter")
@click.option('--gen_cvg',
              '-gc',
              is_flag=True,
              required=False,
              help='Set this flag to generate the Covergroups')
@click.option(
    '--gen_test_list',
    '-t',
    is_flag=True,
    required=False,
    help='Set this flag if a test-list.yaml is to be generated by utg. '
    'utg does not generate the test_list by default.')
@click.option('--linker_dir',
              '-ld',
              multiple=False,
              required=False,
              type=click.Path(exists=True, resolve_path=True, readable=True),
              help="Path to the directory containing the linker file."
              "Work Directory is Chosen for linker if this argument is empty")
@click.option('--work_dir',
              '-wd',
              multiple=False,
              required=True,
              type=click.Path(exists=True, resolve_path=True, readable=True),
              help="Path to the working directory where generated files will be"
              " stored.")
@click.option('--modules',
              '-m',
              default='all',
              multiple=False,
              is_flag=False,
              help="Enter a list of modules as a string in a comma separated "
              "format.\ndefault-all",
              type=str)
@click.option('--verbose',
              '-v',
              default='info',
              help='Set verbose level for debugging',
              type=click.Choice(['info', 'error', 'debug'],
                                case_sensitive=False))
@cli.command()
def generate(alias_file, dut_config, linker_dir, module_dir, gen_cvg,
             gen_test_list, work_dir, modules, verbose):
    """
    Generates tests, cover-groups for a list of modules corresponding to the DUT
    defined in dut_config inside the work_dir. Can also generate the test_list
    needed to execute them on RiverCore.\n
    Requires: -dc, --dut_config, -md, --module_dir; -wd, --work_dir\n
    Depends : (-gc, --gen_cvg -> -af, --alias_file)\n
    Optional: -gc, --gen_cvg; -t, --gen_test_list; -ld, --linker_dir;\n
              -m, --modules; -v, --verbose
    """

    logger.level(verbose)
    info(__version__)

    dut_dict = load_yaml(dut_config)

    module = clean_modules(module_dir, modules, verbose)

    generate_tests(work_dir=work_dir,
                   linker_dir=linker_dir,
                   modules_dir=module_dir,
                   modules=module,
                   config_dict=dut_dict,
                   test_list=gen_test_list,
                   verbose=verbose)
    if gen_cvg:
        if alias_file is not None:
            alias_dict = load_yaml(alias_file)
            generate_sv(work_dir=work_dir,
                        config_dict=dut_dict,
                        modules_dir=module_dir,
                        modules=module,
                        alias_dict=alias_dict,
                        verbose=verbose)
        else:
            logger.error('Can not generate covergroups without alias_file.')
            exit('GEN_CVG WITHOUT ALIAS_FILE')


# -------------------------


@click.version_option(version=__version__)
@click.option('--verbose',
              '-v',
              default='info',
              help='Set verbose level for debugging',
              type=click.Choice(['info', 'error', 'debug'],
                                case_sensitive=False))
@click.option('--module_dir',
              '-md',
              multiple=False,
              required=True,
              type=click.Path(exists=True, resolve_path=True, readable=True),
              help="Absolute Path to the directory containing the python files"
              " which generates the assembly tests. "
              "Required Parameter")
@cli.command()
def list_modules(module_dir, verbose):
    """
    Provides the list of modules supported from the module_dir\n
    Requires: -md, --module_dir
    """
    module_str = "\nSupported modules:\n"
    for module in (list_of_modules(module_dir, verbose)):
        module_str += '\t' + module + '\n'
    print(f'{module_str}')


# -------------------------


@click.option('--config_file',
              '-c',
              multiple=False,
              required=False,
              type=click.Path(exists=True, resolve_path=True, readable=True),
              help="Provide a config.ini file's path. This runs utg based upon "
              "the parameters stored in the file. If not specified "
              "individual args/flags are to be passed through cli. In the"
              "case of conflict between cli and config.ini values, config"
              ".ini values will be chosen")
@click.option('--verbose',
              '-v',
              default='info',
              help='Set verbose level for debugging',
              type=click.Choice(['info', 'error', 'debug'],
                                case_sensitive=False))
@cli.command()
def from_config(config_file, verbose):
    """
    This subcommand reads parameters from config.ini and runs utg based on the
    values.\n
    Optional: -c, --config
    """

    config = ConfigParser()
    config.read(config_file)

    module_dir = config['utg']['module_dir']
    modules = config['utg']['modules']
    verbosity = config['utg']['verbose']
    
    module = clean_modules(module_dir, modules, verbose=verbose)
    logger.level(verbosity)

    info(__version__)

    if config['utg']['gen_test'].lower() == 'true':
        dut_dict = load_yaml(config['utg']['dut_config'])
        generate_tests(work_dir=config['utg']['work_dir'],
                       linker_dir=config['utg']['linker_dir'],
                       modules_dir=module_dir,
                       modules=module,
                       config_dict=dut_dict,
                       test_list=config['utg']['gen_test_list'],
                       verbose=verbose)
    if config['utg']['gen_cvg'].lower() == 'true':
        dut_dict = load_yaml(config['utg']['dut_config'])
        alias_dict = load_yaml(config['utg']['alias_file'])
        generate_sv(work_dir=config['utg']['work_dir'],
                    modules=module,
                    modules_dir=module_dir,
                    config_dict=dut_dict,
                    alias_dict=alias_dict,
                    verbose=verbose)
    if config['utg']['val_test'].lower() == 'true':
        dut_dict = load_yaml(config['utg']['dut_config'])
        validate_tests(modules=module,
                       work_dir=config['utg']['work_dir'],
                       config_dict=dut_dict,
                       modules_dir=module_dir,
                       verbose=verbose)

    if config['utg']['clean'].lower() == 'true':
        logger.debug('Invoking clean_dirs')
        clean_dirs(work_dir=config['utg']['work_dir'],
                   modules_dir=module_dir,
                   verbose=verbose)


# -------------------------


@click.option('--config_path',
              '-cp',
              multiple=False,
              required=False,
              type=click.Path(exists=True, resolve_path=True, readable=True),
              help="Directory to store the config.ini file")
@click.option('--alias_path',
              '-ap',
              multiple=False,
              required=False,
              type=click.Path(exists=True, resolve_path=True, readable=True),
              help="Directory to store the aliasing.yaml file")
@click.option('--dut_path',
              '-dp',
              multiple=False,
              required=False,
              type=click.Path(exists=True, resolve_path=True, readable=True),
              help="Directory to store the dut_config.yaml file")
@cli.command()
def setup(config_path, alias_path, dut_path):
    """
        Setups template files for config.ini, dut_config.yaml and aliasing.yaml.
        Optionally you can provide the path's for each of them. If not specified
        files will be written to default paths.\n
        Optional: -dp, --dut_path;  -ap, --alias_path; -cp, --config_path
    """
    if config_path is None:
        config_path = './'
    if alias_path is None:
        alias_path = './'
    if dut_path is None:
        dut_path = './'

    create_config_file(config_path=config_path)
    create_dut_config(dut_config_path=dut_path)
    create_alias_file(alias_path=alias_path)

    print(f'Files created')


# -------------------------


@click.version_option(version=__version__)
@click.option('--dut_config',
              '-dc',
              multiple=False,
              required=False,
              type=click.Path(resolve_path=True, readable=True),
              help="Path to the yaml file containing DUT configuration. "
              "Needed to generate/validate tests")
@click.option('--module_dir',
              '-md',
              multiple=False,
              required=False,
              type=click.Path(exists=True, resolve_path=True, readable=True),
              help="Absolute Path to the directory containing the python files"
              " which generate the assembly tests. "
              "Required Parameter")
@click.option('--work_dir',
              '-wd',
              multiple=False,
              required=False,
              type=click.Path(exists=True, resolve_path=True, readable=True),
              help="Path to the working directory where generated files will be"
              " stored.")
@click.option('--modules',
              '-m',
              default='all',
              multiple=False,
              is_flag=False,
              help="Enter a list of modules as a string in a comma separated "
              "format.\ndefault-all",
              type=str)
@click.option('--verbose',
              '-v',
              default='info',
              help='Set verbose level for debugging',
              type=click.Choice(['info', 'error', 'debug'],
                                case_sensitive=False))
@cli.command()
def validate(dut_config, module_dir, work_dir, modules, verbose):
    logger.level(verbose)
    info(__version__)
    dut_yaml = load_yaml(dut_config)

    module = clean_modules(module_dir, modules, verbose)
    validate_tests(modules=module,
                   work_dir=work_dir,
                   config_dict=dut_yaml,
                   modules_dir=module_dir,
                   verbose=verbose)
