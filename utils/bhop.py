import time
import threading
import pymem
import os
import mem.memfuncs
import mem.antioffset as antioffset
import ctypes
from mem.ext_types import Offset # Need to import Offset dataclass

# Load the user32.dll for GetAsyncKeyState
user32 = ctypes.WinDLL('user32.dll')

def bhop_thread(memf: mem.memfuncs.memfunc, client_dll_base_address: int, antioffset_obj: Offset, stop_event: threading.Event):
    print("[Bhop] Bhop enabled.")
    try:
        while not stop_event.is_set():
            # Read entity list and local player controller/pawn
            entity_list = memf.ReadPointer(client_dll_base_address, antioffset_obj.dwEntityList)
            local_player_controller = memf.ReadPointer(client_dll_base_address, antioffset_obj.dwLocalPlayerController)
            
            if not local_player_controller or not entity_list:
                time.sleep(0.1)
                continue

            local_pawn_handle = memf.ReadInt(local_player_controller, antioffset_obj.m_hPlayerPawn)
            
            if not local_pawn_handle:
                time.sleep(0.1)
                continue

            # Resolve local pawn address from handle
            list_entry2 = memf.ReadPointer(entity_list, 0x8 * ((local_pawn_handle & 0x7FFF) >> 9) + 16)
            if not list_entry2:
                time.sleep(0.1)
                continue

            local_player_pawn = memf.ReadPointer(list_entry2, 120 * (local_pawn_handle & 0x1FF))

            if local_player_pawn:
                flags = memf.ReadInt(local_player_pawn, antioffset_obj.m_fFlags)
                # Check if spacebar is pressed (0x20 is VK_SPACE) and player is on ground (FL_ONGROUND flag)
                if user32.GetAsyncKeyState(0x20) and (flags & (1 << 0)): # (1 << 0) is FL_ONGROUND
                    memf.WriteInt(client_dll_base_address, 65537, antioffset_obj.ButtonJump) # Force +jump
                    time.sleep(0.1) # Small delay to ensure jump registers
                    memf.WriteInt(client_dll_base_address, 256, antioffset_obj.ButtonJump) # Force -jump
            time.sleep(0.01) # Small sleep to prevent busy-waiting
    except Exception as e:
        print(f"[Bhop] Error in bhop thread: {e}")
    print("[Bhop] Bhop thread stopped.")

def bunnny_main(stop_event: threading.Event):
    try:
        pm = pymem.Pymem("cs2.exe")
        print("[Bhop] Attached to cs2.exe process.")
    except pymem.exception.PymemError:
        print("[-] Error: CS2 process not found. Please start CS2 first.")
        return # Exit gracefully if process not found

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
    print("[Bhop] antioffset loaded.")

    # Start the bhop thread
    bhop_thread_instance = threading.Thread(target=bhop_thread, args=(memf, client_base_address, antioffset_obj, stop_event), daemon=True)
    bhop_thread_instance.start()

    print("[Bhop] Running.")
    stop_event.wait() # Keep main thread alive until stop_event is set
    print("[Bhop] Exiting.")


