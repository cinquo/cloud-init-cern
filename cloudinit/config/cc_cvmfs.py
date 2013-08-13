#################################################################################
# Author: Cristovao Cordeiro <cristovao.cordeiro@cern.ch>			#
#										#
# Cloud Config module for CVMFS service. Testes and working on SLC6 machines.	#
# Documentation in:								#
# https://twiki.cern.ch/twiki/bin/view/LCG/CloudInit				#
#################################################################################

import subprocess
import cloudinit.util as util
import cloudinit.config as cc
import platform
import urllib
import sys
import os

# In case this runs to early during the boot, the PATH environment can still be unset. Let's define each necessary command's path
# Using subprocess calls so it raises exceptions directly from the child process to the parent
RPM_cmd = '/bin/rpm'
YUM_cmd = '/usr/bin/yum'
SERVICE_cmd = '/sbin/service'
CHK_cmd = '/sbin/chkconfig'


def install_cvmfs():
  # Let's retrieve the current cvmfs release
  ReleaseAux = subprocess.Popen([RPM_cmd, "-q", "--queryformat", "%{version}", "sl-release"], stdout=subprocess.PIPE)
  Release, ReleaseErr = ReleaseAux.communicate()

  ReleaseMajor = Release[0]
  arch = platform.machine()       # Platform info

  # cvmfs package url
  cvmfs_rpm_url = 'http://cvmrepo.web.cern.ch/cvmrepo/yum/cvmfs/EL/'+ReleaseMajor+'/'+arch+'/cvmfs-release-2-3.el'+ReleaseMajor+'.noarch.rpm'
  # Downloading cvmfs .rpm file to /home path
  urllib.urlretrieve(cvmfs_rpm_url, '/home/cvmfs.rpm')
  if subprocess.check_call([RPM_cmd, "-Uvh", "/home/cvmfs.rpm"]): # If it returns 0 then it is fine
    print ".rpm installation failed"
    return
  else:
    print ".rpm installation successful."

  # Install cvmfs packages
  try:
    subprocess.check_call([YUM_cmd,'-y','install','cvmfs-keys','cvmfs','cvmfs-init-scripts'])       # cvmfs-auto-setup can also be installed. Meant for Tier 3's
    #cc.install_packages(("cvmfs-keys","cvmfs","cvmfs-init-scripts",))   # If this fails then yum clean all
  except:
    subprocess.call([YUM_cmd,'clean','all'])
    try:
      subprocess.check_call([YUM_cmd,'-y','install','cvmfs-keys','cvmfs','cvmfs-init-scripts'])
                                #cc.install_packages(("cvmfs-keys","cvmfs","cvmfs-init-scripts",))
    except:
      print "CVMFS installation from the yum repository has failed\n"
      print "Ignoring CVMFS setup..."
      return

  # Base setup
  os.system("export PATH=${PATH}:/usr/bin:/sbin; cvmfs_config setup")
  #subprocess.call(["/usr/bin/cvmfs_config setup"], shell=True)

  # Start autofs and make it starting automatically after reboot 
  subprocess.check_call([SERVICE_cmd,'autofs','start'])
  subprocess.check_call([CHK_cmd,'autofs','on'])
  os.system("export PATH=${PATH}:/usr/bin:/sbin; cvmfs_config chksetup")
                #subprocess.check_call(['cvmfs_config','chksetup'])

########################
########################

def config_cvmfs(lfile, dfile, cmsfile, params):
  quota_aux_var = 1   # Aux varibale to check whether to write default quota-limit value or not   
  if 'local' in params:
    local_args = params['local']
    flocal = open(lfile, 'w')
    for prop_name, value in local_args.iteritems():
      if prop_name == 'repositories':
        flocal.write('CVMFS_REPOSITORIES='+value+'\n')
      if prop_name == 'cache-base':
        flocal.write('CVMFS_CACHE_BASE='+value+'\n')
      if prop_name == 'default-domain':
        flocal.write('CVMFS_DEFAULT_DOMAIN='+value+'\n')
      if prop_name == 'http-proxy':
        flocal.write('CVMFS_HTTP_PROXY='+value+'\n')
      if prop_name == 'quota-limit':
        flocal.write('CVMFS_QUOTA_LIMIT='+str(value)+'\n')
        quota_aux_var = 0
      if prop_name == 'cms-local-site':
         cmslocal = open(cmsfile, 'w')
         cmslocal.write('export CMS_LOCAL_SITE='+str(value)+'\n')
         cmslocal.close()

    # Write some default configurations
    if quota_aux_var:
      flocal.write('CVMFS_QUOTA_LIMIT=8000\nCVMFS_TIMEOUT=5\nCVMFS_TIMEOUT_DIRECT=10\nCVMFS_NFILES=65535\n')
    else:
      flocal.write('CVMFS_TIMEOUT=5\nCVMFS_TIMEOUT_DIRECT=10\nCVMFS_NFILES=65535\n')

    # Close the file
    flocal.close()

  if 'domain' in params:
    domain_args = params['domain']
    if 'server' in domain_args:
      fdomain = open(dfile, 'w')
      fdomain.write('CVMFS_SERVER_URL='+domain_args['server']+'\n')
      fdomain.close()

########################
########################

def handle(_name, cfg, cloud, log, _args):
    
  # If there isn't a cvmfs reference in the configuration don't do anything
  if 'cvmfs' not in cfg:
    print "cvmfs configuration was not found"
    return
    
  print "Ready to setup cvmfs."
  cvmfs_cfg = cfg['cvmfs']
  print "Configuring cvmfs...(this may take a while)"
  Installation = False
  if 'install' in cvmfs_cfg:
    Installation = cvmfs_cfg['install']
    if Installation == True:
      install_cvmfs()	    

  LocalFile = '/etc/cvmfs/default.local'
  DomainFile = '/etc/cvmfs/domain.d/cern.ch.local'
  CMS_LocalFile = '/etc/cvmfs/config.d/cms.cern.ch.local'
  
  config_cvmfs(LocalFile, DomainFile, CMS_LocalFile, cvmfs_cfg)
	
  print "START cvmfs"
  # Start cvmfs
  os.system("export PATH=${PATH}:/usr/bin:/sbin; cvmfs_config reload")
  os.system("export PATH=${PATH}:/usr/bin:/sbin; cvmfs_config probe")
	       
