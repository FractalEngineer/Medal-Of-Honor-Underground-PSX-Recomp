#include "mohu_achievements_state.h"

#include <stdio.h>
#include <string.h>

#define MAX_EVENTS 16

typedef struct {
    const char* events[MAX_EVENTS];
    int count;
} EventLog;

static void record(const char* event, void* user) {
    EventLog* log = (EventLog*)user;
    if (log->count < MAX_EVENTS) log->events[log->count] = event;
    ++log->count;
}

static int has(const EventLog* log, const char* event) {
    for (int i = 0; i < log->count && i < MAX_EVENTS; ++i)
        if (strcmp(log->events[i], event) == 0) return 1;
    return 0;
}

static int expect(int condition, const char* what) {
    if (!condition) {
        fprintf(stderr, "FAIL: %s\n", what);
        return 1;
    }
    return 0;
}

int main(void) {
    int failures = 0;
    MohuAchievementsState state;
    EventLog log;

    /* First gameplay frame is the start; menus produce nothing. */
    mohu_achievements_state_reset(&state);
    memset(&log, 0, sizeof(log));
    mohu_achievements_state_sample(&state, 0, -1, -1, record, &log);
    failures += expect(log.count == 0, "menu produced an event");
    mohu_achievements_state_sample(&state, 1, 100, 2, record, &log);
    failures += expect(has(&log, "gameplay_started"), "gameplay_started");
    failures += expect(!has(&log, "weapon_switched"), "first weapon is not a switch");

    /* Sniper and the first actual switch. */
    mohu_achievements_state_sample(&state, 1, 100, 5, record, &log);
    failures += expect(has(&log, "sniper_equipped"), "sniper_equipped");
    mohu_achievements_state_sample(&state, 1, 100, 3, record, &log);
    failures += expect(has(&log, "weapon_switched"), "weapon_switched");

    /* A low-health recovery unlocks once, not once per frame. */
    mohu_achievements_state_sample(&state, 1, 5, 3, record, &log);
    failures += expect(!has(&log, "close_call"), "close_call before recovery");
    mohu_achievements_state_sample(&state, 1, 60, 3, record, &log);
    failures += expect(has(&log, "close_call"), "close_call after recovery");
    const int after_close = log.count;
    mohu_achievements_state_sample(&state, 1, 70, 3, record, &log);
    failures += expect(log.count == after_close, "close_call repeated");

    /* Ten minutes of gameplay unlocks the long-haul event exactly once. */
    mohu_achievements_state_reset(&state);
    memset(&log, 0, sizeof(log));
    for (uint32_t i = 0; i < MOHU_ACH_LONG_HAUL_FRAMES + 10; ++i)
        mohu_achievements_state_sample(&state, 1, 100, 2, record, &log);
    failures += expect(has(&log, "long_haul"), "long_haul");
    int long_haul_count = 0;
    for (int i = 0; i < log.count && i < MAX_EVENTS; ++i)
        if (strcmp(log.events[i], "long_haul") == 0) ++long_haul_count;
    failures += expect(long_haul_count == 1, "long_haul repeated");

    if (!failures) printf("mohu_achievements_test: ok\n");
    return failures ? 1 : 0;
}
