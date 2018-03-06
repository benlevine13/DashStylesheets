import requests
import json
import random
import pandas as pd
import numpy as np

# need token while simulating others doesn't exist
Auth0AccessToken = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6Ik56TTVSVUUzT1VSQ1JEUXlORVUzUlVKRE1qaERRekJHTURRMU5rWXdPRE13UWtNek5ETTRNUSJ9.eyJodHRwOi8vc2NoZW1hcy5taWNyb3NvZnQuY29tL3dzLzIwMDgvMDYvaWRlbnRpdHkvY2xhaW1zL3JvbGUiOltdLCJodHRwczovL3N5c3RlbXZpc2lvbi5jb20vc3Z3aWQiOiIyOWNkYWI1OS0xMmIzLTQzNTMtOGRkYi0wYjk2YTNhNWFlZDEiLCJpc3MiOiJodHRwczovL3N5c3Zpcy5hdXRoMC5jb20vIiwic3ViIjoiZ29vZ2xlLW9hdXRoMnwxMDg5NTI0ODg0NzI2MDc1MzI0MzkiLCJhdWQiOlsid2ViYXBpIiwiaHR0cHM6Ly9zeXN2aXMuYXV0aDAuY29tL3VzZXJpbmZvIl0sImlhdCI6MTUxOTkyODM4NywiZXhwIjoxNTIxNzQyNzg3LCJhenAiOiJKYkJ4bUpIQmc2NDB6QTZWRFlyaWxMOUpjc3JhVHFuMyIsInNjb3BlIjoib3BlbmlkIGVtYWlsIn0.D-JyjyLvkMRmX5vYhSyPOPE35bXjNgKXcu7alTZmTU29sEkkJ8u-fPsACOqcRM7kJnEp-G0jcSG3p-V5WEhKE79eYI27a4If37oABbmIv94t9Ieqmvgg6JpEKf5oCuxd7XJXkn1Licmhcjb2OeM6tPxRPghh6syhE5vi1FibMeLiKTVWJIrQBjpWey6BoM3C1DyG4qApX0fHQR8PUyZcKAzLYorEFcEG5vRUi8kJFZ5Ip4WANzgGTkHuLCE8U63uWcXR5gPTKZwNxP0Lxtzcb1Xb8F0ZSiJ96K-DbFr36ilnP__nL_thFEDIBeg-kgQigDXMnXxTCD7umJ60w0wBjQ'
url = 'https://stage-api.systemvision.com/api/1.0/'
headers = {'Content-Type': 'application/json; charset=utf-8', 'Authorization': 'Bearer ' + Auth0AccessToken}


def GetAll():
    parameters = {"UserID": "29cdab59-12b3-4353-8ddb-0b96a3a5aed1"}
    response = requests.get(url + "designs", headers=headers, params=parameters)
    return response.json()


# Given JSON object design list, search for specific name to return designID and revision ID to read/write design contents + simulation
def FindDesign(designList, designName):
    for i in range(0, len(designList)):
        if 'Name' in designList[i].keys():
            if designList[i]['Name'] == designName:
                return designList[i]['DesignID'], designList[i]['LatestRevisionID']


# Input design ID and revision ID to get full JSON of a specific revision
def GetDesign(designID, revisionID):
    parameters = {"designID": designID, "revisionID": revisionID}
    response = requests.get(url + 'designs', headers=headers, params=parameters)
    return response


# Input design to create new revision ID
def CreateRevision(design):
    response = requests.post(url + 'designs', headers=headers, json=design.json())
    return response


# Get component names for a design
def GetComponents(design):
    components = design['comps']
    componentList = []
    for i in range(0, len(components)):
        componentList.append(components[i]['instName'])
    return componentList


###replace input design with this to have everything the same except propValue
def ChangeProperty(design, componentName, propName, propValue):
    tempDesign = design
    components = tempDesign['comps']
    print("Trying to change parameter")
    for i in range(0, len(components)):
        if components[i]['instName'] == componentName:
            for j in range(0, len(components[i]['instProps'])):
                if components[i]['instProps'][j]['name'] == propName:
                    components[i]['instProps'][j]['value'] = propValue
                    print(str(components[i]['instProps'][j]['name']) + " is being set to " + str(
                        components[i]['instProps'][j]['value']))
    tempDesign['comps'] = components
    return tempDesign


###Set Simulation Parameters

###PUT new design
def PutDesign(design):
    response = requests.put(url + 'designs', headers=headers, data=json.dumps(design))
    return response


# Start a simulation
def StartSimulation(designID, revisionID):
    parameters = {"designID": designID, "revisionID": revisionID}
    response = requests.post(url + 'simulations', headers=headers, params=parameters)
    return response


# get SimId of a specific simulation instance within a revision
def GetSimId(simulations, i):
    if 'simulationId' in simulations[i]['simulationResultInfo']:
        simulationId = simulations[i]['simulationResultInfo']['simulationId']
        return simulationId
    else:
        return None


# Get all SimId's for a given revision JSON object
def GetAllSimId(revision):
    simulations = revision.json()['simulationData']['simulations']
    simId = []
    for i in range(0, len(simulations)):
        simId.append(GetSimId(simulations, i))
    return simId


# Get the jobView state of a simulation
def GetSimulationState(simId):
    parameters = {"simulationID": simId}
    response = requests.get(url + 'simulations', headers=headers, params=parameters)
    return response


# Get the waveform list for a given simulation
def GetWaveformList(simId):
    parameters = {"resultId": simId}
    viewerNode = requests.get(url + 'waveforms', headers=headers, params=parameters)
    return viewerNode


# Given a waveform name, get the ID needed to retrieve waveform data
def FindWaveform(Name, outputWaveformList):
    search = 0
    while outputWaveformList[search]['Name'] != Name:
        search += 1
        if search == len(outputWaveformList):
            print("Could not find waveform")
            return
    return outputWaveformList[search]['Id']


# Get a single waveform as JSON object
def GetWaveformData(simId, waveformId, divisions=1500):
    form = {"DataRequests": [{"resultId": simId, "waveformId": waveformId, "divisions": divisions,
                              "xmin": None, "xmax": None, "includeMetadata": True}]}
    data = requests.post(url + 'waveforms', headers=headers, json=form)
    return data

#Run Simulation for the Sallen Key topology
def RunSallenKey():
    designs = GetAll()
    designID, revisionID = FindDesign(designs, 'Sallen-Key Lowpass')
    if designID and revisionID:
        print('Found design')
    design = GetDesign(designID, revisionID)
    design = CreateRevision(design)
    design = design.json()
    PutDesign(json.dumps(design))
    runner = StartSimulation(designID, revisionID)
    simId = runner.json()
    if (simId):
        print("Simulation started")
    while True:
        simData = GetSimulationState(simId)
        if simData.json()['State'] == 'COMPLETED_NORMALLY':
            break
    print("Simulation complete")
    waveformList = GetWaveformList(simId)
    outputWaveformList = waveformList.json()['Children']
    search = 0
    while outputWaveformList[search]['Name'] != "u1/vout/dbMag":
        search += 1
        if search == len(outputWaveformList):
            print("waveform not found")
            break
    data = GetWaveformData(simId, outputWaveformList[search]['Id'])
    twoVariableData = data.json()['TransferData'][0]['Data']['Data']
    dfGain = pd.DataFrame(twoVariableData)
    search = 0
    while outputWaveformList[search]['Name'] != "u1/vout/phase":
        search += 1
        if search == len(outputWaveformList):
            print("Waveform not found")
            break
    data = GetWaveformData(simId, outputWaveformList[search]['Id'])
    twoVariableData = data.json()['TransferData'][0]['Data']['Data']
    dfPhase = pd.DataFrame(twoVariableData)
    return dfGain, dfPhase
    #DCGain = df['YData'][0]
    #for i in range(0, len(df['YData'])):
    #    if df['YData'][i] + 3 < DCGain:
    #        Cutoff = df['XData'][i]
    #        break
    #return DCGain, Cutoff

#Run Simulation for the Boctor Notch topology
def RunBoctorNotch():
    designs = GetAll()
    designID, revisionID = FindDesign(designs, 'Boctor Notch Lowpass')
    if designID and revisionID:
        print('Found design')
    design = GetDesign(designID, revisionID)
    design = CreateRevision(design)
    PutDesign(design.json())
    runner = StartSimulation(designID, revisionID)
    simId = runner.json()
    if (simId):
        print("Simulation started")
    while True:
        simData = GetSimulationState(simId)
        if simData.json()['State'] == 'COMPLETED_NORMALLY':
            break
    print("Simulation complete")
    waveformList = GetWaveformList(simId)
    outputWaveformList = waveformList.json()['Children']
    search = 0
    while outputWaveformList[search]['Name'] != "u1/output/dbMag":
        search += 1
        if search == len(outputWaveformList):
            print("Waveform not found")
            break
    data = GetWaveformData(simId, outputWaveformList[search]['Id'])
    twoVariableData = data.json()['TransferData'][0]['Data']['Data']
    dfGain = pd.DataFrame(twoVariableData)
    search = 0
    while outputWaveformList[search]['Name'] != "u1/vout/phase":
        search += 1
        if search == len(outputWaveformList):
            print("Waveform not found")
            break
    data = GetWaveformData(simId, outputWaveformList[search]['Id'])
    twoVariableData = data.json()['TransferData'][0]['Data']['Data']
    dfPhase = pd.DataFrame(twoVariableData)
    return dfGain, dfPhase
    #DCGain = df['YData'][0]
    #for i in range(0, len(df['YData'])):
    #    if df['YData'][i] + 3 < DCGain:
    #        Cutoff = df['XData'][i]
    #        break
    #return DCGain, Cutoff

#Run Simulation for the Multiple Feedback topology
def RunMultipleFeedback():
    designs = GetAll()
    designID, revisionID = FindDesign(designs, 'Multiple Feedback Lowpass')
    if designID and revisionID:
        print('Found design')
    design = GetDesign(designID, revisionID)
    design = CreateRevision(design)
    design = design.json()
    PutDesign(json.dumps(design))
    runner = StartSimulation(designID, revisionID)
    simId = runner.json()
    if (simId):
        print("Simulation started")
    while True:
        simData = GetSimulationState(simId)
        if simData.json()['State'] == 'COMPLETED_NORMALLY':
            break
    print("Simulation complete")
    waveformList = GetWaveformList(simId)
    outputWaveformList = waveformList.json()['Children']
    search = 0
    while outputWaveformList[search]['Name'] != "u1/vout/dbMag":
        search += 1
        if search == len(outputWaveformList):
            print("Waveform not found")
            break
    data = GetWaveformData(simId, outputWaveformList[search]['Id'])
    twoVariableData = data.json()['TransferData'][0]['Data']['Data']
    dfGain = pd.DataFrame(twoVariableData)
    search = 0
    while outputWaveformList[search]['Name'] != "u1/vout/phase":
        search += 1
        if search == len(outputWaveformList):
            print("Waveform not found")
            break
    data = GetWaveformData(simId, outputWaveformList[search]['Id'])
    twoVariableData = data.json()['TransferData'][0]['Data']['Data']
    dfPhase = pd.DataFrame(twoVariableData)
    return dfGain, dfPhase
    #DCGain = df['YData'][0]
    #for i in range(0, len(df['YData'])):
    #    if df['YData'][i] + 3 < DCGain:
    #        Cutoff = df['XData'][i]
    #        break
    #return DCGain, Cutoff