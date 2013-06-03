Name: cern-cloudinit-modules
Version: 0
Release: 0.1pre5
Summary: CERN services (cvmfs, ganglia and condor) modules for CloudInit	
Requires: cloud-init git
Group: IT-SDC-OL	
License: GPL	
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
BuildArch: noarch


%description
This RPM copies the cloud config modules of cvmfs, Ganglia and Condor to its respective directory and prepares CloudInit to process those new modules. 


%pre
echo "Cloning the repository..."
git clone https://github.com/cinquo/cloud-init-cern.git
cd cloud-init-cern/
git checkout 0.1-pre5

echo "Copying the modules..."

cp -f cloudinit/config/* /usr/lib/python2.6/site-packages/cloudinit/CloudConfig/

%build

%install

%clean
rm -rf $RPM_BUILD_ROOT

%post
echo "Adding new modules to CloudInit..."
current='cloud_config_modules:'
files=`ls -l cloud-init-cern/cloudinit/config/ | awk {'print $9'}`
new=$current
for i in $files
do
 if [[ $i == cc_* ]]; then
  module=`echo $i | sed -e "s/cc_//g" | sed -e "s/.py//g"`
  new="$new\n - $module"
 fi
done

sed -i.bak "s/${current}/${new}/g" /etc/cloud/cloud.cfg

echo "Cleaning repository..."
cd ..
rm -rf cloud-init-cern/ 
echo "Installation is done. Bye!"


%files




%changelog

