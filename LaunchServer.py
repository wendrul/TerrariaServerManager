from googleapiclient import discovery
from httplib2 import Http
from oauth2client import file, client, tools
import json
from datetime import datetime
import os
import subprocess
import shutil
import mimetypes
from colorama import Fore, Style
from requests import get


def GetUserInfo():
    now = datetime.now()
    if (not os.path.exists('user_info.json')):
        user_name = str(input("Who are you?\n"))
        ip = get('https://api.ipify.org').text
        user_info = {
            "name": user_name,
            "lastHosted": now.strftime("%d/%m/%Y, %H:%M:%S"),
            "stopHostTime": now.strftime("%d/%m/%Y, %H:%M:%S"),
            "ip" : "{ip}".format(ip = ip)
        }
    else:
        with open('user_info.json', 'r') as openfile: 
            user_info = json.load(openfile)
        user_info['lastHosted'] = now.strftime("%d/%m/%Y, %H:%M:%S")
        user_info['stopHostTime'] = now.strftime("%d/%m/%Y, %H:%M:%S")
    with open("user_info.json", "w") as outfile: 
        outfile.write(json.dumps(user_info, indent = 4))
    datutito = ['Daniel', 'daniel', 'The210', 'th210', '210', 'datuten', 'datutito', 'tuten']
    if user_info['name'] in datutito:
        print("How is it going datutito?")
    return user_info

def GetCredentialsAndClient():
    SCOPES = 'https://www.googleapis.com/auth/drive'
    store = file.Storage('storage.json')
    creds = store.get()
    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets('client_id.json', SCOPES)
        creds = tools.run_flow(flow, store)
    DRIVE = discovery.build('drive', 'v3', http=creds.authorize(Http()))
    return (DRIVE)

def pressEnterToQuit():
    input("\nPress `ENTER` to quit...\n")
    exit()

def conflictErrorHandling(mapFile, mapFileName):
    if (len(mapFile) > 1):
        print("There seem to be multiple saves with the same name, please fix this manually")
        pressEnterToQuit()
    if (len(mapFile) == 0):
        print("Please insert a version of the save file {fileName} on the Drive Folder".format(fileName = mapFileName))
        pressEnterToQuit()

def createBackup(mapFile, user_info, DRIVE):
    print("Creating backup...")
    backupFolder = DRIVE.files().list(q = "name = 'Backup'").execute().get('files', [])
    if (len(backupFolder) == 0):
        file_metadata = {
            'name': 'Backup',
            'mimeType': 'application/vnd.google-apps.folder'
        }
        backupFolder = DRIVE.files().create(body = file_metadata).execute()
        if backupFolder:
            print("Backup folder created")
    else:
        backupFolder = backupFolder[0]
    file_metadata = {
        'name': "backup_{user}_{date}".format(user = user_info['name'], date = user_info['lastHosted']),
        'parents' : [backupFolder['id']]
    }
    copy = DRIVE.files().copy(fileId = mapFile['id'], body = file_metadata).execute()
    print ("Created a backup of the current world at %s in the Backup folder." % copy['name'])

def createLocalBackup(filename, user_info, info):
    fn = os.path.split(filename)
    backupName = '.%s%s-%s%s' % (fn[0], info, fn[1], ".wbku")
    if (os.path.exists(backupName)):
        os.remove(backupName)
    shutil.copyfile(filename, backupName)

def pullSaveFile(mapFile, DRIVE, user_info, mapFileName):
    data = DRIVE.files().get_media(fileId = mapFile['id']).execute()
    if (data):
        fn = "%s.wld" % os.path.splitext(mapFileName)[0]
        if (os.path.exists(fn)):
            createLocalBackup(fn, user_info, "OnServerLaunch")
            os.remove(fn)
        with open(fn, 'wb') as fh:
            fh.write(data)
    return

def readToken(occupiedServerToken, DRIVE, user_info):
    token = DRIVE.files().get_media(fileId = occupiedServerToken['id']).execute().decode('utf-8')
    serverToken = json.loads(token)
    print ("\nWoops! Sorry %s, %s is already hosting the server, try connecting to their IP instead! --> %s" % (user_info['name'], serverToken['name'], serverToken['ip']))
    print ("\n%s has been hosting this server since %s." % (serverToken['name'], serverToken['lastHosted']))
    print ("If you think this is an error, please contact your favorite Wendrul to fix your problems.")

def writeToken(tokenName, token):
    if (os.path.exists(tokenName)):
        os.remove(tokenName)
    with open(tokenName, "w") as outfile: 
        outfile.write(json.dumps(token, indent = 4))

def createServerRunningToken(DRIVE, user_info, serverHostToken):
    serverToken = DRIVE.files().list(q = "name = '{n}'".format(n = os.path.split(serverHostToken)[1])).execute().get('files', [])
    if (serverToken):
        readToken(serverToken[0], DRIVE, user_info)
        pressEnterToQuit()
    token = {
        "name" : user_info['name'],
        "lastHosted" : user_info['lastHosted'],
        "ip" : user_info['ip']
    }
    writeToken(serverHostToken, token)
    file_metadata = {'name': os.path.split(serverHostToken)[1]}
    tokenId = DRIVE.files().create(body=file_metadata, media_body=serverHostToken, fields='id').execute()
    os.remove(serverHostToken)
    ##todo create server token so that only 1 host is allowed at a time
    return tokenId['id']

def eraseToken(DRIVE, serverHostToken, tokenId):
    deletion = DRIVE.files().delete(fileId = tokenId).execute()
    print("Succesfully erased token")

def pushNewSaveFile(DRIVE, mapFileName, mapFile):
    mimetypes.add_type("application/octet-stream", ".wld")
    file_metadata = {'name': os.path.split(mapFileName)[1], "mimeType" : "application/octet-stream", "parents" : mapFile['parents']}
    DRIVE.files().delete(fileId = mapFile['id']).execute()
    upload = DRIVE.files().create(body=file_metadata, media_body=mapFileName, fields='id').execute()
    print("Deleted old save file")
    print("Succesfully saved new map")
    return upload

def EnterToContinue(str):
    print(str)
    input()

def addLog(DRIVE, user_info):
    logFolder = DRIVE.files().list(q = "name = 'Logs'").execute().get('files', [])
    if (len(logFolder) == 0):
        file_metadata = {
            'name': 'Logs',
            'mimeType': 'application/vnd.google-apps.folder'
        }
        logFolder = DRIVE.files().create(body = file_metadata).execute()
        if logFolder:
            print("Backup folder created")
    else:
        logFolder = logFolder[0]
    file_metadata = {
        'name': "{name}.json".format(name = user_info['name']),
        'parents' : [logFolder['id']]
    }
    oldLog = DRIVE.files().list(q = "name = '{name}.json'".format(name = user_info['name'])).execute().get('files', [])
    if oldLog:
        DRIVE.files().delete(fileId = oldLog[0]['id']).execute()
    DRIVE.files().create(body = file_metadata, media_body = "user_info.json", fields = 'id').execute()
    print ("Created a log for this session")

def main():
    print("Getting credentials...")
    DRIVE = GetCredentialsAndClient()
    print("Acquired API Client")
    user_info = GetUserInfo()
    with open("path.txt", 'r') as f:
        mapFileName = f.readlines()[0]
    if (not os.path.exists(mapFileName)):
        print("The file does not exist in your computer")
        print("Continuing will write a file `%s` into `%s`, would you like to continue? (y/n)" % (os.path.split(mapFileName)[1], os.path.split(mapFileName)[0]))
        ans = input()
        if (not(ans == 'y' or ans == 'Y')):
            pressEnterToQuit()
    print("Seeking save file...")
    mapFile = DRIVE.files().list(q = "name = '{fileName}'".format(fileName = os.path.split(mapFileName)[1]), fields = '*').execute().get('files', [])
    print("Found file!")
    conflictErrorHandling(mapFile, mapFileName)
    pullSaveFile(mapFile[0], DRIVE, user_info, mapFileName)
    print("Downloaded save file succesfully")
    serverTokenFileName = "server_hosting_token.json" 
    print("Creating token for this session")
    tokenId = createServerRunningToken(DRIVE, user_info, serverTokenFileName)
    createBackup(mapFile[0], user_info, DRIVE)
    print ("\nStarting up server on ip: %s\n" % user_info['ip'])
    subprocess.call("TerrariaServer.exe")
    print ("\nServer shutdown succesfully, uploading new world (DO NOT CLOSE yet, plz)")
    now = datetime.now()
    user_info['stopHostTime'] = now.strftime("%d/%m/%Y, %H:%M:%S")
    newSave = pushNewSaveFile(DRIVE, mapFileName, mapFile[0])
    EnterToContinue("after pushnew")
    addLog(DRIVE, user_info)
    EnterToContinue("afteradd log")
    eraseToken(DRIVE, serverTokenFileName, tokenId)
    createLocalBackup("%s.wld" % os.path.splitext(mapFileName)[0], user_info, "OnServerClose")
    createBackup(newSave, user_info, DRIVE)
    pressEnterToQuit()

main()