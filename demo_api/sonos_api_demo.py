#!/usr/bin/env python3
"""
Sonos, Inc. Sonos Port REST API Demo

Auto-generated FastAPI demonstration for Sonos, Inc. Sonos Port control.
This API provides REST endpoints for 196 UPnP actions.
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional
import aiohttp
import json

# FastAPI app
app = FastAPI(
    title="Sonos, Inc. Sonos Port Demo API",
    description="Demo REST API for Sonos, Inc. Sonos Port UPnP device control",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Device configuration
DEVICE_HOST = None
DEVICE_PORT = None

@app.get("/")
async def root():
    """API root with overview."""
    return {
        "api": "Sonos, Inc. Sonos Port Demo API",
        "total_actions": 196,
        "services": 15,
        "status": "ready",
        "device_connected": DEVICE_HOST is not None,
        "docs": "/docs"
    }

@app.post("/init")
async def initialize_device(host: str = Query(...), port: int = Query(default=1400)):
    """Initialize connection to the UPnP device."""
    global DEVICE_HOST, DEVICE_PORT
    
    DEVICE_HOST = host
    DEVICE_PORT = port
    
    return {
        "status": "success", 
        "message": f"Connected to {host}:{port}",
        "device": "Sonos, Inc. Sonos Port"
    }

@app.get("/actions")
async def list_all_actions():
    """List all available UPnP actions by service."""
    actions_by_service = {}
    
    actions_by_service["alarmclock"] = {
        "SetFormat": {
            "complexity": "🟡 Medium",
            "category": "configuration",
            "arguments_required": 2
        },
        "GetFormat": {
            "complexity": "🟡 Medium",
            "category": "information_retrieval",
            "arguments_required": 0
        },
        "SetTimeZone": {
            "complexity": "🟡 Medium",
            "category": "configuration",
            "arguments_required": 2
        },
        "GetTimeZone": {
            "complexity": "🟡 Medium",
            "category": "information_retrieval",
            "arguments_required": 0
        },
        "GetTimeZoneAndRule": {
            "complexity": "🔴 Complex",
            "category": "information_retrieval",
            "arguments_required": 0
        },
        "GetTimeZoneRule": {
            "complexity": "🟡 Medium",
            "category": "information_retrieval",
            "arguments_required": 1
        },
        "SetTimeServer": {
            "complexity": "🟡 Medium",
            "category": "configuration",
            "arguments_required": 1
        },
        "GetTimeServer": {
            "complexity": "🟡 Medium",
            "category": "information_retrieval",
            "arguments_required": 0
        },
        "SetTimeNow": {
            "complexity": "🟡 Medium",
            "category": "configuration",
            "arguments_required": 2
        },
        "GetHouseholdTimeAtStamp": {
            "complexity": "🟡 Medium",
            "category": "information_retrieval",
            "arguments_required": 1
        },
        "GetTimeNow": {
            "complexity": "🔴 Complex",
            "category": "information_retrieval",
            "arguments_required": 0
        },
        "CreateAlarm": {
            "complexity": "🔴 Complex",
            "category": "other",
            "arguments_required": 10
        },
        "UpdateAlarm": {
            "complexity": "🔴 Complex",
            "category": "configuration",
            "arguments_required": 11
        },
        "DestroyAlarm": {
            "complexity": "🟡 Medium",
            "category": "other",
            "arguments_required": 1
        },
        "ListAlarms": {
            "complexity": "🟡 Medium",
            "category": "information_retrieval",
            "arguments_required": 0
        },
        "SetDailyIndexRefreshTime": {
            "complexity": "🟡 Medium",
            "category": "configuration",
            "arguments_required": 1
        },
        "GetDailyIndexRefreshTime": {
            "complexity": "🟡 Medium",
            "category": "information_retrieval",
            "arguments_required": 0
        },
    }
    actions_by_service["musicservices"] = {
        "GetSessionId": {
            "complexity": "🔴 Complex",
            "category": "information_retrieval",
            "arguments_required": 2
        },
        "ListAvailableServices": {
            "complexity": "🔴 Complex",
            "category": "information_retrieval",
            "arguments_required": 0
        },
        "UpdateAvailableServices": {
            "complexity": "🟢 Easy",
            "category": "configuration",
            "arguments_required": 0
        },
    }
    actions_by_service["audioin"] = {
        "StartTransmissionToGroup": {
            "complexity": "🔴 Complex",
            "category": "other",
            "arguments_required": 2
        },
        "StopTransmissionToGroup": {
            "complexity": "🟡 Medium",
            "category": "media_control",
            "arguments_required": 1
        },
        "SetAudioInputAttributes": {
            "complexity": "🟡 Medium",
            "category": "configuration",
            "arguments_required": 2
        },
        "GetAudioInputAttributes": {
            "complexity": "🟡 Medium",
            "category": "information_retrieval",
            "arguments_required": 0
        },
        "SetLineInLevel": {
            "complexity": "🟡 Medium",
            "category": "configuration",
            "arguments_required": 2
        },
        "GetLineInLevel": {
            "complexity": "🟡 Medium",
            "category": "information_retrieval",
            "arguments_required": 0
        },
    }
    actions_by_service["deviceproperties"] = {
        "SetLEDState": {
            "complexity": "🟡 Medium",
            "category": "configuration",
            "arguments_required": 1
        },
        "GetLEDState": {
            "complexity": "🟡 Medium",
            "category": "information_retrieval",
            "arguments_required": 0
        },
        "AddBondedZones": {
            "complexity": "🟡 Medium",
            "category": "configuration",
            "arguments_required": 1
        },
        "RemoveBondedZones": {
            "complexity": "🟡 Medium",
            "category": "configuration",
            "arguments_required": 2
        },
        "CreateStereoPair": {
            "complexity": "🟡 Medium",
            "category": "other",
            "arguments_required": 1
        },
        "SeparateStereoPair": {
            "complexity": "🟡 Medium",
            "category": "other",
            "arguments_required": 1
        },
        "SetZoneAttributes": {
            "complexity": "🔴 Complex",
            "category": "configuration",
            "arguments_required": 4
        },
        "GetZoneAttributes": {
            "complexity": "🔴 Complex",
            "category": "information_retrieval",
            "arguments_required": 0
        },
        "GetHouseholdID": {
            "complexity": "🟡 Medium",
            "category": "information_retrieval",
            "arguments_required": 0
        },
        "GetZoneInfo": {
            "complexity": "🔴 Complex",
            "category": "information_retrieval",
            "arguments_required": 0
        },
        "SetAutoplayLinkedZones": {
            "complexity": "🟡 Medium",
            "category": "media_control",
            "arguments_required": 2
        },
        "GetAutoplayLinkedZones": {
            "complexity": "🟡 Medium",
            "category": "media_control",
            "arguments_required": 1
        },
        "SetAutoplayRoomUUID": {
            "complexity": "🟡 Medium",
            "category": "media_control",
            "arguments_required": 2
        },
        "GetAutoplayRoomUUID": {
            "complexity": "🟡 Medium",
            "category": "media_control",
            "arguments_required": 1
        },
        "SetAutoplayVolume": {
            "complexity": "🟡 Medium",
            "category": "media_control",
            "arguments_required": 2
        },
        "GetAutoplayVolume": {
            "complexity": "🟡 Medium",
            "category": "media_control",
            "arguments_required": 1
        },
        "SetUseAutoplayVolume": {
            "complexity": "🟡 Medium",
            "category": "media_control",
            "arguments_required": 2
        },
        "GetUseAutoplayVolume": {
            "complexity": "🟡 Medium",
            "category": "media_control",
            "arguments_required": 1
        },
        "AddHTSatellite": {
            "complexity": "🟡 Medium",
            "category": "configuration",
            "arguments_required": 1
        },
        "RemoveHTSatellite": {
            "complexity": "🟡 Medium",
            "category": "configuration",
            "arguments_required": 1
        },
        "EnterConfigMode": {
            "complexity": "🔴 Complex",
            "category": "configuration",
            "arguments_required": 2
        },
        "ExitConfigMode": {
            "complexity": "🟡 Medium",
            "category": "configuration",
            "arguments_required": 1
        },
        "GetButtonState": {
            "complexity": "🟡 Medium",
            "category": "information_retrieval",
            "arguments_required": 0
        },
        "SetButtonLockState": {
            "complexity": "🟡 Medium",
            "category": "configuration",
            "arguments_required": 1
        },
        "GetButtonLockState": {
            "complexity": "🟡 Medium",
            "category": "information_retrieval",
            "arguments_required": 0
        },
        "RoomDetectionStartChirping": {
            "complexity": "🔴 Complex",
            "category": "other",
            "arguments_required": 3
        },
        "RoomDetectionStopChirping": {
            "complexity": "🟡 Medium",
            "category": "media_control",
            "arguments_required": 1
        },
    }
    actions_by_service["systemproperties"] = {
        "SetString": {
            "complexity": "🟡 Medium",
            "category": "configuration",
            "arguments_required": 2
        },
        "GetString": {
            "complexity": "🟡 Medium",
            "category": "information_retrieval",
            "arguments_required": 1
        },
        "Remove": {
            "complexity": "🟡 Medium",
            "category": "configuration",
            "arguments_required": 1
        },
        "GetWebCode": {
            "complexity": "🟡 Medium",
            "category": "information_retrieval",
            "arguments_required": 1
        },
        "ProvisionCredentialedTrialAccountX": {
            "complexity": "🔴 Complex",
            "category": "other",
            "arguments_required": 3
        },
        "AddAccountX": {
            "complexity": "🔴 Complex",
            "category": "configuration",
            "arguments_required": 3
        },
        "AddOAuthAccountX": {
            "complexity": "🔴 Complex",
            "category": "configuration",
            "arguments_required": 8
        },
        "RemoveAccount": {
            "complexity": "🟡 Medium",
            "category": "configuration",
            "arguments_required": 2
        },
        "EditAccountPasswordX": {
            "complexity": "🔴 Complex",
            "category": "security",
            "arguments_required": 3
        },
        "SetAccountNicknameX": {
            "complexity": "🟡 Medium",
            "category": "configuration",
            "arguments_required": 2
        },
        "RefreshAccountCredentialsX": {
            "complexity": "🔴 Complex",
            "category": "other",
            "arguments_required": 4
        },
        "EditAccountMd": {
            "complexity": "🔴 Complex",
            "category": "other",
            "arguments_required": 3
        },
        "DoPostUpdateTasks": {
            "complexity": "🟢 Easy",
            "category": "configuration",
            "arguments_required": 0
        },
        "ResetThirdPartyCredentials": {
            "complexity": "🟢 Easy",
            "category": "configuration",
            "arguments_required": 0
        },
        "EnableRDM": {
            "complexity": "🟡 Medium",
            "category": "other",
            "arguments_required": 1
        },
        "GetRDM": {
            "complexity": "🟡 Medium",
            "category": "information_retrieval",
            "arguments_required": 0
        },
        "ReplaceAccountX": {
            "complexity": "🔴 Complex",
            "category": "other",
            "arguments_required": 6
        },
    }
    actions_by_service["zonegrouptopology"] = {
        "CheckForUpdate": {
            "complexity": "🔴 Complex",
            "category": "configuration",
            "arguments_required": 3
        },
        "BeginSoftwareUpdate": {
            "complexity": "🔴 Complex",
            "category": "configuration",
            "arguments_required": 3
        },
        "ReportUnresponsiveDevice": {
            "complexity": "🟡 Medium",
            "category": "other",
            "arguments_required": 2
        },
        "ReportAlarmStartedRunning": {
            "complexity": "🟢 Easy",
            "category": "other",
            "arguments_required": 0
        },
        "SubmitDiagnostics": {
            "complexity": "🔴 Complex",
            "category": "other",
            "arguments_required": 2
        },
        "RegisterMobileDevice": {
            "complexity": "🔴 Complex",
            "category": "other",
            "arguments_required": 3
        },
        "GetZoneGroupAttributes": {
            "complexity": "🔴 Complex",
            "category": "information_retrieval",
            "arguments_required": 0
        },
        "GetZoneGroupState": {
            "complexity": "🟡 Medium",
            "category": "information_retrieval",
            "arguments_required": 0
        },
    }
    actions_by_service["groupmanagement"] = {
        "AddMember": {
            "complexity": "🔴 Complex",
            "category": "configuration",
            "arguments_required": 2
        },
        "RemoveMember": {
            "complexity": "🟡 Medium",
            "category": "configuration",
            "arguments_required": 1
        },
        "ReportTrackBufferingResult": {
            "complexity": "🟡 Medium",
            "category": "other",
            "arguments_required": 2
        },
        "SetSourceAreaIds": {
            "complexity": "🟡 Medium",
            "category": "configuration",
            "arguments_required": 1
        },
    }
    actions_by_service["qplay"] = {
        "QPlayAuth": {
            "complexity": "🔴 Complex",
            "category": "media_control",
            "arguments_required": 1
        },
    }
    actions_by_service["contentdirectory"] = {
        "GetSearchCapabilities": {
            "complexity": "🟡 Medium",
            "category": "information_retrieval",
            "arguments_required": 0
        },
        "GetSortCapabilities": {
            "complexity": "🟡 Medium",
            "category": "information_retrieval",
            "arguments_required": 0
        },
        "GetSystemUpdateID": {
            "complexity": "🟡 Medium",
            "category": "information_retrieval",
            "arguments_required": 0
        },
        "GetAlbumArtistDisplayOption": {
            "complexity": "🟡 Medium",
            "category": "media_control",
            "arguments_required": 0
        },
        "GetLastIndexChange": {
            "complexity": "🟡 Medium",
            "category": "information_retrieval",
            "arguments_required": 0
        },
        "Browse": {
            "complexity": "🔴 Complex",
            "category": "other",
            "arguments_required": 6
        },
        "FindPrefix": {
            "complexity": "🔴 Complex",
            "category": "other",
            "arguments_required": 2
        },
        "GetAllPrefixLocations": {
            "complexity": "🔴 Complex",
            "category": "information_retrieval",
            "arguments_required": 1
        },
        "CreateObject": {
            "complexity": "🔴 Complex",
            "category": "other",
            "arguments_required": 2
        },
        "UpdateObject": {
            "complexity": "🔴 Complex",
            "category": "configuration",
            "arguments_required": 3
        },
        "DestroyObject": {
            "complexity": "🟡 Medium",
            "category": "other",
            "arguments_required": 1
        },
        "RefreshShareIndex": {
            "complexity": "🟡 Medium",
            "category": "other",
            "arguments_required": 1
        },
        "RequestResort": {
            "complexity": "🟡 Medium",
            "category": "other",
            "arguments_required": 1
        },
        "GetShareIndexInProgress": {
            "complexity": "🟡 Medium",
            "category": "information_retrieval",
            "arguments_required": 0
        },
        "GetBrowseable": {
            "complexity": "🟡 Medium",
            "category": "information_retrieval",
            "arguments_required": 0
        },
        "SetBrowseable": {
            "complexity": "🟡 Medium",
            "category": "configuration",
            "arguments_required": 1
        },
    }
    actions_by_service["connectionmanager"] = {
        "GetProtocolInfo": {
            "complexity": "🟡 Medium",
            "category": "information_retrieval",
            "arguments_required": 0
        },
        "GetCurrentConnectionIDs": {
            "complexity": "🟡 Medium",
            "category": "information_retrieval",
            "arguments_required": 0
        },
        "GetCurrentConnectionInfo": {
            "complexity": "🔴 Complex",
            "category": "information_retrieval",
            "arguments_required": 1
        },
    }
    actions_by_service["renderingcontrol"] = {
        "GetMute": {
            "complexity": "🔴 Complex",
            "category": "volume_control",
            "arguments_required": 2
        },
        "SetMute": {
            "complexity": "🔴 Complex",
            "category": "volume_control",
            "arguments_required": 3
        },
        "ResetBasicEQ": {
            "complexity": "🔴 Complex",
            "category": "configuration",
            "arguments_required": 1
        },
        "ResetExtEQ": {
            "complexity": "🟡 Medium",
            "category": "configuration",
            "arguments_required": 2
        },
        "GetVolume": {
            "complexity": "🔴 Complex",
            "category": "volume_control",
            "arguments_required": 2
        },
        "SetVolume": {
            "complexity": "🔴 Complex",
            "category": "volume_control",
            "arguments_required": 3
        },
        "SetRelativeVolume": {
            "complexity": "🔴 Complex",
            "category": "volume_control",
            "arguments_required": 3
        },
        "GetVolumeDB": {
            "complexity": "🔴 Complex",
            "category": "volume_control",
            "arguments_required": 2
        },
        "SetVolumeDB": {
            "complexity": "🔴 Complex",
            "category": "volume_control",
            "arguments_required": 3
        },
        "GetVolumeDBRange": {
            "complexity": "🔴 Complex",
            "category": "volume_control",
            "arguments_required": 2
        },
        "GetBass": {
            "complexity": "🟡 Medium",
            "category": "volume_control",
            "arguments_required": 1
        },
        "SetBass": {
            "complexity": "🟡 Medium",
            "category": "volume_control",
            "arguments_required": 2
        },
        "GetTreble": {
            "complexity": "🟡 Medium",
            "category": "volume_control",
            "arguments_required": 1
        },
        "SetTreble": {
            "complexity": "🟡 Medium",
            "category": "volume_control",
            "arguments_required": 2
        },
        "GetEQ": {
            "complexity": "🔴 Complex",
            "category": "information_retrieval",
            "arguments_required": 2
        },
        "SetEQ": {
            "complexity": "🔴 Complex",
            "category": "configuration",
            "arguments_required": 3
        },
        "GetLoudness": {
            "complexity": "🔴 Complex",
            "category": "information_retrieval",
            "arguments_required": 2
        },
        "SetLoudness": {
            "complexity": "🔴 Complex",
            "category": "configuration",
            "arguments_required": 3
        },
        "GetSupportsOutputFixed": {
            "complexity": "🟡 Medium",
            "category": "information_retrieval",
            "arguments_required": 1
        },
        "GetOutputFixed": {
            "complexity": "🟡 Medium",
            "category": "information_retrieval",
            "arguments_required": 1
        },
        "SetOutputFixed": {
            "complexity": "🟡 Medium",
            "category": "configuration",
            "arguments_required": 2
        },
        "GetHeadphoneConnected": {
            "complexity": "🟡 Medium",
            "category": "information_retrieval",
            "arguments_required": 1
        },
        "RampToVolume": {
            "complexity": "🔴 Complex",
            "category": "volume_control",
            "arguments_required": 6
        },
        "RestoreVolumePriorToRamp": {
            "complexity": "🟡 Medium",
            "category": "volume_control",
            "arguments_required": 2
        },
        "SetChannelMap": {
            "complexity": "🟡 Medium",
            "category": "configuration",
            "arguments_required": 2
        },
        "GetRoomCalibrationStatus": {
            "complexity": "🔴 Complex",
            "category": "information_retrieval",
            "arguments_required": 1
        },
        "SetRoomCalibrationStatus": {
            "complexity": "🟡 Medium",
            "category": "information_retrieval",
            "arguments_required": 2
        },
    }
    actions_by_service["avtransport"] = {
        "SetAVTransportURI": {
            "complexity": "🔴 Complex",
            "category": "configuration",
            "arguments_required": 3
        },
        "SetNextAVTransportURI": {
            "complexity": "🔴 Complex",
            "category": "media_control",
            "arguments_required": 3
        },
        "AddURIToQueue": {
            "complexity": "🔴 Complex",
            "category": "configuration",
            "arguments_required": 5
        },
        "AddMultipleURIsToQueue": {
            "complexity": "🔴 Complex",
            "category": "configuration",
            "arguments_required": 9
        },
        "ReorderTracksInQueue": {
            "complexity": "🔴 Complex",
            "category": "other",
            "arguments_required": 5
        },
        "RemoveTrackFromQueue": {
            "complexity": "🔴 Complex",
            "category": "configuration",
            "arguments_required": 3
        },
        "RemoveTrackRangeFromQueue": {
            "complexity": "🔴 Complex",
            "category": "configuration",
            "arguments_required": 4
        },
        "RemoveAllTracksFromQueue": {
            "complexity": "🟡 Medium",
            "category": "configuration",
            "arguments_required": 1
        },
        "SaveQueue": {
            "complexity": "🔴 Complex",
            "category": "other",
            "arguments_required": 3
        },
        "BackupQueue": {
            "complexity": "🟡 Medium",
            "category": "other",
            "arguments_required": 1
        },
        "CreateSavedQueue": {
            "complexity": "🔴 Complex",
            "category": "other",
            "arguments_required": 4
        },
        "AddURIToSavedQueue": {
            "complexity": "🔴 Complex",
            "category": "configuration",
            "arguments_required": 6
        },
        "ReorderTracksInSavedQueue": {
            "complexity": "🔴 Complex",
            "category": "other",
            "arguments_required": 5
        },
        "GetMediaInfo": {
            "complexity": "🔴 Complex",
            "category": "information_retrieval",
            "arguments_required": 1
        },
        "GetTransportInfo": {
            "complexity": "🔴 Complex",
            "category": "information_retrieval",
            "arguments_required": 1
        },
        "GetPositionInfo": {
            "complexity": "🔴 Complex",
            "category": "information_retrieval",
            "arguments_required": 1
        },
        "GetDeviceCapabilities": {
            "complexity": "🔴 Complex",
            "category": "information_retrieval",
            "arguments_required": 1
        },
        "GetTransportSettings": {
            "complexity": "🔴 Complex",
            "category": "information_retrieval",
            "arguments_required": 1
        },
        "GetCrossfadeMode": {
            "complexity": "🟡 Medium",
            "category": "information_retrieval",
            "arguments_required": 1
        },
        "Stop": {
            "complexity": "🟡 Medium",
            "category": "media_control",
            "arguments_required": 1
        },
        "Play": {
            "complexity": "🟡 Medium",
            "category": "media_control",
            "arguments_required": 2
        },
        "Pause": {
            "complexity": "🟡 Medium",
            "category": "media_control",
            "arguments_required": 1
        },
        "Seek": {
            "complexity": "🔴 Complex",
            "category": "media_control",
            "arguments_required": 3
        },
        "Next": {
            "complexity": "🟡 Medium",
            "category": "media_control",
            "arguments_required": 1
        },
        "Previous": {
            "complexity": "🟡 Medium",
            "category": "media_control",
            "arguments_required": 1
        },
        "SetPlayMode": {
            "complexity": "🟡 Medium",
            "category": "media_control",
            "arguments_required": 2
        },
        "SetCrossfadeMode": {
            "complexity": "🟡 Medium",
            "category": "configuration",
            "arguments_required": 2
        },
        "NotifyDeletedURI": {
            "complexity": "🟡 Medium",
            "category": "other",
            "arguments_required": 2
        },
        "GetCurrentTransportActions": {
            "complexity": "🟡 Medium",
            "category": "information_retrieval",
            "arguments_required": 1
        },
        "BecomeCoordinatorOfStandaloneGroup": {
            "complexity": "🔴 Complex",
            "category": "other",
            "arguments_required": 1
        },
        "DelegateGroupCoordinationTo": {
            "complexity": "🔴 Complex",
            "category": "other",
            "arguments_required": 3
        },
        "BecomeGroupCoordinator": {
            "complexity": "🔴 Complex",
            "category": "other",
            "arguments_required": 12
        },
        "BecomeGroupCoordinatorAndSource": {
            "complexity": "🔴 Complex",
            "category": "other",
            "arguments_required": 13
        },
        "ChangeCoordinator": {
            "complexity": "🔴 Complex",
            "category": "other",
            "arguments_required": 6
        },
        "ChangeTransportSettings": {
            "complexity": "🔴 Complex",
            "category": "information_retrieval",
            "arguments_required": 3
        },
        "ConfigureSleepTimer": {
            "complexity": "🟡 Medium",
            "category": "configuration",
            "arguments_required": 2
        },
        "GetRemainingSleepTimerDuration": {
            "complexity": "🔴 Complex",
            "category": "information_retrieval",
            "arguments_required": 1
        },
        "RunAlarm": {
            "complexity": "🔴 Complex",
            "category": "other",
            "arguments_required": 9
        },
        "StartAutoplay": {
            "complexity": "🔴 Complex",
            "category": "media_control",
            "arguments_required": 6
        },
        "GetRunningAlarmProperties": {
            "complexity": "🔴 Complex",
            "category": "information_retrieval",
            "arguments_required": 1
        },
        "SnoozeAlarm": {
            "complexity": "🟡 Medium",
            "category": "other",
            "arguments_required": 2
        },
        "EndDirectControlSession": {
            "complexity": "🟡 Medium",
            "category": "other",
            "arguments_required": 1
        },
    }
    actions_by_service["queue"] = {
        "AddURI": {
            "complexity": "🔴 Complex",
            "category": "configuration",
            "arguments_required": 6
        },
        "AddMultipleURIs": {
            "complexity": "🔴 Complex",
            "category": "configuration",
            "arguments_required": 8
        },
        "AttachQueue": {
            "complexity": "🔴 Complex",
            "category": "other",
            "arguments_required": 1
        },
        "Backup": {
            "complexity": "🟢 Easy",
            "category": "other",
            "arguments_required": 0
        },
        "Browse": {
            "complexity": "🔴 Complex",
            "category": "other",
            "arguments_required": 3
        },
        "CreateQueue": {
            "complexity": "🔴 Complex",
            "category": "other",
            "arguments_required": 3
        },
        "RemoveAllTracks": {
            "complexity": "🔴 Complex",
            "category": "configuration",
            "arguments_required": 2
        },
        "RemoveTrackRange": {
            "complexity": "🔴 Complex",
            "category": "configuration",
            "arguments_required": 4
        },
        "ReorderTracks": {
            "complexity": "🔴 Complex",
            "category": "other",
            "arguments_required": 5
        },
        "ReplaceAllTracks": {
            "complexity": "🔴 Complex",
            "category": "other",
            "arguments_required": 8
        },
        "SaveAsSonosPlaylist": {
            "complexity": "🔴 Complex",
            "category": "media_control",
            "arguments_required": 3
        },
    }
    actions_by_service["grouprenderingcontrol"] = {
        "GetGroupMute": {
            "complexity": "🟡 Medium",
            "category": "volume_control",
            "arguments_required": 1
        },
        "SetGroupMute": {
            "complexity": "🟡 Medium",
            "category": "volume_control",
            "arguments_required": 2
        },
        "GetGroupVolume": {
            "complexity": "🟡 Medium",
            "category": "volume_control",
            "arguments_required": 1
        },
        "SetGroupVolume": {
            "complexity": "🟡 Medium",
            "category": "volume_control",
            "arguments_required": 2
        },
        "SetRelativeGroupVolume": {
            "complexity": "🔴 Complex",
            "category": "volume_control",
            "arguments_required": 2
        },
        "SnapshotGroupVolume": {
            "complexity": "🟡 Medium",
            "category": "volume_control",
            "arguments_required": 1
        },
    }
    actions_by_service["virtuallinein"] = {
        "StartTransmission": {
            "complexity": "🔴 Complex",
            "category": "other",
            "arguments_required": 2
        },
        "StopTransmission": {
            "complexity": "🟡 Medium",
            "category": "media_control",
            "arguments_required": 2
        },
        "Play": {
            "complexity": "🟡 Medium",
            "category": "media_control",
            "arguments_required": 2
        },
        "Pause": {
            "complexity": "🟡 Medium",
            "category": "media_control",
            "arguments_required": 1
        },
        "Next": {
            "complexity": "🟡 Medium",
            "category": "media_control",
            "arguments_required": 1
        },
        "Previous": {
            "complexity": "🟡 Medium",
            "category": "media_control",
            "arguments_required": 1
        },
        "Stop": {
            "complexity": "🟡 Medium",
            "category": "media_control",
            "arguments_required": 1
        },
        "SetVolume": {
            "complexity": "🟡 Medium",
            "category": "volume_control",
            "arguments_required": 2
        },
    }

    return {
        "total_actions": 196,
        "actions_by_service": actions_by_service
    }

@app.get("/services")
async def list_services():
    """List all UPnP services."""
    services_info = {}
    services_info["alarmclock"] = {
        "type": "urn:schemas-upnp-org:service:AlarmClock:1",
        "actions": 17,
        "control_url": "/AlarmClock/Control"
    }
    services_info["musicservices"] = {
        "type": "urn:schemas-upnp-org:service:MusicServices:1",
        "actions": 3,
        "control_url": "/MusicServices/Control"
    }
    services_info["audioin"] = {
        "type": "urn:schemas-upnp-org:service:AudioIn:1",
        "actions": 6,
        "control_url": "/AudioIn/Control"
    }
    services_info["deviceproperties"] = {
        "type": "urn:schemas-upnp-org:service:DeviceProperties:1",
        "actions": 27,
        "control_url": "/DeviceProperties/Control"
    }
    services_info["systemproperties"] = {
        "type": "urn:schemas-upnp-org:service:SystemProperties:1",
        "actions": 17,
        "control_url": "/SystemProperties/Control"
    }
    services_info["zonegrouptopology"] = {
        "type": "urn:schemas-upnp-org:service:ZoneGroupTopology:1",
        "actions": 8,
        "control_url": "/ZoneGroupTopology/Control"
    }
    services_info["groupmanagement"] = {
        "type": "urn:schemas-upnp-org:service:GroupManagement:1",
        "actions": 4,
        "control_url": "/GroupManagement/Control"
    }
    services_info["qplay"] = {
        "type": "urn:schemas-tencent-com:service:QPlay:1",
        "actions": 1,
        "control_url": "/QPlay/Control"
    }
    services_info["contentdirectory"] = {
        "type": "urn:schemas-upnp-org:service:ContentDirectory:1",
        "actions": 16,
        "control_url": "/MediaServer/ContentDirectory/Control"
    }
    services_info["connectionmanager"] = {
        "type": "urn:schemas-upnp-org:service:ConnectionManager:1",
        "actions": 3,
        "control_url": "/MediaServer/ConnectionManager/Control"
    }
    services_info["renderingcontrol"] = {
        "type": "urn:schemas-upnp-org:service:RenderingControl:1",
        "actions": 27,
        "control_url": "/MediaRenderer/RenderingControl/Control"
    }
    services_info["avtransport"] = {
        "type": "urn:schemas-upnp-org:service:AVTransport:1",
        "actions": 42,
        "control_url": "/MediaRenderer/AVTransport/Control"
    }
    services_info["queue"] = {
        "type": "urn:schemas-sonos-com:service:Queue:1",
        "actions": 11,
        "control_url": "/MediaRenderer/Queue/Control"
    }
    services_info["grouprenderingcontrol"] = {
        "type": "urn:schemas-upnp-org:service:GroupRenderingControl:1",
        "actions": 6,
        "control_url": "/MediaRenderer/GroupRenderingControl/Control"
    }
    services_info["virtuallinein"] = {
        "type": "urn:schemas-upnp-org:service:VirtualLineIn:1",
        "actions": 8,
        "control_url": "/MediaRenderer/VirtualLineIn/Control"
    }

    return {
        "services": services_info
    }

# Example action endpoints (first few for demo)

@app.post("/alarmclock/format")
async def setformat():
    """
    Execute SetFormat action
    
    Complexity: 🟡 Medium
    Category: configuration
    Service: alarmclock
    """
    if not DEVICE_HOST:
        raise HTTPException(status_code=400, detail="Device not initialized. Call /init first.")
    
    return {
        "status": "demo",
        "action": "SetFormat",
        "service": "alarmclock",
        "message": "This is a demo endpoint - would execute SetFormat on real device"
    }

@app.post("/alarmclock/format")
async def getformat():
    """
    Execute GetFormat action
    
    Complexity: 🟡 Medium
    Category: information_retrieval
    Service: alarmclock
    """
    if not DEVICE_HOST:
        raise HTTPException(status_code=400, detail="Device not initialized. Call /init first.")
    
    return {
        "status": "demo",
        "action": "GetFormat",
        "service": "alarmclock",
        "message": "This is a demo endpoint - would execute GetFormat on real device"
    }

@app.post("/alarmclock/timezone")
async def settimezone():
    """
    Execute SetTimeZone action
    
    Complexity: 🟡 Medium
    Category: configuration
    Service: alarmclock
    """
    if not DEVICE_HOST:
        raise HTTPException(status_code=400, detail="Device not initialized. Call /init first.")
    
    return {
        "status": "demo",
        "action": "SetTimeZone",
        "service": "alarmclock",
        "message": "This is a demo endpoint - would execute SetTimeZone on real device"
    }

@app.post("/alarmclock/timezone")
async def gettimezone():
    """
    Execute GetTimeZone action
    
    Complexity: 🟡 Medium
    Category: information_retrieval
    Service: alarmclock
    """
    if not DEVICE_HOST:
        raise HTTPException(status_code=400, detail="Device not initialized. Call /init first.")
    
    return {
        "status": "demo",
        "action": "GetTimeZone",
        "service": "alarmclock",
        "message": "This is a demo endpoint - would execute GetTimeZone on real device"
    }

@app.post("/alarmclock/timezoneandrule")
async def gettimezoneandrule():
    """
    Execute GetTimeZoneAndRule action
    
    Complexity: 🔴 Complex
    Category: information_retrieval
    Service: alarmclock
    """
    if not DEVICE_HOST:
        raise HTTPException(status_code=400, detail="Device not initialized. Call /init first.")
    
    return {
        "status": "demo",
        "action": "GetTimeZoneAndRule",
        "service": "alarmclock",
        "message": "This is a demo endpoint - would execute GetTimeZoneAndRule on real device"
    }

@app.get("/security")
async def security_analysis():
    """Show security-relevant actions."""
    security_actions = []
    security_actions.append({
        "action": "EditAccountPasswordX",
        "service": "systemproperties",
        "complexity": "🔴 Complex"
    })

    return {
        "security_actions": security_actions,
        "warning": "These actions could modify device security settings!"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
