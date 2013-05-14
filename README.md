cloud-init-cern
===============

Additional Cloud-init modules developed in order to contextualize services to executed LHC experiments jobs.

More information can be found here:
https://twiki.cern.ch/twiki/bin/view/LCG/CloudInit

*****

In this directory you can find the CloudInit modules for the installation and configuration of Ganglia, CVMFS and Condor.

These are Cloud Config modules, which means after they are correctly installed in your operating system you will be able to easily configure those three services through user-data.

You are free to download them, test them and modify them accordingly to your needs.

Here is a brief summary on what you need to do to use these modules:

1. Download the three modules to an instance where you already have the CloudInit package installed, and move them to the Python modules directory (where all of the other Cloud Config modules are): /usr/lib/python2.6/site-packages/cloudinit/CloudConfig/
2. Edit the file /etc/cloud/cloud.cfg and add these three lines to the 'cloud_config_modules' section:
		 - condor
		 - ganglia
		 - cvmfs
	1. Alternatively, you can skip steps **1** and **2** by downloading and install the RPM available in https://cern-cloudinit-modules.web.cern.ch/cern-cloudinit-modules/
3. EXTRA STEP: if you are planning to do extensive testing and/or use these modules as default I would suggest you to either snapshot the current instance or bake your own Cloud Image from scratch with these modules included.
4. Create your user-data file using the Cloud Config structure and refer to the services you want to install and configure.

You can configure several parameters for each one of the services. Here are two minimal examples of user-data files that you could use during instantiation: 

*To create a simple node*
	

	#cloud-config

	cvmfs:
	 local:
	  repositories: grid.cern.ch
	  http-proxy: DIRECT

	ganglia:
	 nodes:	
	  udpSendChannel:
	   host: yourheadnode.com
   
	condor:
	 workernode:
	  condor-host: yourcondormaster.com
	  daemon-list: MASTER, STARTD

*To create a master headnode*


	#cloud-config

	condor:
 	 master:
	  lowport: 21000
  	  highport: 24500
 
	ganglia:
 	 headnode:
	  source: '"my cluster"'


Always remember to write "#cloud-config" in the first line of your user-data file, and to respect white-spacing.


Cristóvão Cordeiro, 26/04/2013, cristovao.cordeiro@cern.ch

