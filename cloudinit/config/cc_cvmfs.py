###########
# Author: Cristovao Cordeiro <christovao.jose.domingues.cordeiro@cern.ch>
#
# Cloud Config module for CVMFS service. Testes and working on SLC6 machines.
# Documentation in:
# https://twiki.cern.ch/twiki/bin/view/LCG/CloudInit
###########

import subprocess
import cloudinit.util as util
import cloudinit.CloudConfig as cc
import platform
import urllib


def handle(_name, cfg, cloud, log, _args):
    
    # If there isn't a cvmfs reference in the configuration don't do anything
    if 'cvmfs' not in cfg:
        print "cvmfs configuration was not found"
        return
    
    print "Ready to setup cvmfs."
    cvmfs_cfg = cfg['cvmfs']
    if 'cvmfs' in cfg:	
	print "Configuring cvmfs...(this may take a while)"
	
	# Let's retrieve the current cvmfs release
	ReleaseAux = subprocess.Popen(["rpm", "-q", "--queryformat", "%{version}", "sl-release"], stdout=subprocess.PIPE)
	Release, ReleaseErr = ReleaseAux.communicate()
		
	ReleaseMajor = Release[0]
	
	arch = platform.machine()	# Platform info
	
	# cvmfs package url
	cvmfs_rpm_url = 'http://cvmrepo.web.cern.ch/cvmrepo/yum/cvmfs/EL/'+Release+'/'+arch+'/cvmfs-release-2-2.el'+ReleaseMajor+'.noarch.rpm'
	# Downloading cvmfs .rpm file to /home path
	urllib.urlretrieve(cvmfs_rpm_url, '/home/cvmfs.rpm')
	if subprocess.check_call(["rpm", "-i", "/home/cvmfs.rpm"]):	# If it returns 0 then it is fine
	    print ".rpm installation failed"
            return
    	else:
            print ".rpm installation successful."

	# Install cvmfs packages
	try:
		cc.install_packages(("cvmfs-keys","cvmfs","cvmfs-init-scripts",))   # If this fails then yum clean all
	except:
		subprocess.call(['yum','clean','all'])
		try:
			cc.install_packages(("cvmfs-keys","cvmfs","cvmfs-init-scripts",))
		except:
			print "CVMFS installation from the yum repository has failed\n"
			print "Ignoring CVMFS setup..."
			return
	
	# Base setup
	subprocess.call(["cvmfs_config", "setup"])
        
	# Start autofs and make it starting automatically after reboot 
        subprocess.call(['service','autofs','start'])
        subprocess.call(['chkconfig','autofs','on'])
        subprocess.call(['cvmfs_config','chksetup'])	

	LocalFile = '/etc/cvmfs/default.local'
	DomainFile = '/etc/cvmfs/domain.d/cern.ch.local'
        quota_aux_var = 1   # Aux varibale to check whether to write default quota-limit value or not	
	# To configure cvmfs...
	if 'local' in cvmfs_cfg:
	    local_args = cvmfs_cfg['local']
	    flocal = open(LocalFile, 'w')
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
                    flocal.write('\nCMS_LOCAL_SITE='+str(value)+'\n')
		    flocal.write('export CMS_LOCAL_SITE=T2_CH_CERN_AI\n')
	
	    # Write some default configurations
            if quota_aux_var:
	        flocal.write('CVMFS_QUOTA_LIMIT=8000\nCVMFS_TIMEOUT=5\nCVMFS_TIMEOUT_DIRECT=10\nCVMFS_NFILES=65535\n')  
	    else:
                flocal.write('CVMFS_TIMEOUT=5\nCVMFS_TIMEOUT_DIRECT=10\nCVMFS_NFILES=65535\n')
	    
            # Close the file
	    flocal.close()
	    
	
	if 'domain' in cvmfs_cfg:
	    domain_args = cvmfs_cfg['domain']
	    if 'server' in domain_args:
	        fdomain = open(DomainFile, 'w')
	        fdomain.write('CVMFS_SERVER_URL='+domain_args['server']+'\n')
	        fdomain.close()
	        
	
	print "START cvmfs"
        # Start cvmfs
        subprocess.check_call(['service', 'cvmfs', 'start'])
        subprocess.call(['service', 'cvmfs', 'probe'])    # To mount the repositories
	        
