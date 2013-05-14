Name: cern-cloudinit-modules
Version: 1.1
Release: 1
Summary: CERN services (cvmfs, ganglia and condor) modules for CloudInit	
Requires: cloud-init
Group: IT-SDC-OL	
License: GPL	
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
BuildArch: noarch


%description
This RPM copies the cloud config modules of cvmfs, Ganglia and Condor to its respective directory and prepares CloudInit to process those new modules. 


%pre
echo "Downloading the modules..."
wget https://raw.github.com/cinquo/cloud-init-cern/devel/cloudinit/config/cc_condor.py
wget https://raw.github.com/cinquo/cloud-init-cern/devel/cloudinit/config/cc_cvmfs.py
wget https://raw.github.com/cinquo/cloud-init-cern/devel/cloudinit/config/cc_ganglia.py

mv cc_ganglia.py /usr/lib/python2.6/site-packages/cloudinit/CloudConfig/
mv cc_cvmfs.py /usr/lib/python2.6/site-packages/cloudinit/CloudConfig/
mv cc_condor.py /usr/lib/python2.6/site-packages/cloudinit/CloudConfig/

rm cern-cloudinit-modules.tar

%build

%install

%clean
rm -rf $RPM_BUILD_ROOT

%post
echo "Adding new modules to CloudInit..."
current='cloud_config_modules:'
new='cloud_config_modules:\n - cvmfs\n - ganglia\n - condor'
sed -i.bak "s/${current}/${new}/g" /etc/cloud/cloud.cfg

echo "Installation is done. Bye!"


%files




%changelog

