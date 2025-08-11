import time
import threading
import pymem
import os
import mem.memfuncs
import mem.antioffset as antioffset
from mem.ext_types import Offset # Need to import Offset dataclass

def anti_flash_thread(memf: mem.memfuncs.memfunc, client_dll_base_address: int, antioffset_obj: Offset):
    print("[Anti-Flash] Anti-flash enabled.")
    try:
        while True:
            # Read the local player pawn address
            player_pawn_address = memf.ReadPointer(client_dll_base_address, antioffset_obj.dwLocalPlayerPawn)
            if player_pawn_address:
                # Set m_flFlashMaxAlpha to 0.0 to disable flash
                memf.WriteFloat(player_pawn_address, 0.0, antioffset_obj.m_flFlashMaxAlpha)
            time.sleep(0.001) # Small sleep to prevent busy-waiting
    except Exception as e:
        print(f"[Anti-Flash] Error in anti-flash thread: {e}")
    finally:
        # Attempt to restore flash on exit
        try:
            player_pawn_address = memf.ReadPointer(client_dll_base_address, antioffset_obj.dwLocalPlayerPawn)
            if player_pawn_address:
                memf.WriteFloat(player_pawn_address, 255.0, antioffset_obj.m_flFlashMaxAlpha) # Restore original flash value
                print("[Anti-Flash] Flash restored to original value.")
        except Exception as e:
            print(f"[Anti-Flash] Error restoring flash on exit: {e}")
    print("[Anti-Flash] Anti-flash thread stopped.")

def antiflash_main():
    try:
        pm = pymem.Pymem("cs2.exe")
        print("[Anti-Flash] Attached to cs2.exe process.")
    except pymem.exception.PymemError:
        print("[-] Error: CS2 process not found. Please start CS2 first.")
        os._exit(1)

    client_base_address = pymem.process.module_from_name(pm.process_handle, "client.dll").lpBaseOfDll
    memf = mem.memfuncs.memfunc(proc=pm)

    # Initialize antioffset by fetching them (replicates main.py's get_antioffset logic)
    oc = antioffset.Client() # This fetches antioffset from GitHub
    antioffset_obj = Offset(
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
    print("[Anti-Flash] antioffset loaded.")

    # Start the anti-flash thread
    anti_flash_thread_instance = threading.Thread(target=anti_flash_thread, args=(memf, client_base_address, antioffset_obj), daemon=True)
    anti_flash_thread_instance.start()

    
    try:
        pass
    finally:
        # The daemon thread's finally block will handle restoration
        print("[Anti-Flash] Exiting.")

