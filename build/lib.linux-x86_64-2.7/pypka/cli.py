import argparse
import os
import config
import log
from formats import read_pdb_line


def drange(dmin, dmax, step):
    """Decimal Range

    Requires:
      dmin (float or int) is the range minimum value
      dmax (float or int) is the range maximum value
      step (float or int) is the range step value

    Ensures:
      lrange (list)

    Example:
      drange(5, 7.5, 0.5)
        -> [5.0, 5.5, 6.0, 6.5, 7.0, 7.5]

    """
    lrange = []
    dmin, dmax = float(dmin), float(dmax)
    step = float(step)
    inv_step = step ** -1
    dmin_int = int(int(dmin) * inv_step)
    dmax_int = int(int(dmax) * inv_step) + 1
    for i in range(dmin_int, dmax_int):
        lrange.append(i / inv_step)
    return lrange


def setParameter(param, value):
    if param in config.input_conversion.keys():
        param = config.input_conversion[param]
    config.params[param] = value


def getParameter(param):
    if param in config.input_conversion.keys():
        param = config.input_conversion[param]
    return config.params[param]


def inputParametersFilter(settings):
    """
    Check if input parameters are valid

    Mandatory Parameters:
      - Dielectric Constant
      - Ionic Strength
      - Temperature
      - Percentege of grid filling
      - pH range
      - sites_A

    """
    config.pid = os.getpid()
    config.script_dir = os.path.dirname(__file__)
    param_names = settings.keys()
    # MANDATORY #
    mandatory_params = ('input_pdb', 'epsin', 'ionicstr',
                        'pbc_dimensions', 'temp', 'grid_fill',
                        'ncpus', 'pH', 'sites_A')
    for param in mandatory_params:        
        if param not in param_names:
            log.requiredParameterError(param)
        if type(settings[param]) in (float, int):
            settings[param] = str(settings[param])
        if len(settings[param]) == 0:
            log.requiredParameterError(param)

    # Check parameter conditions: parameter is integer
    integer_params = ('gsizeP', 'gsizeM', 'seed', 'ncpus')
    for param in integer_params:
        if param in param_names:
            try:
                param_value = int(settings[param])                
            except:
                log.inputVariableError(param,
                                       'an integer.', '')
            setParameter(param, param_value)

    # Check parameter conditions: parameter is float
    float_params = ('scaleP', 'scaleM', 'ionicstr', 'convergence', 'nlit',
                    'nonit', 'relfac', 'relpar', 'pHstep', 'epssol',
                    'temp', 'epsin', 'slice', 'cutoff')
    for param in float_params:
        if param in param_names:
            try:
                param_value = float(settings[param])            
            except:
                log.inputVariableError(param,
                                       'a float.', '')
            setParameter(param, param_value)

    # Check parameter conditions: parameter > 0
    # These parameters have already been checked for type int or float
    great_params = ('scaleP', 'scaleM', 'convergence', 'pHstep', 'gsizeP',
                    'gsizeM', 'ncpus', 'temp', 'grid_fill', 'pH_step')
    for param in great_params:
        if param in param_names:
            try:
                param_value = getParameter(param)
                assert param_value > 0
            except:
                log.inputVariableError(param,
                                       'greater than zero.', '')
            setParameter(param, param_value)

    # Check parameters conditions: parameter is boolean
    bool_params = ('pbx', 'pby', 'clean_pdb')
    for param in bool_params:
        if param in param_names:
            param_value = settings[param]
            if param_value == 'yes':
                param_value = True
            elif param_value == 'no':
                param_value = False
            else:
                log.inputVariableError(param,
                                       'either "yes" or "no".', '')

            setParameter(param, param_value)


    # Check particular parameter conditions
    if 'bndcon' in param_names and \
       settings['bndcon'] not in ('1', '2', '3', '4'):

        log.inputVariableError('bndcon',
                               '1 (zero), 2(dipolar),'
                               ' 3(focusing) or 4 (coulombic).', '')
        setParameter('bndcon', settings['bndcon'])

    if 'precision' in param_names and \
       settings['precision'] not in ('single', 'double'):

        log.inputVariableError('precision',
                               'either "single" or "double".', '')
        setParameter('precision', settings['precision'])

    if 'ffID' in param_names and \
       settings['ffID'] not in ('G54A7'):  # for now only GROMOS FF
        log.inputVariableError('ffID',
                               'equal to "G54A7".', '')
        setParameter('ffID', settings['ffID'])

    file_path = os.path.join(config.script_dir, config.params['ffID'])
    config.f_crg = '{0}/DataBaseT.crg'.format(file_path)
    config.f_siz = '{0}/DataBaseT.siz'.format(file_path)

    if settings['pbc_dimensions'] not in ('0', '2'):
        log.inputVariableError('pbc_dimensions',
                               'either "0" or "2".', '')
    else:
        param_value = int(settings['pbc_dimensions'])
        setParameter('pbc_dimensions', param_value)

    # Needs to accept both a single value and a range
    pH_parts = settings['pH'].split('-')
    if len(pH_parts) > 1:
        try:
            setParameter('pHmin', float(pH_parts[0]))
            setParameter('pHmax', float(pH_parts[1]))
        except:
            log.inputVariableError('pH',
                                   'a float.', '')            
    else:
        try:
            setParameter('pHmin', float(pH_parts[0]))
            setParameter('pHmax', float(pH_parts[0]))
        except:
            log.inputVariableError('pH',
                                   'a float.', '')
        setParameter('pH', [param_value])

    # Declare IO Files
    # Input .pdb File
    config.f_pdb = settings['input_pdb']

    # Output pKs File
    if 'output' in param_names:
        config.f_out = settings['output']
    else:
        outputname = settings['input_pdb'].split('.')[0]
        config.f_out = outputname

    # Output Titration File
    if 'titration_output' in param_names:
        config.f_prot_out = settings['titration_output']

    # Output log File
    if 'logfile' in param_names:
        config.f_log = settings['logfile']  # default: "LOG"

    # Check coherence between variables
    if getParameter('pbc_dim') == 2 and \
       getParameter('relfac') != 0.2 and 'relfac' not in settings:
        setParameter('relfac', 0.2)

    for i in settings['lipid_definition']:
        resname = settings['lipid_definition'][i]
        config.lipids[i] = resname
        if resname in config.lipid_residues:
            resname_i = config.lipid_residues.index(resname)
            del config.lipid_residues[resname_i]
    return


def readSettings(filename):
    """Reads the settings file.

    This file should have the following format:
     - commented lines should being with a '#'
     - every parameter should be declared as such: name = value

    All parameter values are interpreted as strings, however, a type
    check is later performed for each declared input value.

    All parameter names not recognizable are reported as a warning.
    """
    parameters = {}
    parameters['lipid_definition'] = {}
    with open(filename) as f:
        nline = 0
        for line in f:
            nline += 1
            if len(line.strip()) > 0 and line[0] != '#':
                parts = line.split('=')
                param_name = parts[0].strip()
                param_value = '='.join(parts[1:]).strip()
                if 'lipid_definition' in param_name:
                    parts = param_value.split(':')
                    old_name = parts[0]
                    new_name = parts[1]
                    parameters['lipid_definition'][old_name] = new_name
                elif len(parts) != 2 or \
                   not len(param_name) > 0 or \
                   not len(param_value) > 0:
                    raise IOError('Incorrect format in line {0} of file {1}: '
                                  '\n{1}#{0}: {2}'.format(nline, filename, line))
                else:
                    parameters[param_name] = param_value

    # Search for all titrable sites in different chains
    sites = {}
    for param_name in parameters:
        if 'site' in param_name:
            chain = param_name.split('_')[1]
            chain_sites = parameters[param_name].split(', ')
            if chain_sites != ['all']:
                sites[chain] = chain_sites
    config.sites = sites

    return parameters


def checkParsedInput():
    """Gets the CLI arguments and interprets them"""

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter, description="""
Object-Oriented Script to Calculate the pKint of each site \
as well as the pairwise energies
Requires:
DelPhi2Py module installation
Nanoshaper and cppSolver are optional libraries

Objects:
DelPhiParams stores the DelPhi input parameters like a .prm file

TitratingMolecule is the molecule which has more than one Site

Site

Tautomer

Example:
python pypka.py test.pdb test.dat -o pKas.out --debug

    """)

    # Mandatory Arguments
    parser.add_argument('settings', help=' settings file name',
                        default="settings.dat", action='store')

    # Optional Arguments
    parser.add_argument('--debug', help='activation of the debug mode '
                        'to print extra information', action='store_true')

    args = parser.parse_args()

    # Apply some criteria to input arguments
    if not os.path.isfile(args.settings):
        wrongType('settings', 'correctly assigned',
                      'File {0} does not exist.'.format(args.settings))

    # Read Settings File
    config.f_dat = args.settings
    config.debug = args.debug
    parameters = readSettings(args.settings)

    return parameters