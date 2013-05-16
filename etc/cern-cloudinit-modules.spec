Name: cern-cloudinit-modules
Version: 1.1
Release: 2
Summary: CERN services (cvmfs, ganglia and condor) modules for CloudInit	
Requires: cloud-init
Group: IT-SDC-OL	
License: GPL	
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
BuildArch: noarch


%description
This RPM copies the cloud config modules of cvmfs, Ganglia and Condor to its respective directory and prepares CloudInit to process those new modules. 


%pre
echo "Cloning the repository..."
git clone git@github.com:cinquo/cloud-init-cern.git
cd cloud-init-cern/
git checkout 0.1-pre1

echo "Copying the modules..."
# wget https://raw.github.com/cinquo/cloud-init-cern/devel/cloudinit/config/cc_condor.py
# wget https://raw.github.com/cinquo/cloud-init-cern/devel/cloudinit/config/cc_cvmfs.py
# wget https://raw.github.com/cinquo/cloud-init-cern/devel/cloudinit/config/cc_ganglia.py

cp cloudinit/config/cc_ganglia.py /usr/lib/python2.6/site-packages/cloudinit/CloudConfig/
cp cloudinit/config/cc_cvmfs.py /usr/lib/python2.6/site-packages/cloudinit/CloudConfig/
cp cloudinit/config/cc_condor.py /usr/lib/python2.6/site-packages/cloudinit/CloudConfig/

%build

%install

%clean
rm -rf $RPM_BUILD_ROOT

%post
echo "Adding new modules to CloudInit..."
current='cloud_config_modules:'
new='cloud_config_modules:\n - cvmfs\n - ganglia\n - condor'
sed -i.bak "s/${current}/${new}/g" /etc/cloud/cloud.cfg

echo "Cleaning repository..."
cd ..
rm -rf cloud-init-cern/ 
echo "Installation is done. Bye!"


%files




%changelog

