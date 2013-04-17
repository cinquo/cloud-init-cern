# vim: ts=4 expandtab
import base64
import cloudinit.util as util
import cloudinit.CloudConfig as cc
import os
import subprocess


__author__ = "Marek Denis <marek.denis@cern.ch>"
__version__ = 0.2


## CONTANTS ##

MODULE_NAME = 'glidein'

class PATHS(object):
    runtime_directory='/tmp/glidein_runtime'
    default_config_directory='/etc/glideinwms'
    default_config_filename='glidein-pilot.ini'
    default_config_file = ''.join([default_config_directory,'/',default_config_filename])
    glidein_userdata_file='glidein_userdata' # file with options for glidein, used internally
    global_userdata_file='user-data' # global file that glidein will eat


class SECTIONS(object):
    vm_properties = 'vm_properties'
    proxy = 'proxy'
    glidein_startup= 'glidein_startup'
    additional_args = 'additional_args'

class PARAMETERS(object):
    """
    Class used for managing all the parameters,
    parsed from default file, dynamic user-data or 
    default, hardcoded value.
    """
    param_default_max_lifetime = 'default_max_lifetime'
    param_disable_shutdown = 'disable_shutdown'
    param_contextualize_protocol = 'contextualize_protocol'
    param_ec2_url = 'ec2_url'
    param_user_name = 'user_name'
    param_user_home = 'user_home'
    param_user_ids  = 'user_ids'
    param_args = 'args'
    param_webbase ='webbase'
    param_proxy_file_name = 'proxy_file_name'
    param_proxy ='proxy'
    param_environment = 'environment'

    def __init__(self):
        self.data = dict()

    def key_value_parameter(self,attribute,join_character='='):
        return join_character.join([attribute,str(self.__getattr__(attribute))])

    def parse(self,cfg):
        """
        1) Setup default values
        2) Add/override values from the /etc/glideinwms/pilot.ini file
        """

        self.__setup_default_values__()
        self.__open_and_parse_etc_config__(PATHS.default_config_file)

    def update(self,values):
        """Adds values to the class-wide dictionary with the parameters"""
        if isinstance(values,dict):
            self.data.update(values)
        else:
            raise ValueError("values argument must be a dictionary")

    def setup_env_variables_str(self):
        envvars = self.data.get(PARAMETERS.param_environment,"")
        return '\n'.join(envvars.split())

    def __open_and_parse_etc_config__(self,filename):
        """
        Handle opening the default configuration file,
        and run parsing method
        """
        try:
            with open(filename,'r') as fh:
                self.__parse_etc_config__(fh)
        except IOError:
            pass # no such file, I guess? 

    def __parse_etc_config__(self,config):
        """
        The config should be iterable,
        a file object is fine as well
        """
        for line in config:
            line = line.strip()

            if line == '[GRID_ENV]':
                self.data[PARAMETERS.param_environment] = self.__parse_env__(config)

            if line.startswith('[') or line.startswith('#') or line == '':
                continue

            key,value = line.split('=',2)
            self.data[key] = value

    def __parse_env__(self,config):
        environment = []
        for line in config:
            line = line.strip()
            if line.startswith('['):
                break
            if line.startswith('#') or line == '':
                continue
            environment.append(line)
        else:
            return ' '.join(environment)
        

    def __setup_default_values__(self):
        """Setup hardcoded values"""
        if self.data:
            return
        self.data[PARAMETERS.param_default_max_lifetime] = 86400# 1 day
        self.data[PARAMETERS.param_disable_shutdown] = False
        self.data[PARAMETERS.param_contextualize_protocol] = 'EC2'
        self.data[PARAMETERS.param_ec2_url] = ''.join([PATHS.runtime_directory,'/',PATHS.global_userdata_file])
        self.data[PARAMETERS.param_user_name] = 'glidein'
        self.data[PARAMETERS.param_user_home] = '/scratch/glidein'
        self.data[PARAMETERS.param_user_ids]  = '509.509'
        self.data[PARAMETERS.param_proxy_file_name] = 'proxy'

    def __getattr__(self,attribute):
        """If parameter was not found, return empty String"""
        result = None
        try:
            if attribute == PARAMETERS.param_ec2_url:
                result = ''.join([PATHS.runtime_directory,'/',PATHS.global_userdata_file])
            else:
                result = self.data[attribute]
        except (KeyError,AttributeError):
            result = ""
        finally:
            return result

class MSG(object):
    cannotuse = "Cannot find section %s, will use default values"
    emptyfile = "This file should include proxy key, however it was not set in the contextualization data"
    fatal = "Unhandled exception was caught: %s"
    cannot_base64 = "Cannot decode base64 encoded file, got exception: %s"


def handle(_name, cfg, cloud, log, _args):
   """A replacement cloud-init module for running glidein-bootstrap"""
   
   log.info("Starting...")
   if MODULE_NAME not in cfg:
       log.warn("%s not in the user-data, exiting.." % MODULE_NAME)
       return

   glidein_cfg = cfg[MODULE_NAME]
   parameters = PARAMETERS()
   parameters.parse(glidein_cfg)

   ##### VM-PROPERTIES #####
   vm_properties_cfg = None
   try:
       vm_properties_cfg = glidein_cfg[SECTIONS.vm_properties]
       parameters.update(vm_properties_cfg)
   except KeyError:
       log.warn(MSG.cannotuse % SECTIONS.vm_properties)
       vm_properties_cfg = dict()
   except Exception,e:
       log.error(MSG.fatal % e)
   
   # ensure the directory exists, add an exception? 
   if not os.path.exists(PATHS.default_config_directory):
       os.makedirs(PATHS.default_config_directory)

   glidein_config_file = dict()

   # configurable values from the [DEFAULTS] section
   default_max_lifetime = parameters.key_value_parameter(PARAMETERS.param_default_max_lifetime)
   contextualize_protocol = parameters.key_value_parameter(PARAMETERS.param_contextualize_protocol)
   disable_shutdown = parameters.key_value_parameter(PARAMETERS.param_disable_shutdown)
   ec2_url = parameters.key_value_parameter(PARAMETERS.param_ec2_url)

   glidein_config_file['[DEFAULTS]'] = [default_max_lifetime,contextualize_protocol,disable_shutdown,ec2_url]

   # configure values from the [GRID_ENV] section
   environment = ''
   try:
       environment = parameters.setup_env_variables_str()
   except KeyError:
       pass
   except Exception,e:
       log.warn(MSG.fatal % PARAMETERS.environment)

   glidein_config_file['[GRID_ENV]'] = [environment]
   
   # default [GLIDEIN_USER] section
   user_name = parameters.key_value_parameter(PARAMETERS.param_user_name)
   user_home = parameters.key_value_parameter(PARAMETERS.param_user_home)
   user_ids = parameters.key_value_parameter(PARAMETERS.param_user_ids)

   glidein_config_file['[GLIDEIN_USER]'] = [user_name,user_home,user_ids]

   with open(PATHS.default_config_file,"w") as fh:
       for k,v in glidein_config_file.iteritems():
           fh.write(k + '\n')
           fh.write('\n'.join(v))
           fh.write('\n')

   ###### GLIDEIN_USERDATA  ######
   
   if not os.path.exists(PATHS.runtime_directory):
       os.makedirs(PATHS.runtime_directory)

   glidein_startup_cfg = None
   try:
       glidein_startup_cfg = glidein_cfg[SECTIONS.glidein_startup]
       parameters.update(glidein_startup_cfg)
   except KeyError:
       log.warn(MSG.cannotuse % SECTIONS.glidein_startup)
       glidein_startup_cfg = dict()
       
   args = parameters.key_value_parameter(PARAMETERS.param_args)
   proxy_file_name = parameters.key_value_parameter(PARAMETERS.param_proxy_file_name)
   webbase = parameters.key_value_parameter(PARAMETERS.param_webbase)

   content = '\n'.join([args,proxy_file_name,webbase])
   with open(PATHS.runtime_directory+'/'+PATHS.glidein_userdata_file,'w') as fh:
       fh.write("[glidein_startup]\n")
       fh.write(content)
   
   ###### PROXY FILE ######

   proxy = None
   try:
       proxy = glidein_cfg[SECTIONS.proxy]
       parameters.update({PARAMETERS.param_proxy:proxy})
   except KeyError:
       log.warn(MSG.cannotuse % SECTIONS.proxy)
       proxy = base64.b64encode(MSG.emptyfile)
   except Exception,e:
       log.warn(MSG.fatal % e)

   proxy_file = None
   try:
       proxy_file = base64.b64decode(proxy) ## we must decode it
   except TypeError,e:
       log.warn(MSG.cannot_base64 % e)
       proxy_file = MSG.emptyfile

   proxy_file_path = parameters.key_value_parameter(PARAMETERS.param_proxy_file_name)
   with open(PATHS.runtime_directory+'/'+proxy_file_path,'w') as fh:
       fh.write(proxy_file)

   #make a tarball and base64 encode it
   #since Python natively doesn't support tar we must use /bin/tar
   pipe = subprocess.Popen(['/bin/tar', 'czf', '-', proxy_file_path, PATHS.glidein_userdata_file],stdout=subprocess.PIPE,cwd=PATHS.runtime_directory)
   tar_data,_ = pipe.communicate()
   tar_encoded = str(base64.b64encode(tar_data))

   ##### ADDITIONAL ARGUMENTS #####
   additional_args = ''
   try:
       additional_args = str(glidein_cfg[SECTIONS.additional_args])
   except KeyError:
       log.warn(MSG.cannotuse % SECTIONS.additional_args)

   # glidein will eventually eat this file
   with open(PATHS.runtime_directory+'/'+ PATHS.global_userdata_file,'w') as fh:
       fh.write(''.join([tar_encoded,'####',additional_args]))

   log.info("done.")
