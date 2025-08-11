import time
import threading
import pymem
import os
import mem.memfuncs
import mem.antioffset as antioffset
import random 
import keyboard 
from pynput.mouse import Controller, Button 
from win32gui import GetWindowText, GetForegroundWindow 
from mem.ext_types import Offset

mouse = Controller() 

def trigger_bot_logic(memf, client_dll, offsets, settings, debug_print=False):
    if debug_print: print("\n--- TriggerBot Debug Frame ---")
    try:
        # Check if CS2 is foreground window
        if not GetWindowText(GetForegroundWindow()) == "Counter-Strike 2":
            if debug_print: print("[Debug] CS2 is not foreground window.")
            return
        if debug_print: print("[Debug] CS2 is foreground window.")

        local_pawn = memf.ReadPointer(client_dll, offsets.dwLocalPlayerPawn)
        if not local_pawn: 
            if debug_print: print("[Debug] No local player pawn.")
            return
        if debug_print: print(f"[Debug] Local Player Pawn: {hex(local_pawn)}")

        entity_id = memf.ReadInt(local_pawn, offsets.m_iIDEntIndex)
        if entity_id <= 0: 
            if debug_print: print(f"[Debug] No entity under crosshair (ID: {entity_id}).")
            return
        if debug_print: print(f"[Debug] Entity under crosshair ID: {entity_id}")

        ent_list = memf.ReadPointer(client_dll, offsets.dwEntityList)
        
        # Corrected entity resolution based on provided base code
        entry_base = memf.ReadPointer(ent_list, 0x8 * (entity_id >> 9) + 0x10)
        enemy_pawn = memf.ReadPointer(entry_base, 120 * (entity_id & 0x1FF))
        
        if not enemy_pawn: 
            if debug_print: print("[Debug] Could not resolve enemy pawn from entity ID.")
            return
        if debug_print: print(f"[Debug] Enemy Pawn: {hex(enemy_pawn)}")

        my_team = memf.ReadInt(local_pawn, offsets.m_iTeamNum)
        enemy_team = memf.ReadInt(enemy_pawn, offsets.m_iTeamNum)
        enemy_hp = memf.ReadInt(enemy_pawn, offsets.m_iHealth)

        if debug_print: print(f"[Debug] My Team: {my_team}, Enemy Team: {enemy_team}, Enemy HP: {enemy_hp}")

        if my_team != enemy_team and enemy_hp > 0:
            if debug_print: print("[Debug] Valid enemy found! Simulating click.")
            delay = settings.get("trigger_delay_ms", 10) / 1000.0
            time.sleep(delay)
            mouse.press(Button.left)
            time.sleep(random.uniform(0.01, 0.05))
            mouse.release(Button.left)
        elif debug_print:
            print("[Debug] Not a valid enemy (same team or dead).")

    except Exception as e:
        if debug_print: print(f"[Debug] EXCEPTION in trigger_bot_logic: {e}")
        return

def triggerbot_thread(memf: mem.memfuncs.memfunc, client_dll_base_address: int, antioffset_obj: Offset, settings: dict, stop_event: threading.Event):
    key_name = settings.get('keyboards', 'x').lower() # Using 'keyboards' from settings
    print(f"[TriggerBot] Hotkey set to: {key_name}")

    hotkey_was_pressed = False
    while not stop_event.is_set():
        try:
            key_pressed = keyboard.is_pressed(key_name)
            debug_this_frame = False
            if key_pressed and not hotkey_was_pressed:
                debug_this_frame = True
            
            hotkey_was_pressed = key_pressed

            if settings.get('trigger_bot_active', 0) and key_pressed:
                trigger_bot_logic(memf, client_dll_base_address, antioffset_obj, settings, debug_print=debug_this_frame)
            time.sleep(0.001)
        except Exception as e:
            if debug_print: print(f"[Debug] EXCEPTION in triggerbot_thread: {e}")
            pass

def triggerbot_main(settings: dict, stop_event: threading.Event):
    try:
        pm = pymem.Pymem("cs2.exe")
    except pymem.exception.PymemError:
        return

    client_base_address = pymem.process.module_from_name(pm.process_handle, "client.dll").lpBaseOfDll
    memf = mem.memfuncs.memfunc(proc=pm)
    oc = antioffset.Client()
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
        m_boneArray=128,
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
        m_vecAbsOrigin=oc.get('CGameSceneNode', 'm_vecAbsOrigin')
    )

    triggerbot_thread_instance = threading.Thread(target=triggerbot_thread, args=(memf, client_base_address, antioffset_obj, settings, stop_event), daemon=True)
    triggerbot_thread_instance.start()
    stop_event.wait()