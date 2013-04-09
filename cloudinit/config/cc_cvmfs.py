# vi: ts=4 expandtab
#
#    Copyright (C) 2013 CERN
#
#    Author: Cristovao Cordeiro <christovao.jose.domingues.cordeiro@cern.ch>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License version 3, as
#    published by the Free Software Foundation.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

import subprocess
import cloudinit.util as util
import cloudinit.CloudConfig as cc
import platform
import urllib


def handle(_name, cfg, cloud, log, _args):
	print "Searching for cvmfs reference..."
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
		# print Release		# If you want to check the release number
		
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
		cc.install_packages(("cvmfs-keys","cvmfs","cvmfs-init-scripts",))   # TODO: create a failure check here. If it fails, do a yum -y clean all
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

			# Write some default configurations
			if quota_aux_var:
				flocal.write('CVMFS_QUOTA_LIMIT=8000\nCVMFS_TIMEOUT=5\nCVMFS_TIMEOUT_DIRECT=10\nCVMFS_NFILES=65535')
			else:
				flocal.write('CVMFS_TIMEOUT=5\nCVMFS_TIMEOUT_DIRECT=10\nCVMFS_NFILES=65535')

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
		subprocess.check_call(['service', 'cvmfs', 'probe'])    # To mount the repositories

