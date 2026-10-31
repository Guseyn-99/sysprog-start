#include <stdio.h>
#include <windows.h>

int main(void) {
    DWORD pid = GetCurrentProcessId();

    printf("agent v0, pid=%lu\n", (unsigned long)pid);
    printf("Press Enter to exit...\n");

    getchar();

    return 0;
}