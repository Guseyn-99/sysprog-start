
import ctypes

kernel32 = ctypes.windll.kernel32
kernel32.GetCurrentProcessId.restype = ctypes.c_ulong

pid = kernel32.GetCurrentProcessId()

print(f"agent v0 (python), pid={pid}")
input("Press Enter to exit...")
