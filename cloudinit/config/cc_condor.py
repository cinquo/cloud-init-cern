###########
# Author: Cristovao Cordeiro <christovao.jose.domingues.cordeiro@cern.ch>
#
# Cloud Config module for Condor service. Testes and working on SLC6 machines.
# Documentation in:
# https://twiki.cern.ch/twiki/bin/view/LCG/CloudInit
###########

import subprocess
import cloudinit.CloudConfig as cc
import urllib
import os
import re
import platform

def handle(_name, cfg, cloud, log, _args):
   if 'condor' in cfg:
    	condor_cc_cfg = cfg['condor']    
    	if 'master' in condor_cc_cfg and 'workernode' in condor_cc_cfg:
        	print 'You can not set condor master and condor workernode in the same machine.\n'
        	print 'Exiting condor configuration...'
        	return

    	print "Checking for previous condor versions."
 
    	if subprocess.call(['service','condor','stop']):
		# If it returns 1 it means that the command failed and that condor isn't recognized
		print "No previous condor version was found! Moving on"
		OldVersion = False
	else:
		OldVersion = True
		print "Condor is already installed. Applying your configuration parameters and deleting the old ones."
		OldConfigFile_aux = subprocess.Popen(['find','/','-name','condor_config.local'], stdout=subprocess.PIPE)
		OldConfigFile, olderr = OldConfigFile_aux.communicate()

		OldConfigFile = re.sub('\n','',OldConfigFile)

		# Comment the above lines and uncomment the following ones if you want a clean condor installation even if there is already a condor installed
		# subprocess.check_call(['pkill','-f','condor'])
            	# subprocess.check_call(['rpm','-e','$(rpm -qa | grep condor)'])
            	# subprocess.check_call(['rm','/etc/yum.repos.d/condor-stable-rhel5.repo'])        

	# Condor configuration file
        ConfigFile = '/root/condor_config.local'

	# Default CONDOR_HOST
        Host = subprocess.Popen(["hostname", "-f"], stdout=subprocess.PIPE)
        Hostname, ReleaseErr = Host.communicate()
	Hostname = re.sub('\n','',Hostname)      

	if not OldVersion:
		CondorRepo = "http://www.cs.wisc.edu/condor/yum/repo.d/condor-stable-rhel6.repo"
		urllib.urlretrieve(CondorRepo,'/etc/yum.repos.d/condor.repo')        	

		# Defining the most suitable condor version for the machine
		arch = str(platform.machine())
		if arch == 'x86_64': arch = '.'+str(arch)
		else:
			arch = '.i'
		version0 = subprocess.Popen(['yum','info','condor%s' % arch], stdout=subprocess.PIPE)
		version1 = subprocess.Popen(['grep','Version   '], stdin=version0.stdout, stdout=subprocess.PIPE)
		version0.stdout.close()
		yum_version, verror = version1.communicate()
		yum_version = re.sub('\n','', yum_version)
		yum_version = re.sub(' ','',yum_version)
		
		yum_condor_version = yum_version.split(':')
		
		DownloadManually = False
		# If CondorVersion is empty that it means that condor is not available on the yum repository or that some error has occured
		if not yum_condor_version:
			# In this case let's define and download manually the condor we want to install 
			CondorVersion = "condor-7.8.7"	# Stable version
			DownloadManually = True
		else:
			CondorVersion = 'condor-'+str(yum_condor_version[1])

 	        # Sourcing from /etc/profile.d/condor.sh
            	path_aux = subprocess.Popen(['echo ${PATH}'], stdout=subprocess.PIPE, shell=True)
            	path_aux2 = subprocess.Popen(['tr','\n',':'], stdin=path_aux.stdout, stdout=subprocess.PIPE)
            	path_aux.stdout.close()
            	Path, perr = path_aux2.communicate()

            	f3 = open('/etc/profile.d/condor.sh','a') # Create if the file doesn't exist
            	f3.write("export PATH="+str(Path)+"/opt/"+CondorVersion+"/usr/bin:/opt/"+str(CondorVersion)+"/usr/sbin:/sbin\nexport CONDOR_CONFIG=/opt/"+str(CondorVersion)+"/etc/condor/condor_config\n")
            	f3.close()

            	os.environ['PATH'] = os.environ['PATH']+":/opt/"+CondorVersion+"/usr/bin:/opt/"+str(CondorVersion)+"/usr/sbin:/sbin"
            	os.environ['CONDOR_CONFIG'] = "/opt/"+str(CondorVersion)+"/etc/condor/condor_config"
            	# This sourcing is done here, instead of being done in the end, to avoid situation where the user logs in into the machine before the configuration is finished.

        	print "Installing Condor dependencies..."
        	cc.install_packages(("yum-downloadonly","libtool-ltdl","libvirt","perl-XML-Simple","openssl098e","compat-expat1","compat-openldap","perl-DateManip","perl-Time-HiRes","policycoreutils-python",))
		
		if arch == '.i': arch == ''	# To avoid confusions between i386 and i686, which are 32 bits. So let's just 'yum install condor' in case the machine is 32 bits

		if not DownloadManually:
			subprocess.call(["yum -y install condor%s --downloadonly --downloaddir=/tmp" % arch] , shell=True)		

	        	r1 = subprocess.Popen(["ls -1 /tmp/condor-*.rpm"], stdout=subprocess.PIPE, shell=True)
        		r2 = subprocess.Popen(["head", "-1"],stdin=r1.stdout, stdout=subprocess.PIPE)
        		r1.stdout.close()
        		CondorRPM, rerror = r2.communicate()
			CondorRPM = re.sub('\n','',CondorRPM)	
		else:			
			arch = str(platform.machine())	# All of these arch redefinements are due to the fact that on the yum repo, the condor 32 bits is named condor.i386 and on the official website it is condor.i686
			# If condor is not available in the yum repository you can uncomment the following lines to donwload the .rpm directly from the source.
			try:
				urllib.urlretrieve('http://research.cs.wisc.edu/htcondor/yum/stable/rhel6/condor-7.8.7-86173.rhel6.3.'+arch+'.rpm', '/root/condor.rpm') 	# Version 7.8.7
			except:
				# If it failed it probably means that the arch is not right or it is not compatible with the available condor versions
				urllib.urlretrieve('http://research.cs.wisc.edu/htcondor/yum/stable/rhel6/condor-7.8.7-86173.rhel6.3.i686.rpm', '/root/condor.rpm')
				CondorRPM = '/root/condor.rpm'

        	print "Condor installation:"
        	subprocess.check_call(["rpm -ivh %s --relocate /usr=/opt/%s/usr --relocate /var=/opt/%s/var --relocate /etc=/opt/%s/etc" % (CondorRPM, CondorVersion, CondorVersion, CondorVersion)] , shell=True) 	# Relocating...
       		# subprocess.check_call(["rpm -ivh %s" % CondorRPM], shell=True) 	# Uncomment this line and comment the above one if you do not want to relocate condor installation
	
	# Write new configuration file
        f = open(ConfigFile,'w')        
	
	# Default variables    
        DaemonList = 'MASTER, STARTD'
        Highport = 24500
        Lowport = 20000
        CollectorHostPORT = 20001
        Start = 'True'
        Suspend = 'False'
        Preempt = 'False'
        Kill = 'False'
        QueueSuperUsers = 'root, condor'        
        AllowWrite = '*'
        StarterAllowRunasOwner = 'False'
        AllowDaemon = '*'
        HostAllowRead = '*'
        HostAllowWrite = '*'
        SecDaemonAuthentication = 'OPTIONAL'

        # PARAMETERS LIST
        if 'workernode' in condor_cc_cfg:
            condor_cfg = condor_cc_cfg['workernode']
            if 'condor-host' in condor_cfg:
                Hostname = condor_cfg['condor-host']
            f.write("CONDOR_HOST = "+str(Hostname)+'\n')

            f.write("COLLECTOR_NAME = Personal Condor at "+Hostname+'\n')

            CondorAdmin = Hostname
            UIDDomain = Hostname        

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
                CondorAdmin = condor_cfg['condor-admin']
            f.write("CONDOR_ADMIN = "+str(CondorAdmin)+'\n')

            if 'queue-super-users' in condor_cfg:
                QueueSuperUsers = condor_cfg['queue-super-users']
            f.write("QUEUE_SUPER_USERS = "+str(QueueSuperUsers)+'\n')

            if 'highport' in condor_cfg:
                Highport = condor_cfg['highport']
            f.write("HIGHPORT = "+str(Highport)+'\n')

            if 'lowport' in condor_cfg:
                Lowport = condor_cfg['lowport']
            f.write("LOWPORT = "+str(Lowport)+'\n')

            if 'uid-domain' in condor_cfg:
                UIDDomain = condor_cfg['uid-domain']
            f.write("UID_DOMAIN = "+str(UIDDomain)+'\n')

            if 'allow-write' in condor_cfg:
                AllowWrite = condor_cfg['allow-write']    
            f.write("ALLOW_WRITE = "+str(AllowWrite)+'\n')

            if 'dedicated-execute-account-regexp' in condor_cfg:
                f.write("DEDICATED_EXECUTE_ACCOUNT_REGEXP = "+str(condor_cfg['dedicated-execute-account-regexp'])+'\n')

            if 'allow-daemon' in condor_cfg:
                AllowDaemon = condor_cfg['allow-daemon']
            f.write("ALLOW_DAEMON = "+str(AllowDaemon)+'\n')

            if 'starter-allow-runas-owner' in condor_cfg:
                StarterAllowRunasOwner = condor_cfg['starter-allow-runas-owner']    
            f.write("STARTER_ALLOW_RUNAS_OWNER = "+str(StarterAllowRunasOwner)+'\n')

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
                SecDaemonAuthentication = condor_cfg['sec-daemon-authentication']
            f.write("SEC_DAEMON_AUTHENTICATION = "+str(SecDaemonAuthentication)+'\n')

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
                HostAllowWrite = condor_cfg['hostallow-write']    
            f.write("HOSTALLOW_WRITE = "+str(HostAllowWrite)+'\n')
    
            if 'hostallow-read' in condor_cfg:
                HostAllowRead = condor_cfg['hostallow-read']    
            f.write("HOSTALLOW_READ = "+str(HostAllowRead)+'\n')

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

            # Dynamically writing SLOT users
            CPUs_aux = subprocess.Popen(['cat /proc/cpuinfo | grep processor | wc -l'], stdout=subprocess.PIPE, shell=True)
            CPUs, cpuerr = CPUs_aux.communicate()
            CPUs = re.sub('\n','', CPUs)  

            for count in range(1,int(CPUs)+1):
                f.write("SLOT"+str(count)+"_USER = user"+str(count)+'\n')
                os.system("useradd -m -s /sbin/nologin  user"+str(count)+" > /dev/null 2>&1\n")

 	Start = 'False'           
        DaemonList = 'COLLECTOR, MASTER, NEGOTIATOR, SCHEDD'        
        if 'master' in condor_cc_cfg:
            condor_cfg = condor_cc_cfg['master']

            f.write("CONDOR_HOST = "+str(Hostname)+'\n')

            f.write("COLLECTOR_NAME = Personal Condor at "+Hostname+'\n')

            if 'collector-host-port' in condor_cfg:
                CollectorHostPORT = condor_cfg['collector-host-port']
            f.write("COLLECTOR_HOST = "+str(Hostname)+':'+str(CollectorHostPORT)+'\n')
            
            if 'highport' in condor_cfg:
                Highport = condor_cfg['highport']
            f.write("HIGHPORT = "+str(Highport)+'\n')

            if 'lowport' in condor_cfg:
                Lowport = condor_cfg['lowport']
            f.write("LOWPORT = "+str(Lowport)+'\n')

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

            if 'hostallow-write' in condor_cfg:
                HostAllowWrite = condor_cfg['hostallow-write']
            f.write("HOSTALLOW_WRITE = "+str(HostAllowWrite)+'\n')

            if 'hostallow-read' in condor_cfg:
                HostAllowRead = condor_cfg['hostallow-read']
            f.write("HOSTALLOW_READ = "+str(HostAllowRead)+'\n')

	    if 'daemon-list' in condor_cfg:
                DaemonList = condor_cfg['daemon-list']
            f.write("DAEMON_LIST = "+DaemonList+'\n')

            cid1 = subprocess.Popen(["cat", "/etc/passwd"], stdout=subprocess.PIPE)
            cid2 = subprocess.Popen(["grep", "condor:"],stdin=cid1.stdout, stdout=subprocess.PIPE)
            cid3 = subprocess.Popen(["awk", "-F:",'{print $3"."$4}'], stdin=cid2.stdout, stdout=subprocess.PIPE)
            cid1.stdout.close()
            cid2.stdout.close()

            CondorIDs, Err = cid3.communicate()

            f.write("CONDOR_IDS = "+str(CondorIDs)+'\n')

            f.write("SEC_DAEMON_AUTHENTICATION = OPTIONAL\n")
            f.write("SEC_DEFAULT_AUTHENTICATION = OPTIONAL\n")

        f.close()
        subprocess.check_call(['/etc/init.d/iptables', 'stop'])		# The iptables should be configured instead of being stopped 

	if not OldVersion:
        	# Moving our config file to the right directory (erase the old config)        
        	subprocess.check_call(['rm','-f','/opt/%s/etc/condor/condor_config.local' % CondorVersion])
        	subprocess.check_call(['cp','/root/condor_config.local','/opt/%s/etc/condor/' % CondorVersion])
		subprocess.call(['rm','-f','/root/condor_config.local'])
      
		subprocess.call(['chown','-R','condor:condor','/opt/%s' % CondorVersion])
		subprocess.call(['chmod','-R','go+rwx','/opt/%s/var/log' % CondorVersion])

		# Specifying additional default directories in /etc/ld.so.conf
	        f2 = open('/etc/ld.so.conf','a')
     	   	f2.write('/opt/'+CondorVersion+'/usr/lib64\n/opt/'+CondorVersion+'/usr/lib64/condor\n')
        	f2.close()

        	# Executing ldconfig
        	subprocess.check_call(['/sbin/ldconfig'])
                

	else:
		# Moving our config file to the right directory (overwrite the old config)
                subprocess.check_call(['rm','-f','%s' % OldConfigFile])
                subprocess.check_call(['cp','/root/condor_config.local','%s' % OldConfigFile])
                subprocess.call(['rm','-f','/root/condor_config.local'])

        # Starting condor
        subprocess.check_call(['service','condor','start'])

	# END
