"""Read numeric shipped calibration initializers for diagnostic pose solvers.

The old PCA receipts are historical measurements, not the current runtime
defaults. Reject a changed initializer format rather than solve against stale
or silently guessed values. Runtime code still owns the immutable profiles.
"""
from pathlib import Path
import re

IDS = dict(p38=0, mp40=1, shotgun=4, scoped_rifle=5, colt_45=8,
           silenced_pistol=9, stick_grenade=10, m1_garand=12, panzerfaust=13,
           crossbow=14, petrol_bomb=15, sten=16, stg44=17)


def calibrations(root=None):
    root = Path(root) if root else Path(__file__).resolve().parents[2]
    source = (root / 'vr/underground/weapon.c').read_text(encoding='utf-8')
    rows = re.findall(r'static const MohuVrWeaponCalibration k_(\w+)_calibration = '
                      r'\{(.*?)\n\};', source, re.S)
    result = {}
    for name, body in rows:
        vectors = re.findall(r'\{([^{}]+)\}', body)
        if len(vectors) != 6 or name not in IDS:
            raise ValueError('Changed calibration initializer schema')
        values = {key: [float(x.strip()) for x in row.split(',')]
                  for key, row in zip(('grip_pivot', 'muzzle', 'right', 'up',
                                       'forward', 'mount_offset_m'), vectors)}
        rest = body[body.rindex('}')+1:].strip().lstrip(',').strip()
        fields = rest.split(',')
        values.update(zip(('model_units_per_metre', 'reference_length_m', 'forward_span_units'),
                          map(float, fields[:3])))
        if any(len(v) != 3 for v in values.values() if isinstance(v, list)):
            raise ValueError('Malformed calibration vector')
        result[IDS[name]] = values
    if set(result) != set(IDS.values()):
        raise ValueError('Incomplete shipped calibration set')
    return result
