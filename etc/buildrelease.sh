#!/bin/sh

##################################################################
## Generates log file, tags and build RPM for CloudInit modules ##
##################################################################

usage () {
	echo "USAGE: ./buildrelease.sh [OPTIONS]=value"
	echo -e '\nScript to tag and build a new release for the CloudInit modules.\n'
	echo -e 'OPTIONS:\n'
	echo -e '  --h\t\tHelp. Prints this output.'
	echo -e '  --user\tSpecify the username of who is running the script. The same username that will be used to mount DFS.'
	echo -e '  --tag\t\tName of the tag that will be created.'
	echo -e '  --repo_dir\tLocal directory where mounting (for DFS) shall be done.'
	echo -e '  --code_url\tURL of repository where the code is.'  
}

USER=""
TAG_VERSION=""
REPO_DIR=""
CODE_URL=""

# Check for arguments
while [ $# -ge 1 ]; do
        case $1 in
                --h ) usage
                exit 1 ;;
                --user=* ) USER=${1#*=}; shift;;
                --tag=* ) TAG_VERSION=${1#*=}; shift;;
                --repo_dir=* ) REPO_DIR=${1#*=}; shift;;
                --code_url=* ) CODE_URL=${1#*=}; shift;;
                -* ) usage
                echo "Unrecognised options will be discarded." 
		exit 1;;
                * ) break ;;
        esac
done
#----#

if [ -z "$USER" ]; then
        echo "You must specify an username. Please insert your CERN username!"
        read -p "User:" USER
fi

echo "Welcome "$USER

CURRENT_DIR=`pwd`

if [ ! -z "$CODE_URL" ]; then
	git clone $CODE_URL
	if [ $? -eq 0 ]; then
		error=$?
		echo -e '\nFailed to clone git repo. Please check if you provided a valid URL.'
		exit $error
	fi
	GIT_DIR=$CURRENT_DIR'/cloud-init-cern'
else
	GIT_DIR=${CURRENT_DIR%/*}
fi

cd $GIT_DIR

GIT_BRANCH=`git rev-parse --abbrev-ref HEAD`
if [ $GIT_BRANCH != "devel" ]; then
        echo "Attention: this script is meant to run on the devel branch. Changing..."
        git checkout devel
fi

# Creating tag
echo "The current list of existing tags is:"
git tag -l

LAST_TAG=`git describe --abbrev=0`
echo "The last tag version is "$LAST_TAG
aux=0
if [ ! -z "$TAG_VERSION" ]; then
	git show-ref --verify --quiet "refs/tags/${TAG_VERSION}"
        if [ $? -eq 0 ]; then
        	echo "The version you want already exists, please choose another or Ctrl+C to abort"
      		aux=1
	fi
fi
if [ $aux -eq 1 -o -z "$TAG_VERSION" ]; then
	while [ $aux ]
	do
        	read -p "What is the tag version that should be created?" TAG_VERSION
		git show-ref --verify --quiet "refs/tags/${TAG_VERSION}"
        	if [ $? -eq 0 ]; then
                	echo "The version you want already exists, please choose another or Ctrl+C to abort"
        	else
			break;
        	fi
	done
fi


# ChangeLog file
# git log --pretty=format:"%h - %an, %ar : %s" > FULL_LOG
echo "Writing CHANGELOG for new tag "$TAG_VERSION
echo "${TAG_VERSION} in "`date` > $GIT_DIR/CHANGELOG
git log --pretty=format:'  - %s' ${LAST_TAG}.. >> $GIT_DIR/CHANGELOG
read -p "Would you like to add/modify something in the CHANGELOG?y/n(other key)" ADD_CHANGELOG
if [ $ADD_CHANGELOG == 'y' ] || [ $ADD_CHANGELOG == 'Y' ]; then
        ${EDITOR:-vi} $GIT_DIR/CHANGELOG
fi

git add $GIT_DIR/CHANGELOG

git commit -a -s -m "$TAG_VERSION"

echo "Creating new tag: "$TAG_VERSION
git log --pretty=format:'  - %s' ${LAST_TAG}.. | git tag -a $TAG_VERSION -F -

git push --tags -f

echo "Tagging is done...Building a new RPM:"
# RPM building

SPEC_DIR=$CURRENT_DIR'/cern*.spec'	# The SPEC file must always be in the same directory as the script
if [ -f $SPEC_DIR ]; then
        echo "Current Release is "$LAST_TAG
	CURRENT_REL=$LAST_TAG
else
        echo "The SPEC file wasn't found. Make sure it is in the same folder as the script. Exiting..."
        exit 3
fi

NEW_REL=$TAG_VERSION

echo "The new release will be: "$NEW_REL

OLD_LINE='Release: '
NEW_LINE='Release: '$NEW_REL
NEW_LINE=`echo $NEW_LINE | sed -e 's/-//g'` 
 
SPEC_FILENAME=`basename $SPEC_DIR`
SPEC_FULL_FILENAME=$CURRENT_DIR'/'$SPEC_FILENAME
sed -i "s/${OLD_LINE}.*/${NEW_LINE}/g" $SPEC_FULL_FILENAME

OLD_VERSION='Version: '
NEW_VERSION='Version: '`echo ${TAG_VERSION:0:1}`
sed -i "s/${OLD_VERSION}.*/${NEW_VERSION}/g" $SPEC_FULL_FILENAME

OLD_CHECKOUT='git checkout '
NEW_CHECKOUT="git checkout ${TAG_VERSION}"
sed -i "s/${OLD_CHECKOUT}.*/${NEW_CHECKOUT}/g" $SPEC_FULL_FILENAME

# TODO : Allow RPM signing
cd $CURRENT_DIR
rpmbuild -bb $SPEC_FULL_FILENAME --define "_rpmdir ."
if [ $? -ne 0 ]; then
	error=$?
        sed -i "s/$NEW_LINE/$OLD_LINE$CURRENT_REL/g" $SPEC_FULL_FILENAME
        echo "You don't have the means to build a valid RPM."
        echo "Please check if you have rpm-build installed."
        echo "Exiting..."
        exit $error
fi

if [ ! -z "$CODE_URL" ]; then
	cp $SPEC_FILENAME $GIT_DIR/etc
fi

mv -f noarch/cern*.rpm $GIT_DIR/rpm/
rm -fr noarch/

cd $GIT_DIR/etc
git add $SPEC_FILENAME 

git rm -rf $GIT_DIR/rpm/repodata/

echo "New RPM was created. Creating repodata..."
createrepo $GIT_DIR/rpm/

echo "Ready to upload new data!"

echo "To mount you need to be root, please insert your root password below."

MOUNT_DIR='/tmp/dfs/cern.ch/'

if [ ! -z "$REPO_DIR" ]; then
	MOUNT_DIR=$REPO_DIR'/'
fi

mkdir -p $MOUNT_DIR

sudo mount -t cifs //cerndfs.cern.ch/dfs $MOUNT_DIR -o user=$USER

NEW_REL_NAME=`echo $NEW_REL | sed -e 's/-//g'`

cp -fr $GIT_DIR/rpm/repodata/ $MOUNT_DIR'Websites/c/cern-cloudinit-modules/'
cp -f $GIT_DIR/rpm/cern*$NEW_REL_NAME.noarch.rpm $MOUNT_DIR'Websites/c/cern-cloudinit-modules/'

echo "Unmounting..."
sudo umount $MOUNT_DIR

cd $GIT_DIR/rpm/
git add *
git commit -m "Adding RPM built from buildrelease script, on tag ${TAG_VERSION}"
git push -f

echo "Finished. Bye!"

exit 0
