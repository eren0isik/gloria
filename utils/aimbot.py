import time
import threading
import pymem
import os
import mem.memfuncs
import mem.antioffset as antioffset
import ctypes
from mem.ext_types import Offset
import math

user32 = ctypes.WinDLL('user32.dll')

KEY_MAP = {
    'alt': 0x12,      # VK_MENU
    'lalt': 0xA4,     # VK_LMENU
    'ralt': 0xA5,     # VK_RMENU
    'shift': 0x10,    # VK_SHIFT
    'lshift': 0xA0,   # VK_LSHIFT
    'rshift': 0xA1,   # VK_RSHIFT
    'ctrl': 0x11,     # VK_CONTROL
    'lctrl': 0xA2,    # VK_LCONTROL
    'rctrl': 0xA3,    # VK_RCONTROL,
    'mouse1': 0x01,   # VK_LBUTTON
    'mouse2': 0x02,   # VK_RBUTTON
    'mouse3': 0x04,   # VK_MBUTTON
    'mouse4': 0x05,   # VK_XBUTTON1
    'mouse5': 0x06,   # VK_XBUTTON2
}

# --- Math library from test.py ---
class Vector3:
    def __init__(self, x=0.0, y=0.0, z=0.0):
        self.x = x
        self.y = y
        self.z = z

    def __add__(self, o: "Vector3") -> "Vector3":
        return Vector3(self.x + o.x, self.y + o.y, self.z + o.z)

    def __sub__(self, o: "Vector3") -> "Vector3":
        return Vector3(self.x - o.x, self.y - o.y, self.z - o.z)

    def __mul__(self, s: float) -> "Vector3":
        return Vector3(self.x * s, self.y * s, self.z * s)

    def length(self) -> float:
        return math.sqrt(self.x*self.x + self.y*self.y + self.z*self.z)

def clamp_pitch(pitch: float) -> float:
    return max(-89.0, min(89.0, pitch))

def normalize_yaw(yaw: float) -> float:
    while yaw > 180.0:
        yaw -= 360.0
    while yaw < -180.0:
        yaw += 360.0
    return yaw

def calc_angles(source: Vector3, target: Vector3) -> Vector3:
    delta = target - source
    hyp = math.sqrt(delta.x*delta.x + delta.y*delta.y)
    if hyp == 0:
        return Vector3(0,0,0)
    pitch = -math.degrees(math.atan2(delta.z, hyp))
    yaw = math.degrees(math.atan2(delta.y, delta.x))
    return Vector3(clamp_pitch(pitch), normalize_yaw(yaw), 0.0)

def smooth_angle(current: Vector3, target: Vector3, smooth: float) -> Vector3:
    if smooth <= 1.0:
        return target
    
    diff_pitch = target.x - current.x
    diff_yaw = target.y - current.y
    
    if diff_yaw > 180: diff_yaw -= 360
    if diff_yaw < -180: diff_yaw += 360

    new_pitch = current.x + diff_pitch / smooth
    new_yaw = current.y + diff_yaw / smooth
    return Vector3(clamp_pitch(new_pitch), normalize_yaw(new_yaw), 0.0)

def compute_fov(current: Vector3, target: Vector3) -> float:
    diff_pitch = current.x - target.x
    diff_yaw = current.y - target.y
    if diff_yaw > 180: diff_yaw -= 360
    if diff_yaw < -180: diff_yaw += 360
    return math.sqrt(diff_pitch*diff_pitch + diff_yaw*diff_yaw)

# --- Memory reading helpers ---
def get_player_eyepos(memf, player_pawn, offsets) -> Vector3:
    try:
        origin = memf.ReadVec(player_pawn, offsets.m_vOldOrigin)
        view_offset = memf.ReadVec(player_pawn, offsets.m_vecViewOffset)
        return origin + view_offset
    except Exception:
        return None

def get_enemy_target_pos(memf, enemy_pawn, offsets) -> Vector3:
    # First, try to get the precise head position
    try:
        game_scene_node = memf.ReadPointer(enemy_pawn, offsets.m_pGameSceneNode)

        bone_matrix_addr = memf.ReadPointer(game_scene_node + offsets.m_modelState, offsets.m_boneArray) # Use m_boneArray from offsets
        base = bone_matrix_addr + 6 * 32 # Head bone index * size
        head_pos = Vector3(
            memf.ReadFloat(base, 0x0),
            memf.ReadFloat(base, 0x4),
            memf.ReadFloat(base, 0x8)
        )
        if abs(head_pos.x) < 100000 and abs(head_pos.y) < 100000 and abs(head_pos.z) < 100000:
            return head_pos
    except Exception as e:
        pass # If it fails, proceed to the fallback

    # Fallback: If head bone fails, aim at the player's origin, adjusting for crouch
    try:
        enemy_origin = memf.ReadVec(enemy_pawn, offsets.m_vOldOrigin)
        flags = memf.ReadInt(enemy_pawn, offsets.m_fFlags)
        is_crouching = (flags & (1 << 1)) != 0
        z_offset = 40.0 if is_crouching else 60.0 # Use a lower offset for crouched players
        return Vector3(enemy_origin.x, enemy_origin.y, enemy_origin.z + z_offset)
    except Exception as e:
        return None

# --- Main Aimbot Logic ---
def aimbot_logic(memf, client_dll, offsets, settings):
    try:
        local_pawn = memf.ReadPointer(client_dll, offsets.dwLocalPlayerPawn)
        if not local_pawn: return

        my_pos = get_player_eyepos(memf, local_pawn, offsets)
        if not my_pos: return
        
        my_team = memf.ReadInt(local_pawn, offsets.m_iTeamNum)
        current_angles = Vector3(
            memf.ReadFloat(client_dll, offsets.dwViewAngles),
            memf.ReadFloat(client_dll, offsets.dwViewAngles + 4),
            0
        )

        best_target_angles = None
        min_fov = settings.get('radius', 50)

        entity_list = memf.ReadPointer(client_dll, offsets.dwEntityList)
        entity_ptr = memf.ReadPointer(entity_list, 0x10)

        for i in range(1, 65):
            try:
                entity_controller = memf.ReadPointer(entity_ptr, 0x78 * (i & 0x1FF))
                if not entity_controller: continue

                pawn_handle = memf.ReadInt(entity_controller, offsets.m_hPlayerPawn)
                if not pawn_handle: continue

                list_entry = memf.ReadPointer(entity_list, 0x8 * ((pawn_handle & 0x7FFF) >> 9) + 16)
                if not list_entry: continue

                enemy_pawn = memf.ReadPointer(list_entry, 120 * (pawn_handle & 0x1FF))
                if not enemy_pawn or enemy_pawn == local_pawn: continue

                health = memf.ReadInt(enemy_pawn, offsets.m_iHealth)
                team = memf.ReadInt(enemy_pawn, offsets.m_iTeamNum)
                life_state = memf.ReadInt(enemy_pawn, offsets.m_lifeState)

                if health > 0 and team != my_team and life_state == 256:
                    enemy_target_pos = get_enemy_target_pos(memf, enemy_pawn, offsets)
                    if not enemy_target_pos: continue
                    

                    target_angles = calc_angles(my_pos, enemy_target_pos)
                    fov = compute_fov(current_angles, target_angles)

                    if fov < min_fov:
                        min_fov = fov
                        best_target_angles = target_angles
            except Exception:
                continue

        if best_target_angles:
            smooth = settings.get('aim_smoothing', 5.0)
            smoothed_angles = smooth_angle(current_angles, best_target_angles, smooth)
            memf.WriteFloat(client_dll, smoothed_angles.x, offsets.dwViewAngles)
            memf.WriteFloat(client_dll, smoothed_angles.y, offsets.dwViewAngles + 4)

    except Exception:
        return

def aimbot_thread(memf: mem.memfuncs.memfunc, client_dll_base_address: int, antioffset_obj: Offset, settings: dict, stop_event: threading.Event):
    key_name = settings.get('keyboard', 'alt').lower()
    if key_name in KEY_MAP:
        aim_key_hex = KEY_MAP[key_name]
    else:
        aim_key_hex = ctypes.windll.user32.VkKeyScanA(ord(key_name.upper())) & 0xFF

    while not stop_event.is_set():
        try:
            if settings.get('aim_active', 1) and (user32.GetAsyncKeyState(aim_key_hex) & 0x8000):
                aimbot_logic(memf, client_dll_base_address, antioffset_obj, settings)
            time.sleep(0.001)
        except Exception:
            pass

def aimbot_main(settings: dict, stop_event: threading.Event):
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

    aimbot_thread_instance = threading.Thread(target=aimbot_thread, args=(memf, client_base_address, antioffset_obj, settings, stop_event), daemon=True)
    aimbot_thread_instance.start()
    stop_event.wait()
