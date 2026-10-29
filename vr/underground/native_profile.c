/* Diagnostic-only timings of the generated CPS segments, including their
 * PGXP and cycle services. A segment returns to dispatch; it does not contain
 * its guest callees. Thus these times are exclusive, not nested call totals.
 * The original generated bodies and savestate/execution contract are intact.
 * No timers, wrappers or command exist in a normal production build. */
#include "cpu_state.h"
#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

extern unsigned mohu_vr_native_profile_scope(void);
static volatile LONG64 ticks[3][8], calls[3][8];
static const uint32_t addresses[8] = {
    0x80010000u, 0x80010508u, 0x80010CF0u, 0x80011424u,
    0x80013B40u, 0x80013EB4u, 0x80017628u, 0x8001A004u
};

#define WRAP(address, index) \
    extern void __real_func_##address(CPUState* cpu); \
    void __wrap_func_##address(CPUState* cpu) { \
        const unsigned scope = mohu_vr_native_profile_scope(); \
        LARGE_INTEGER begin, end; \
        QueryPerformanceCounter(&begin); \
        __real_func_##address(cpu); \
        QueryPerformanceCounter(&end); \
        InterlockedExchangeAdd64(&ticks[scope][index], end.QuadPart-begin.QuadPart); \
        InterlockedIncrement64(&calls[scope][index]); \
    }
WRAP(80010000, 0)
WRAP(80010508, 1)
WRAP(80010CF0, 2)
WRAP(80011424, 3)
WRAP(80013B40, 4)
WRAP(80013EB4, 5)
WRAP(80017628, 6)
WRAP(8001A004, 7)

int mohu_vr_native_profile_command(const char* args, char* reply, int cap) {
    /* One scope per reply fits the framework's 1024-byte command reply. */
    const unsigned scope = (unsigned)strtoul(args, NULL, 10);
    if (scope>2u) return -1;
    LARGE_INTEGER frequency;
    QueryPerformanceFrequency(&frequency);
    int used = snprintf(reply, cap, "{\"exclusive_cps_segments\":true,\"rows\":[");
    for (unsigned i=0; i<8; ++i) {
        if (used<0 || used>=cap) return -1;
        used += snprintf(reply+used, cap-used,
            "%s{\"scope\":%u,\"address\":\"0x%08X\",\"calls\":%llu,\"us\":%.3f}",
            i ? "," : "", scope, addresses[i],
            (unsigned long long)InterlockedCompareExchange64(&calls[scope][i],0,0),
            InterlockedCompareExchange64(&ticks[scope][i],0,0)*1000000.0/
                (double)frequency.QuadPart);
    }
    if (used<0 || used>=cap) return -1;
    const int tail = snprintf(reply+used, cap-used, "]}");
    return tail>=0 && tail<cap-used ? 0 : -1;
}
