#!/usr/bin/env python3
# Should be run in the chip home directory
import hashlib
import subprocess
import sys
import yaml
import requests
import time
import os
import os.path

releasePackageFolderName = "WiRocPython2ReleasePackages"
releaseRestCollection = "WiRocPython2Releases"
installFolderName = "WiRoc-Python-2"
serviceName = "WiRocPython"
serviceName2 = "WiRocPythonWS"
settingKeyForVersion = "WiRocPythonVersion"
releaseUpgradeScriptRestCollection = "WiRocPython2ReleaseUpgradeScripts"
versionTextFileName = "WiRocPythonVersion.txt"

# New software version
newSoftwareVersion = sys.argv[1]
newSoftwareVersion = newSoftwareVersion.lstrip('v')
print("New Software version: " + newSoftwareVersion)

# NEW or UPGRADE
installMode = "UPGRADE"
if len(sys.argv) > 2: 
    installMode = sys.argv[2]
    print("Install mode: " + installMode)
    
# HW Version
f = open("settings.yaml", "r")
settings = yaml.load(f, Loader=yaml.BaseLoader)
f.close()
hardwareVersionAndRevision = ""
if "WiRocHWVersion" in settings:
    hardwareVersionAndRevision = settings["WiRocHWVersion"]
    hardwareVersionAndRevision = hardwareVersionAndRevision.strip()
    print("1 Hardware Version And Revision: " + hardwareVersionAndRevision)

if hardwareVersionAndRevision == "":
    with open("WiRocHWVersion.txt", "r") as f:
        hardwareVersionAndRevision = f.read()
    hardwareVersionAndRevision = hardwareVersionAndRevision.strip()
    print("2 Hardware Version And Revision: " + hardwareVersionAndRevision)
    settings["WiRocHWVersion"] = hardwareVersionAndRevision

hardwareVersionAndRevisionArr = hardwareVersionAndRevision.split("Rev")
hardwareVersion = hardwareVersionAndRevisionArr[0].lstrip('v').lstrip('V')
hardwareRevision = hardwareVersionAndRevisionArr[1]
print("Hardware Version: " + hardwareVersion)
print("Hardware Revision: " + hardwareRevision)

# Old software version
oldSoftwareVersion = ""
if settingKeyForVersion in settings:
    oldSoftwareVersion = settings[settingKeyForVersion]
    oldSoftwareVersion = oldSoftwareVersion.strip()
    print("1 Old software version: " + oldSoftwareVersion)

if oldSoftwareVersion == "":
    with open(versionTextFileName, "r") as f:
        oldSoftwareVersion = f.read()
    oldSoftwareVersion = oldSoftwareVersion.strip()
    print("2 Old software version: " + oldSoftwareVersion)
    settings[settingKeyForVersion] = oldSoftwareVersion


with open('apikey.txt', 'r') as apikeyfile:
    apiKey = apikeyfile.read()
    apiKey = apiKey.strip()

print("APIKey: " + apiKey)

headers = {'X-Authorization': apiKey}
URL = "https://monitor.wiroc.se/api/v1/" + releaseRestCollection + "?sort=versionNumber desc&hwVersion=" + hardwareVersion + "&hwRevision=" + hardwareRevision
resp = requests.get(url=URL, timeout=2, headers=headers, verify=True)
if resp.status_code == 200:
    releases = resp.json()
    print(releases)
    theReleaseArr = [release for release in releases if release['versionNumber'] == newSoftwareVersion]
    if len(theReleaseArr) > 0:
        # The release exists and is applicable to this hardwareVersion hardwareRevision
        theRelease = theReleaseArr[0]
        originalMd5Hash = theRelease['md5HashOfReleaseFile']
        print("original MD5 hash: " + originalMd5Hash)

        # Download the release
        if not os.path.exists(releasePackageFolderName):
            os.makedirs(releasePackageFolderName)

        localFilePath = releasePackageFolderName + "/v" + theRelease['versionNumber'] + ".tar.gz"
        wgetRes = subprocess.run(["wget", "-O", localFilePath, "https://monitor.wiroc.se/" + releasePackageFolderName + "/v" + theRelease['versionNumber'] + ".tar.gz"])
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
            if serviceStop1Res.returncode != 0:
                print("Ignore, service might just not be loaded yet")

            if serviceName2 != "":
                serviceStop2Res = subprocess.run(["systemctl", "stop", serviceName2])
                print("serviceStop2 response: " + str(serviceStop2Res.returncode))
                if serviceStop2Res.returncode != 0:
                    print("Ignore, service might just not be loaded yet")

            rmRes = subprocess.run(["rm", "-rf", installFolderName])
            print("rm response: " + str(rmRes.returncode))
            if rmRes.returncode != 0:
                exit(rmRes.rmRes)

            tarRes = subprocess.run(["tar", "xvfz", localFilePath, installFolderName + '-' + newSoftwareVersion])
            print("tar response: " + str(tarRes.returncode))
            if tarRes.returncode != 0:
                exit(tarRes.returncode)

            mvRes = subprocess.run(["mv", installFolderName + '-' + newSoftwareVersion, installFolderName])
            print("mv response: " + str(mvRes.returncode))
            if mvRes.returncode != 0:
                exit(mvRes.returncode)

            # Get and run all required upgrade scripts
            URLScripts = "https://monitor.wiroc.se/api/v1/" + releaseUpgradeScriptRestCollection + "?sort=versionNumber asc&limitFromVersion=" + oldSoftwareVersion + "&limitToVersion=" + newSoftwareVersion
            print("URLScripts: " + URLScripts)
            scriptsResp = requests.get(url=URLScripts, timeout=2, headers=headers, verify=True)
            if scriptsResp.status_code == 200:

                timestr = time.strftime("%Y%m%d-%H%M%S")
                localScriptFolderPath = releasePackageFolderName + "/" + timestr
                mkdirRes = subprocess.run(["mkdir", localScriptFolderPath])
                print("mkdir response: " + str(mkdirRes.returncode))
                if mkdirRes.returncode != 0:
                    exit(mkdirRes.returncode)

                # Create script files
                scriptFilePathsInOrder = []
                scriptsArr = scriptsResp.json()
                print("script json: " + str(scriptsArr))
                for scriptObj in scriptsArr:
                    scriptText = scriptObj['scriptText']
                    scriptFileName = localScriptFolderPath + '/v' + scriptObj['versionNumber'] + '-' + str(scriptObj['id'])
                    scriptFilePathsInOrder.append(scriptFileName)
                    with open(scriptFileName, 'w') as scriptFile:
                        scriptFile.write(scriptText)
                    ChModRes = subprocess.run(["chmod", "ugo+x", scriptFileName])
                    print("chmod response: " + str(ChModRes.returncode))
                    if ChModRes.returncode != 0:
                        exit(ChModRes.returncode)

                for scriptFilePath in scriptFilePathsInOrder:
                    scriptRes = subprocess.run([scriptFilePath])
                    print("script response: " + str(scriptRes.returncode))
                    if scriptRes.returncode != 0:
                        exit(scriptRes.returncode)

                # Update settings.yaml with new version
                settings[settingKeyForVersion] = newSoftwareVersion
                with open('settings.yaml', 'w') as f2:
                    yaml.dump(settings, f2)  # Write a YAML representation of data to 'settings.yaml'.

                if installMode == "UPGRADE":
                    serviceStart1Res = subprocess.run(["systemctl", "start", serviceName])
                    print("serviceStart1 response: " + str(serviceStart1Res.returncode))
                    if serviceStart1Res.returncode != 0:
                        exit(serviceStart1Res.returncode)

                    if serviceName2 != "":
                        serviceStart2Res = subprocess.run(["systemctl", "start", serviceName2])
                        print("serviceStart2 response: " + str(serviceStart2Res.returncode))
                        if serviceStart2Res.returncode != 0:
                            exit(serviceStart2Res.returncode)

        else:
            print("MD5 hash is WRONG!")
    else:
        print("New Software Version not found, or not available for this hardware")

