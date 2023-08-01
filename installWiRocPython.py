#!/usr/bin/env python3
# Import hashlib library (md5 method is part of it)
import hashlib
import subprocess
import sys
import yaml
import requests

releasePackageFolderNameAndRestCollection = "WiRoc2PythonReleasePackages"
installFolderName = "WiRoc-Python-2"
serviceName = "WiRocPython"
serviceName2 = "WiRocPythonWS"
settingKeyForVersion = "WiRocPythonVersion"

# New software version
newSoftwareVersion = sys.argv[1]
newSoftwareVersion = newSoftwareVersion.lstrip('v')
print("New Software version: " + newSoftwareVersion)

# HW Version
f = open("../settings.yaml", "r")
settings = yaml.load(f, Loader=yaml.BaseLoader)
f.close()
hardwareVersionAndRevision = settings["WiRocHWVersion"]
hardwareVersionAndRevision = hardwareVersionAndRevision.strip()
print("1 Hardware Version And Revision: " + hardwareVersionAndRevision)

if hardwareVersionAndRevision == "":
    f = open("../WiRocHWVersion.txt", "r")
    hardwareVersionAndRevision = f.read()
    hardwareVersionAndRevision = hardwareVersionAndRevision.strip()
    print("2 Hardware Version And Revision: " + hardwareVersionAndRevision)
    f.close()

hardwareVersionAndRevisionArr = hardwareVersionAndRevision.split("Rev")
hardwareVersion = hardwareVersionAndRevisionArr[0].lstrip('v').lstrip('V')
hardwareRevision = hardwareVersionAndRevisionArr[1]
print("Hardware Version: " + hardwareVersion)
print("Hardware Revision: " + hardwareRevision)

# Old software version
oldSoftwareVersion = settings[settingKeyForVersion]
oldSoftwareVersion = oldSoftwareVersion.strip()
print("1 Old software version: " + oldSoftwareVersion)

if oldSoftwareVersion == "":
    f = open("../WiRocPythonVersion.txt", "r")
    oldSoftwareVersion = f.read()
    oldSoftwareVersion = oldSoftwareVersion.strip()
    print("2 Old software version: " + oldSoftwareVersion)
    f.close()


with open('../apikey.txt', 'r') as apikeyfile:
    apiKey = apikeyfile.read()
    apiKey = apiKey.strip()

print("APIKey: " + apiKey)

headers = {'X-Authorization': apiKey}
URL = "https://monitor.wiroc.se/api/v1/" + releasePackageFolderNameAndRestCollection + "?sort=versionNumber desc&hwVersion=" + hardwareVersion + "&hwRevision=" + hardwareRevision
resp = requests.get(url=URL, timeout=1, headers=headers, verify=True)
if resp.status_code == 200:
    releases = resp.json()
    print(releases)
    theReleaseArr = [release for release in releases if release['versionNumber'] == newSoftwareVersion]
    if len(theReleaseArr) > 0:
        # The release exists and is applicable to this hardwareVersion hardwareRevision
        theRelease = theReleaseArr[0]
        originalMd5Hash = theRelease['md5HashOfReleaseFile']
        print("original MD5 hash: " + originalMd5Hash)

        # Download the release to WiRocPython2Releases
        localFilePath = releasePackageFolderNameAndRestCollection + "/v" + theRelease['versionNumber'] + ".tar.gz"
        wgetRes = subprocess.run(["wget", "-O", localFilePath, "https://monitor.wiroc.se/" + releasePackageFolderNameAndRestCollection + "/v" + theRelease['versionNumber'] + ".tar.gz"])
        print(wgetRes)

        # Check MD5 hash
        # Open,close, read file and calculate MD5 on its contents
        with open(localFilePath, 'rb') as releasePackage:
            releasePackageData = releasePackage.read()
            md5OfDownloadedPackage = hashlib.md5(releasePackageData).hexdigest()
            print("calculated MD5 hash of downloaded package: " + md5OfDownloadedPackage)

        if originalMd5Hash == md5OfDownloadedPackage:
            print("MD5 hash is correct!")

            # Stop service
            serviceStop1Res = subprocess.run(["systemctl", "stop", serviceName])
            print("serviceStop1 response: " + str(serviceStop1Res.returncode))

            if serviceName2 != "":
                serviceStop2Res = subprocess.run(["systemctl", "stop", serviceName2])
                print("serviceStop2 response: " + str(serviceStop2Res.returncode))

            rmRes = subprocess.run(["rm", "-rf", installFolderName])
            print("rm response: " + str(rmRes.returncode))

            tarRes = subprocess.run(["tar", "xvfz", localFilePath, installFolderName + "-v" + newSoftwareVersion])
            print("tar response: " + str(tarRes.returncode))

            mvRes = subprocess.run(["mv", installFolderName + "-v" + newSoftwareVersion, localFilePath])
            print("mv response: " + str(mvRes.returncode))

            # Update settings.yaml with new version
            settings[settingKeyForVersion] = newSoftwareVersion
            with open('../settings.yaml', 'w') as f2:
                yaml.dump(settings, f2)  # Write a YAML representation of data to 'settings.yaml'.

            serviceStart1Res = subprocess.run(["systemctl", "start", serviceName])
            print("serviceStart1 response: " + str(serviceStart1Res.returncode))

            if serviceName2 != "":
                serviceStart2Res = subprocess.run(["systemctl", "start", serviceName2])
                print("serviceStart2 response: " + str(serviceStart2Res.returncode))


        else:
            print("MD5 hash is WRONG!")
    else:
        print("New Software Version not found, or not available for this hardware")






#useless_cat_call = subprocess.run(["cat"],
##                                  stdout=subprocess.PIPE,
#                                  text=True,
#                                  input="Hello from the other side")
#print(useless_cat_call.stdout)