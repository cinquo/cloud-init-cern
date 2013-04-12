# vim: ts=4 expandtab
import base64
import cloudinit.util as util
import cloudinit.CloudConfig as cc
import os
import subprocess


__author__ = "Marek Denis <marek.denis@cern.ch>"
__version__ = 0.1


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
    default_max_lifetime = 'default_max_lifetime'
    disable_shutdown = 'disable_shutdown'
    contextualize_protocol = 'contextualize_protocol'
    ec2_url = 'ec2_url'
    user_name = 'user_name'
    user_home = 'user_home'
    user_ids  = 'user_ids'
    args = 'args'
    webbase ='webbase'
    proxy_file_name = 'proxy_file_name'
    proxy ='proxy'
    environment = 'environment'

class GLIDEIN_DEFAULT_VALUES(object):
    # for default configuration file
    default_max_lifetime =  86400 # 1 day
    disable_shutdown = False
    contextualize_protocol = 'EC2'
    ec2_url = PATHS.runtime_directory + '/' + PATHS.global_userdata_file
    user_name = 'glidein'
    user_home = '/scratch/glidein'
    user_ids = '509.509'
    # other
    proxy_file_name = 'proxy'

class MSG(object):
    cannotuse = "Cannot find section %s, will use default values"
    emptyfile = "This file should include proxy key, however it was not set in the contextualization data"
    fatal = "Unhandled exception was caught: %s"
    cannot_base64 = "Cannot decode base64 encoded file, got exception: %s"


def make_key_value(param,dictionary,default=None,join_character='='):
    value = dictionary.get(param,default)
    result=join_character.join([str(param),str(value)])
    return result

def setup_env_variables_str(envvars):
    return '\n'.join(envvars.split())


def handle(_name, cfg, cloud, log, _args):
   """A replacement cloud-init module for running glidein-bootstrap"""
   
   log.info("Starting...")
   if MODULE_NAME not in cfg:
       log.warn("%s not in the user-data, exiting.." % MODULE_NAME)
       return

   glidein_cfg = cfg[MODULE_NAME]

   ##### VM-PROPERTIES #####
   vm_properties_cfg = None
   try:
       vm_properties_cfg = glidein_cfg[SECTIONS.vm_properties]
   except KeyError:
       print MSG.cannotuse % SECTIONS.vm_properties
       vm_properties_cfg = dict()
   except Exception,e:
       log.error(MSG.fatal % e)
   
   # ensure the directory exists, add an exception? 
   if not os.path.exists(PATHS.default_config_directory):
       os.makedirs(PATHS.default_config_directory)

   glidein_config_file = dict()

   # configurable values from the [DEFAULTS] section
   default_max_lifetime = make_key_value(PARAMETERS.default_max_lifetime,vm_properties_cfg,default=GLIDEIN_DEFAULT_VALUES.default_max_lifetime)
   contextualize_protocol = make_key_value(PARAMETERS.contextualize_protocol,vm_properties_cfg,default=GLIDEIN_DEFAULT_VALUES.contextualize_protocol)
   disable_shutdown = make_key_value(PARAMETERS.disable_shutdown,vm_properties_cfg,default=GLIDEIN_DEFAULT_VALUES.disable_shutdown)
   ec2_url = make_key_value(PARAMETERS.ec2_url, vm_properties_cfg,default=GLIDEIN_DEFAULT_VALUES.ec2_url) # usually should be empty in the configuration

   glidein_config_file['[DEFAULTS]'] = [default_max_lifetime,contextualize_protocol,disable_shutdown,ec2_url]

   # configure values from the [GRID_ENV] section
   environment = ''
   try:
       environment = vm_properties_cfg[PARAMETERS.environment]
   except KeyError:
       pass
   except Exception,e:
       log.warn(MSG.fatal % PARAMETERS.environment)
   finally:
       environment = setup_env_variables_str(environment)

   glidein_config_file['[GRID_ENV]'] = [environment]
   
   # default [GLIDEIN_USER] section
   user_name = make_key_value(PARAMETERS.user_name, vm_properties_cfg, default=GLIDEIN_DEFAULT_VALUES.user_name)
   user_home = make_key_value(PARAMETERS.user_home,vm_properties_cfg, default=GLIDEIN_DEFAULT_VALUES.user_home)
   user_ids = make_key_value(PARAMETERS.user_ids,vm_properties_cfg, default=GLIDEIN_DEFAULT_VALUES.user_ids)

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
   except KeyError:
       print MSG.cannotuse % SECTIONS.glidein_startup
       glidein_startup_cfg = dict()
       
   args = make_key_value(PARAMETERS.args,glidein_startup_cfg,default='')
   proxy_file_name = make_key_value(PARAMETERS.proxy_file_name,glidein_startup_cfg,default='')
   webbase = make_key_value(PARAMETERS.webbase,glidein_startup_cfg,default='')

   content = '\n'.join([args,proxy_file_name,webbase])
   with open(PATHS.runtime_directory+'/'+PATHS.glidein_userdata_file,'w') as fh:
       fh.write("[glidein_startup]\n")
       fh.write(content)
   
   ###### PROXY FILE ######

   proxy = None
   try:
       proxy = glidein_cfg[SECTIONS.proxy]
   except KeyError:
       print MSG.cannotuse % SECTIONS.proxy
       proxy = base64.b64encode(MSG.emptyfile)
   except Exception,e:
       log.warn(MSG.fatal % e)

   proxy_file = None
   try:
       proxy_file = base64.b64decode(proxy) ## we must decode it
   except TypeError,e:
       log.warn(MSG.cannot_base64 % e)
       proxy_file = MSG.emptyfile

   proxy_file_path = glidein_startup_cfg.get(PARAMETERS.proxy_file_name,GLIDEIN_DEFAULT_VALUES.proxy_file_name)
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
       print MSG.cannotuse % SECTIONS.additional_args

   # glidein will eventually eat this file
   with open(PATHS.runtime_directory+'/'+ PATHS.global_userdata_file,'w') as fh:
       fh.write(''.join([tar_encoded,'####',additional_args]))


   log.info("done.")
