#include "weapon_markers.h"
#include <assert.h>
#include <stdio.h>

int main(void) {
    for (unsigned i=0; i<sizeof k_marker_groups/sizeof k_marker_groups[0]; ++i) {
        const MohuVrMarkerGroup* group=&k_marker_groups[i];
        const MohuVrWeaponProfile* p=mohu_vr_weapon_profile_find(group->id);
        assert(p);
        unsigned count=group->counts[0]+group->counts[1]+group->counts[2];
        assert(count<=MOHU_VR_MARKER_VERTEX_LIMIT);
        printf("GROUP|%u|%u,%u,%u|",group->id,group->counts[0],group->counts[1],group->counts[2]);
        int16_t vertices[MOHU_VR_MARKER_VERTEX_LIMIT][3];
        for (unsigned v=0; v<count; ++v) {
            assert(mohu_vr_weapon_gun_vertex(p,group->vertices[v][0],group->vertices[v][1]));
            printf("%s%u:%u",v ? "," : "",group->vertices[v][0],group->vertices[v][1]);
            vertices[v][0]=100; vertices[v][1]=-200; vertices[v][2]=300;
        }
        putchar('\n');
        vertices[0][0]+=(int16_t)group->counts[0];
        double points[3][3];
        assert(mohu_vr_marker_points(group,vertices,count,points));
        assert(points[0][0]>100.999999 && points[0][0]<101.000001);
        assert(points[1][1]>-200.000001 && points[1][1]<-199.999999);
        if (!group->counts[2]) assert(!memcmp(points[0],points[2],sizeof points[0]));
        double saved[3][3]; memcpy(saved,points,sizeof saved);
        assert(!mohu_vr_marker_points(group,vertices,count-1,points));
        assert(!memcmp(points,saved,sizeof saved));
        assert(!mohu_vr_marker_points(NULL,vertices,count,points));
    }
    const MohuVrMarkerKey current={0x801483D0u,0x801487D0u,0x801491C0u,0,0x8544F8B9u,7};
    MohuVrMarkerSample sample={0};
    sample.key=current; sample.valid=1; sample.cycle=1000000;
    assert(mohu_vr_marker_usable(&sample,&current,1000000+MOHU_VR_MARKER_MAX_AGE));
    assert(!mohu_vr_marker_usable(&sample,&current,999999));
    assert(!mohu_vr_marker_usable(&sample,&current,1000001+MOHU_VR_MARKER_MAX_AGE));
    assert(!mohu_vr_marker_usable(NULL,&current,1000000));
#define REJECT(field,value) do { MohuVrMarkerKey key=current;key.field=value; \
    assert(!mohu_vr_marker_usable(&sample,&key,1000000)); } while (0)
    REJECT(owner,0x80145810u); REJECT(input,current.input+4);
    REJECT(object,current.object+4); REJECT(id,1); REJECT(id,255);
    REJECT(geometry_fnv32,0); REJECT(geometry_fnv32,current.geometry_fnv32+1);
    REJECT(generation,8);
#undef REJECT
    sample.valid=0; assert(!mohu_vr_marker_usable(&sample,&current,1000000));
    puts("PASS: canonical marker means, model selections, ownership, load and freshness");
    return 0;
}
