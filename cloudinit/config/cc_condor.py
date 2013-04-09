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
#    along with this program.  If not, see <http://www.gnu.org/licenses/>

import subprocess
import cloudinit.CloudConfig as cc
import urllib
from os import environ
import re

# Cloud Config module for condor 7.8.7
def handle(_name, cfg, cloud, log, _args):
   if 'condor' in cfg:
        print "If there is any previous version of condor, it must be removed."
	if subprocess.call(['service','condor','stop']):
		# If it returns 1 it means that the command failed and that condor isn't recognized
		print "No previous condor version was found! Moving on"
	else:
		subprocess.check_call(['pkill','-f','condor'])
            	subprocess.check_call(['rpm','-e','$(rpm -qa | grep condor)'])
            	subprocess.check_call(['rm','/etc/yum.repos.d/condor-stable-rhel5.repo'])        

	# Condor configuration file
        ConfigFile = '/root/condor_config.local'

	# Default CONDOR_HOST
        Host = subprocess.Popen(["hostname", "-f"], stdout=subprocess.PIPE)
        Hostname, ReleaseErr = Host.communicate()
        
	CondorRepo = "http://www.cs.wisc.edu/condor/yum/repo.d/condor-stable-rhel5.repo"
        CondorVersion = "condor-7.8.7"	# Stable version. 

	Hostname = re.sub('\n','',Hostname)	

        urllib.urlretrieve(CondorRepo,'/root/condor-7.8.7.repo')

        print "Installing Condor dependencies..."
        cc.install_packages(("yum-downloadonly","libvirt","perl-XML-Simple","openssl098e","compat-expat1","compat-openldap","perl-DateManip","perl-Time-HiRes","policycoreutils-python",))

	# At the moment the latest stable version of condor is not available in yum repository.
	# When it is, you can uncomment this next part and comment the .rpm retieving from the official source.

        # r1 = subprocess.Popen(["ls","-1","/tmp/condor-*.rpm"], stdout=subprocess.PIPE)
        # r2 = subprocess.Popen(["head", "-1"],stdin=r1.stdout, stdout=subprocess.PIPE)
        # r1.stdout.close()
        # CondorRPM, rerror = r2.communicate()

	urllib.urlretrieve('http://research.cs.wisc.edu/htcondor/yum/stable/rhel6/condor-7.8.7-86173.rhel6.3.x86_64.rpm', '/root/condor.rpm') 	# Stable version

        print "Condor installation:"
        subprocess.check_call(["rpm","-ivh","/root/condor.rpm"]) 	# Relocating results on some issues, so install condor by default
        
        f = open(ConfigFile,'w')        
        condor_cfg = cfg['condor']
	
	# Default variables    
        DaemonList = 'COLLECTOR, MASTER, NEGOTIATOR, SCHEDD, STARTD'
        Highport = 24500
        Lowport = 20000
        CollectorHostPORT = 20001
        Start = 'True'
        Suspend = 'False'
        Preempt = 'False'
        Kill = 'False'
        
        # PARAMETERS LIST

        if 'condor-master' in condor_cfg:
            Hostname = condor_cfg['condor-master']
        f.write("CONDOR_HOST = "+str(Hostname)+'\n')

        f.write("COLLECTOR_NAME = Personal Condor at "+Hostname+'\n')

        if 'collector-host-port' in condor_cfg:
            CollectorHostPORT = condor_cfg['collector-host-port']
        f.write("COLLECTOR_HOST = "+str(Hostname)+':'+str(CollectorHostPORT)+'\n')

        if 'daemon-list' in condor_cfg:
            DaemonList = condor_cfg['daemon-list']
        f.write("DAEMON_LIST = "+DaemonList+'\n')

        if 'release-dir' in condor_cfg:
            f.write("RELEASE_DIR = "+condor_cfg['release-directory']+'\n')
        
        if 'local-dir' in condor_cfg:
            f.write("LOCAL_DIR = "+condor_cfg['local-dir']+'\n')
    
        if 'condor-admin' in condor_cfg:
            f.write("CONDOR_ADMIN = "+str(condor_cfg['condor-admin'])+'\n')

        if 'queue-super-users' in condor_cfg:
            f.write("QUEUE_SUPER_USERS = "+condor_cfg['queue-super-users']+'\n')

        if 'highport' in condor_cfg:
            Highport = condor_cfg['highport']
        f.write("HIGHPORT = "+str(Highport)+'\n')

        if 'lowport' in condor_cfg:
            Lowport = condor_cfg['lowport']
        f.write("LOWPORT = "+str(Lowport)+'\n')

        if 'uiddomain' in condor_cfg:
            f.write("UID_DOMAIN = "+str(condor_cfg['uiddomain'])+'\n')

        if 'allow-write' in condor_cfg:
            f.write("ALLOW_WRITE = "+str(condor_cfg['allow-write'])+'\n')

        if 'dedicated-execute-account-regexp' in condor_cfg:
            f.write("DEDICATED_EXECUTE_ACCOUNT_REGEXP = "+str(condor_cfg['dedicated-execute-account-regexp'])+'\n')

        if 'starter-allow-runas-owner' in condor_cfg:
            f.write("STARTER = "+str(condor_cfg['filesystem-domain'])+'\n')

        if 'java' in condor_cfg:
            f.write("JAVA = "+str(condor_cfg['java'])+'\n')

        if 'user-job-wrapper' in condor_cfg:
            f.write("USER_JOB_WRAPPER = "+str(condor_cfg['user-job-wrapper'])+'\n')

        if 'gsite' in condor_cfg:
            f.write("GSITE = "+str(condor_cfg['gsite'])+'\n')

        if 'startd-attrs' in condor_cfg:
            f.write("STARTD_ATTRS = "+str(condor_cfg['startd-attrs'])+'\n')

        if 'enable-ssh-to-job' in condor_cfg:
            f.write("ENABLE_SSH_TO_JOB = "+str(condor_cfg['enable-ssh-to-job'])+'\n')

        if 'certificate-mapfile' in condor_cfg:
            f.write("CERTIFICATE_MAPFILE = "+str(condor_cfg['certificate-mapfile'])+'\n')

        if 'ccb-address' in condor_cfg:
            f.write("CCB_ADDRESS = "+str(condor_cfg['ccb-address'])+'\n')

        if 'execute' in condor_cfg:
            f.write("EXECUTE = "+str(condor_cfg['execute'])+'\n')        

        if 'starter-debug' in condor_cfg:
            f.write("STARTER_DEBUG = "+str(condor_cfg['starter-debug'])+'\n')

        if 'startd-debug' in condor_cfg:
            f.write("STARTD_DEBUG = "+str(condor_cfg['startd-debug'])+'\n')

        if 'sec-default-authentication' in condor_cfg:
            f.write("SEC_DEFAULT_AUTHENTICATION = "+str(condor_cfg['sec-default-authentication'])+'\n')

        if 'sec-default-authentication-methods' in condor_cfg:
            f.write("SEC_DEFAULT_AUTHENTICATION_METHODS = "+str(condor_cfg['sec-default-authentication-methods'])+'\n')

        if 'sec-daemon-authentication' in condor_cfg:
            f.write("SEC_DAEMON_AUTHENTICATION = "+str(condor_cfg['sec-daemon-authentication'])+'\n')

        if 'sec-password-file' in condor_cfg:
            f.write("SEC_PASSWORD_FILE = "+str(condor_cfg['sec-password-file'])+'\n')

        if 'update-collector-with-tcp' in condor_cfg:
            f.write("UPDATE_COLLECTOR_WITH_TCP = "+str(condor_cfg['update-collector-with-tcp'])+'\n')

        if 'max-job-retirement-time' in condor_cfg:
            f.write("MAXJOBRETIREMENTTIME = "+str(condor_cfg['max-job-retirement-time'])+'\n')

        if 'startd-cron-joblist' in condor_cfg:
            f.write("STARTD_CRON_JOBLIST = "+str(condor_cfg['startd-cron-joblist'])+'\n')

        if 'startd-cron-atlval-mode' in condor_cfg:
            f.write("STARTD_CRON_ATLVAL_MODE = "+str(condor_cfg['startd-cron-atlval-mode'])+'\n')

        if 'startd-cron-atlval-executable' in condor_cfg:
            f.write("STARTD_CRON_ATLVAL_EXECUTABLE = "+str(condor_cfg['startd-cron-atlval-executable'])+'\n')

        if 'startd-cron-atlval-period' in condor_cfg:
            f.write("STARTD_CRON_ATLVAL_PERIOD = "+str(condor_cfg['startd-cron-atlval-period'])+'\n')

        if 'startd-cron-atlval-job-load' in condor_cfg:
            f.write("STARTD_CRON_ATLVAL_JOB_LOAD = "+str(condor_cfg['startd-cron-atlval-job-load'])+'\n')

        if 'hostallow-write' in condor_cfg:
            f.write("HOSTALLOW_WRITE = "+str(condor_cfg['hostallow-write'])+'\n')
    
        if 'hostallow-read' in condor_cfg:
            f.write("HOSTALLOW_READ = "+str(condor_cfg['hostallow-read'])+'\n')

        if 'start' in condor_cfg:
            Start = condor_cfg['start']
        f.write("START = "+str(Start)+'\n')

        if 'suspend' in condor_cfg:
            Suspend = condor_cfg['suspend']
        f.write("SUSPEND = "+str(Suspend)+'\n')

        if 'preempt' in condor_cfg:
            Preempt = condor_cfg['preempt']
        f.write("PREEMPT = "+str(Preempt)+'\n')
        
        if 'kill' in condor_cfg:
            Kill = condor_cfg['kill']
        f.write("KILL = "+str(Kill)+'\n')


        # End of parameters
        ##############################################################################

        cid1 = subprocess.Popen(["cat", "/etc/passwd"], stdout=subprocess.PIPE)
        cid2 = subprocess.Popen(["grep", "condor:"],stdin=cid1.stdout, stdout=subprocess.PIPE)
        cid3 = subprocess.Popen(["awk", "-F:",'{print $3"."$4}'], stdin=cid2.stdout, stdout=subprocess.PIPE)
        cid1.stdout.close()
        cid2.stdout.close()
        
        CondorIDs, Err = cid3.communicate()
    
        f.write("CONDOR_IDS = "+str(CondorIDs)+'\n')

        f.close()
        
        # Moving our config file to the right directory (erase the old config)        
        subprocess.check_call(['rm','-f','/etc/condor/condor_config.local'])
        subprocess.check_call(['cp','/root/condor_config.local','/etc/condor/'])

        # Specifying additional default directories in /etc/ld.so.conf
        f2 = open('/etc/ld.so.conf','a')
        f2.write("/opt/$CONDOR_VERSION/usr/lib64\n/opt/$CONDOR_VERSION/usr/lib64/condor\n")
        f2.close()

        # Sourcing from /etc/profile.d/condor.sh
        path_aux = subprocess.Popen(['echo ${PATH}'], stdout=subprocess.PIPE, shell=True)
        path_aux2 = subprocess.Popen(['tr','\n',':'], stdin=path_aux.stdout, stdout=subprocess.PIPE)
	path_aux.stdout.close()
	Path, perr = path_aux2.communicate()
        
        f3 = open('/etc/profile.d/condor.sh','a') # Create if the file doesn't exist
        f3.write("export PATH="+str(Path)+"/opt/"+str(CondorVersion)+"/usr/bin:/opt/"+str(CondorVersion)+"/usr/sbin:/sbin\nexport CONDOR_CONFIG=/opt/"+str(CondorVersion)+"/etc/condor/condor_config\n")
        f3.close()

        # Executing ldconfig
        subprocess.check_call(['/sbin/ldconfig'])

        # Sourcing
        pipe = subprocess.Popen(". /etc/profile.d/condor.sh; env", stdout=subprocess.PIPE, shell=True)
	data = pipe.communicate()[0]
	env = dict((line.split("=", 1) for line in data.splitlines()))

	environ.update(env)

        # Starting condor
        subprocess.check_call(['service','condor','start'])


        # END
