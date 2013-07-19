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
import tempfile

def handle(_name, cfg, cloud, log, _args):
   if 'condor' in cfg:
    	condor_cc_cfg = cfg['condor']    
    	if 'master' in condor_cc_cfg and 'workernode' in condor_cc_cfg:
        	print 'You can not set condor master and condor workernode in the same machine.\n'
        	print 'Exiting condor configuration...'
        	return

	# In case this runs to early during the boot, the PATH environment can still be unset. Let's define each necessary command's path
        # Using subprocess calls so it raises exceptions directly from the child process to the parent
	YUM_cmd = '/usr/bin/yum'
	GREP_cmd = '/bin/grep'
	RPM_cmd = '/bin/rpm'
	SERVICE_cmd = '/sbin/service'
	CAT_cmd = '/bin/cat'
	AWK_cmd = '/bin/awk'
	CP_cmd = '/bin/cp'
	RM_cmd = '/bin/rm'

    	Installation = False
	Repo = False 

	# If Install is False, this will assume that Condor is already installed in the destination
	if 'install' in condor_cc_cfg:
		Installation = condor_cc_cfg['install']
		
	# There is the possibilty of telling the module where to download Condor from		
	if 'rpm-url' in condor_cc_cfg:
               	Repo = True
               	InstallFrom = condor_cc_cfg['rpm-url']
 
	# Condor configuration file
        ConfigFile = '/root/condor_config.local'

	# Default CONDOR_HOST
        #Host = subprocess.Popen(["hostname", "-f"], stdout=subprocess.PIPE)
        #Hostname, ReleaseErr = Host.communicate()
	#Hostname = re.sub('\n','',Hostname)      
	# In case a RPM is being downloaded, let's do it in a temp file
	tp = tempfile.NamedTemporaryFile()	

	if Installation == True:
		print 'Starting Condor installation: '

                print "Installing Condor dependencies..."
                subprocess.check_call([YUM_cmd,"-y","install","libtool-ltdl","libvirt","perl-XML-Simple","openssl098e","compat-expat1","compat-openldap","perl-DateManip","perl-Time-HiRes","policycoreutils-python"])
		#cc.install_packages(("yum-downloadonly","libtool-ltdl","libvirt","perl-XML-Simple","openssl098e","compat-expat1","compat-openldap","perl-DateManip","perl-Time-HiRes","policycoreutils-python",))

	        print 'Overwriting condor_config.local'
		
		if Repo:
			try:
				urllib.urlretrieve(InstallFrom, tp.name)
				CondorRPM = tp.name
				CondorVersion = "condor"
			except:
				print '\nATTENTION: the condor repository you provided is not valid. Skipping condor module...\n'
				return
		else:
			CondorRepo = "http://www.cs.wisc.edu/condor/yum/repo.d/condor-stable-rhel6.repo"
			urllib.urlretrieve(CondorRepo,'/etc/yum.repos.d/condor.repo')        	

			# Defining the most suitable condor version for the machine
			arch = str(platform.machine())
			if arch == 'x86_64': arch = '.'+str(arch)
			else:
				arch = '.i'
			version0 = subprocess.Popen([YUM_cmd,'info','condor%s' % arch], stdout=subprocess.PIPE)
			version1 = subprocess.Popen([GREP_cmd,'Version   '], stdin=version0.stdout, stdout=subprocess.PIPE)
			version0.stdout.close()
			yum_version, verror = version1.communicate()
			yum_version = re.sub('\n','', yum_version)
			yum_version = re.sub(' ','',yum_version)
			
			yum_condor_version = yum_version.split(':')
		
			DownloadManually = False
			# If CondorVersion is empty that it means that condor is not available on the yum repository or that some error has occured
			if not yum_condor_version:
				# In this case let's define and download manually the condor we want to install 
				CondorVersion = "condor-8.0.0"	# Stable version
				DownloadManually = True
			else:
				CondorVersion = 'condor-'+str(yum_condor_version[1])
	
			if arch == '.i': arch == ''     # To avoid confusions between i386 and i686, which are 32 bits. So let's just 'yum install condor' in case the machine is 32 bits

                if not Repo:
                        if not DownloadManually:
				subprocess.check_call([YUM_cmd,'-y','install','condor'+arch])
                                #cc.install_packages(('condor'+arch,))
                        else:
                                # If condor is not available in the yum repository (due to some odd reason) you can uncomment the following lines to donwload the .rpm directly from the source.
                                try:
                                        # Download a version that will most certainly work in every machine.
                                        urllib.urlretrieve('http://research.cs.wisc.edu/htcondor/yum/stable/rhel6/condor-8.0.0-133173.rhel6.4.i686.rpm', tp.name)
                                except:
                                        print 'It was not possible to install Condor from any available source. Exiting condor setup...'
                                        return
                                CondorRPM = tp.name
                                subprocess.check_call([RPM_cmd,"-ivh",CondorRPM])
                else:
                        subprocess.check_call([RPM_cmd,"-ivh",CondorRPM])
                        # subprocess.check_call(["rpm -ivh %s --relocate /usr=/opt/%s/usr --relocate /var=/opt/%s/var --relocate /etc=/opt/%s/etc" % (CondorRPM, CondorVersion, CondorVersion, CondorVersion)] , shell=True)    # Relocating

 		# Sourcing from /etc/profile.d/condor.sh
            	#path_aux = subprocess.Popen(['echo ${PATH}'], stdout=subprocess.PIPE, shell=True)
	        #path_aux2 = subprocess.Popen(['tr','\n',':'], stdin=path_aux.stdout, stdout=subprocess.PIPE)
        	#path_aux.stdout.close()
            	#Path, perr = path_aux2.communicate()
	
        	#f3 = open('/etc/profile.d/condor.sh','a+') # Create if the file doesn't exist
            	#f3.write("export PATH="+str(Path)+"/usr/sbin:/sbin\nexport CONDOR_CONFIG=/etc/condor/condor_config\n")
	        #f3.close()
	
        	os.environ['PATH'] = os.environ['PATH']+"/usr/sbin:/sbin"
            	os.environ['CONDOR_CONFIG'] = "/etc/condor/condor_config"
	        # This 'sourcing' is done here, instead of being done in the end, to avoid situation where the user logs in into the machine before the configuration is finished.

	try:
		subprocess.call([SERVICE_cmd,'condor','stop'])
	except:
		print 'Please check if the previous Condor version is correctly installed.\n'

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
            
	    # Dynamically writing SLOT users
            CPUs_aux1 = subprocess.Popen([CAT_cmd, "/proc/cpuinfo"], stdout=subprocess.PIPE)
            CPUs_aux2 = subprocess.Popen([GREP_cmd, "processor"], stdin=CPUs_aux1.stdout, stdout=subprocess.PIPE)
            #CPUs_aux3 = subprocess.Popen(["wc -l"], shell=True, stdin=CPUs_aux2.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            CPUs_aux1.stdout.close()
            #CPUs_aux2.stdout.close()

            CPUs, cpuerr = CPUs_aux2.communicate()
	    print CPUs
	    #CPUs_aux1.wait()
	    #CPUs_aux2.wait()
            #CPUs = re.sub('\n','', CPUs)
	    	
            cid1 = subprocess.Popen([CAT_cmd, "/etc/passwd"], stdout=subprocess.PIPE)
            cid2 = subprocess.Popen([GREP_cmd, "condor:"],stdin=cid1.stdout, stdout=subprocess.PIPE)
            cid3 = subprocess.Popen([AWK_cmd, "-F:",'{print $3"."$4}'], stdin=cid2.stdout, stdout=subprocess.PIPE)
            cid1.stdout.close()
            cid2.stdout.close()
        
            CondorIDs, Err = cid3.communicate()
    
            f.write("CONDOR_IDS = "+str(CondorIDs)+'\n')

            for count in range(1,len(CPUs.splitlines())+1):
                f.write("SLOT"+str(count)+"_USER = user"+str(count)+'\n')
                os.system("/usr/sbin/useradd -m -s /sbin/nologin  user"+str(count)+" > /dev/null 2>&1\n")

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

            cid1 = subprocess.Popen([CAT_cmd, "/etc/passwd"], stdout=subprocess.PIPE)
            cid2 = subprocess.Popen([GREP_cmd, "condor:"],stdin=cid1.stdout, stdout=subprocess.PIPE)
            cid3 = subprocess.Popen([AWK_cmd, "-F:",'{print $3"."$4}'], stdin=cid2.stdout, stdout=subprocess.PIPE)
            cid1.stdout.close()
            cid2.stdout.close()

            CondorIDs, Err = cid3.communicate()

            f.write("CONDOR_IDS = "+str(CondorIDs)+'\n')

            f.write("SEC_DAEMON_AUTHENTICATION = OPTIONAL\n")
            f.write("SEC_DEFAULT_AUTHENTICATION = OPTIONAL\n")

        f.close()
        subprocess.check_call(['/etc/init.d/iptables', 'stop'])		# The iptables should be configured instead of being stopped 

	
        # Moving our config file to the right directory (erase the old config)        
        subprocess.call([RM_cmd,'-f','/etc/condor/condor_config.local'])	# Just in case
        subprocess.check_call([CP_cmd,'/root/condor_config.local','/etc/condor/'])
	subprocess.call([RM_cmd,'-f','/root/condor_config.local'])
      
	if Installation:
		subprocess.call(["/bin/ln -s /etc/condor/condor_config.local /etc/condor/config.d/condor_config.local"], shell=True)
        else:
		# Moving our config file to the right directory (overwrite the old config)
                subprocess.call([RM_cmd,'-f', '/etc/condor/condor_config.local'])
                subprocess.check_call([CP_cmd,'-f',ConfigFile,'/etc/condor/condor_config.local'])
                subprocess.call([RM_cmd,'-f', ConfigFile])

        # Starting condor
        subprocess.check_call([SERVICE_cmd,'condor','start'])

	# END
