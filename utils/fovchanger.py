import time
import threading
import pymem
import os
import mem.memfuncs
import mem.antioffset as offsets
from mem.ext_types import Offset # Need to import Offset dataclass

# Default FOV to apply. You can change this value.

# Variable to store the original FOV for restoration
original_fov = None

def fov_changer_thread(memf: mem.memfuncs.memfunc, client_dll_base_address: int, offsets_obj: Offset, target_fov: int, stop_event: threading.Event):
    print(f"[FOV Changer] FOV changer enabled. Target FOV: {target_fov}")
    try:
        while not stop_event.is_set():
            local_player_p = memf.ReadPointer(client_dll_base_address, offsets_obj.dwLocalPlayerPawn)
            if local_player_p:
                camera_services = memf.ReadPointer(local_player_p, offsets_obj.m_pCameraServices)
                if camera_services:
                    current_fov = memf.ReadInt(camera_services, offsets_obj.m_iFOV)
                    is_scoped = memf.ReadBool(local_player_p, offsets_obj.m_bIsScoped)

                    # Only change FOV if not scoped and current FOV is not already target FOV
                    if not is_scoped and current_fov != target_fov:
                        memf.WriteInt(camera_services, target_fov, offsets_obj.m_iFOV)
            time.sleep(0.5) # Further increased sleep to reduce potential shaking
    except Exception as e:
        print(f"[FOV Changer] Error in FOV changer thread: {e}")
    finally:
        print("[FOV Changer] FOV changer thread stopped.")

def fovchanger_main(target_fov: int, stop_event: threading.Event):
    global original_fov # Declare as global to modify

    try:
        pm = pymem.Pymem("cs2.exe")
        print("[FOV Changer] Attached to cs2.exe process.")
    except pymem.exception.PymemError:
        print("[-] Error: CS2 process not found. Please start CS2 first.")
        return # Exit gracefully if process not found

    client_base_address = pymem.process.module_from_name(pm.process_handle, "client.dll").lpBaseOfDll
    memf = mem.memfuncs.memfunc(proc=pm)

    # Initialize offsets by fetching them (replicates main.py's get_offsets logic)
    oc = offsets.Client() # This fetches offsets from GitHub
    offsets_obj = Offset(
        dwViewMatrix=oc.offset("dwViewMatrix"),
        dwLocalPlayerPawn=oc.offset("dwLocalPlayerPawn"),
        dwEntityList=oc.offset("dwEntityList"),
        dwLocalPlayerController=oc.offset("dwLocalPlayerController"),
        dwViewAngles = oc.offset("dwViewAngles"),
        dwGameRules = oc.offset("dwGameRules"),

        ButtonJump=oc.button("jump"),

        m_hPlayerPawn=oc.get("CCSPlayerController", "m_hPlayerPawn"),
        m_iHealth=oc.get("C_BaseEntity", "m_iHealth"),
        m_lifeState=oc.get("C_BaseEntity", "m_lifeState"),
        m_iTeamNum=oc.get("C_BaseEntity", "m_iTeamNum"),
        m_vOldOrigin=oc.get("C_BasePlayerPawn", "m_vOldOrigin"),
        m_pGameSceneNode=oc.get("C_BaseEntity", "m_pGameSceneNode"),
        m_modelState=oc.get("CSkeletonInstance", "m_modelState"),
        m_boneArray=128, # This is a hardcoded value in main.py
        m_nodeToWorld=oc.get("CGameSceneNode", "m_nodeToWorld"),
        m_sSanitizedPlayerName=oc.get("CCSPlayerController", "m_sSanitizedPlayerName"),
        m_iIDEntIndex=oc.get("C_CSPlayerPawnBase", "m_iIDEntIndex"),
        m_flFlashMaxAlpha=oc.get("C_CSPlayerPawnBase", "m_flFlashMaxAlpha"),
        m_fFlags=oc.get("C_BaseEntity", "m_fFlags"),
        m_iFOV=oc.get("CCSPlayerBase_CameraServices", "m_iFOV"),
        m_pCameraServices=oc.get("C_BasePlayerPawn", "m_pCameraServices"),
        m_bIsScoped=oc.get("C_CSPlayerPawn", "m_bIsScoped"),
        m_vecViewOffset = oc.get("C_BaseModelEntity", "m_vecViewOffset"),
        m_entitySpottedState = oc.get("C_CSPlayerPawn", "m_entitySpottedState"),
        m_bSpotted = oc.get("EntitySpottedState_t", "m_bSpotted"),
        m_bBombPlanted = oc.get("C_CSGameRules", "m_bBombPlanted"),
        m_vecAbsOrigin=oc.get('CGameSceneNode', 'm_vecAbsOrigin'),
    )
    print("[FOV Changer] Offsets loaded.")

    # Get current FOV to restore later
    try:
        local_player_p = memf.ReadPointer(client_base_address, offsets_obj.dwLocalPlayerPawn)
        if local_player_p:
            camera_services = memf.ReadPointer(local_player_p, offsets_obj.m_pCameraServices)
            if camera_services:
                original_fov = memf.ReadInt(camera_services, offsets_obj.m_iFOV)
                print(f"[FOV Changer] Original FOV: {original_fov}")
    except Exception as e:
        print(f"[FOV Changer] Could not read original FOV: {e}. Defaulting to 90 for restoration.")
        original_fov = 90 # Fallback if cannot read

    # Start the FOV changer thread
    fov_changer_thread_instance = threading.Thread(target=fov_changer_thread, args=(memf, client_base_address, offsets_obj, target_fov, stop_event), daemon=True)
    fov_changer_thread_instance.start()

    print(f"[FOV Changer] Running. Target FOV: {target_fov}.")
    try:
        stop_event.wait() # Wait until stop_event is set
    except KeyboardInterrupt:
        print("[FOV Changer] Ctrl+C detected. Stopping FOV changer.")
    finally:
        # Restore original FOV
        try:
            if original_fov is not None:
                local_player_p = memf.ReadPointer(client_base_address, offsets_obj.dwLocalPlayerPawn)
                if local_player_p:
                    camera_services = memf.ReadPointer(local_player_p, offsets_obj.m_pCameraServices)
                    if camera_services:
                        memf.WriteInt(camera_services, original_fov, offsets_obj.m_iFOV)
                        print(f"[FOV Changer] FOV restored to original value: {original_fov}.")
        except Exception as e:
            pass


