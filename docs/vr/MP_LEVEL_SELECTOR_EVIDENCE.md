# Underground multiplayer level-selector evidence

Date: 2026-10-26

This is the W2.1 measurement only. It does not add an MP eye-frustum override,
change the P1-only renderer, redirect shots or make a physical-headset claim.

## Fixture and invocation

The probe used a fresh copy of root MP slot 1: P38 in loadout slot 0, zero
weapon switches, stationary P2 and no firing. It loaded the ordinary PGXP save,
ran the native two-player frame and recorded both natural scene-callback call
sites. The final capture observed:

| PC | Meaning | Count |
| --- | --- | ---: |
| `80054BC4` | native frame function guarded by the existing MP view contract | 296 frames |
| `80054CD4` | first natural `8006E9D8` call site | 296 |
| `80054D54` | second natural `8006E9D8` call site | 296 |
| `8006E9D8` | native MP scene dispatch | 592 |

The two scene calls are the two native views in the frame. The probe did not
attach to an operator process. Source saves, thumbnails, controller preferences
and SteamVR settings matched their pre-run hashes, and no game or debug listener
remained.

## Complete code contracts

| Function | Address | Size | FNV-1a | Caller / role |
| --- | --- | ---: | --- | --- |
| Native frame | `80054BC4` | `0x200` | `6CDFBB75` | Natural MP frame entry |
| Scene dispatch | `8006E9D8` | `0x180` | `04C21F46` | JAL from `80054CD4`, `80054D54` |
| Level-node callback | `8006C61C` | `0x290` | `A2AAC71B` | JALR from scene dispatch |
| Visibility selector | `80096EF4` | `0x90` | `273C8059` | JAL from `8006C664`, `8006C688` |
| Visibility helper | `80096AC8` | `0x428` | `77C2060F` | JAL from `80096F70` |

The scene call words are `0C01BA76`, with return addresses `80054CDC` and
`80054D5C`. The selector call words are `0C025BBD`, with return addresses
`8006C66C` and `8006C690`. The helper call word is `0C025AB2`, returning at
`80096F78`.

The compact receipt at
[weapon-mp-level-selector-receipt.json](../../vr/proof/weapon-mp-level-selector-receipt.json)
retains the addresses, sizes and SHA-256/FNV values. The ignored raw receipt
under
`analysis/vr-baseline/weapon-mesh-mapping/w2-level-selector-20261026-final2/`
retains all 690 disassembled instructions across the five complete functions.

## MP selection shape

`8006E9D8` accepts context `800A0B08` and the list at `[800A35CC]`. In the final
fixture the list root was `8014A450` with 26 live nodes:

- two unarmed header nodes;
- 21 level nodes whose `+0x384` callback is `8006C61C`;
- one special node, `801A8C40`, whose callback is `80057920`;
- two player nodes whose callback is `80082598`.

The 21 level nodes are the flat native queue in traversal order:

```text
80129980 8012AEE0 8012C440 8012D9A0 8012EF00 80130460 801319C0
80132ED0 801343E0 801358F0 80136E00 80138310 80139820 8013AD30
8013C240 8013D750 8013EC60 80140170 80141680 80142B90 801440A0
```

At this fixture every level node had:

| Node field | Observed value |
| --- | --- |
| Visibility mask at `+0x0C` | `0x07020200` |
| Render flags at `+0x10` | `0x00400211` |
| Auxiliary flags at `+0x14` | `0x08000001` |

The complete `8006C61C` callback reads `+0x0C` before selection. Its low bit and
`0x0300` field select the `80096EF4` path; `0x0200` and `0x0100` participate in
later render suppression. The selected-player node takes the explicit
`[800A35C4]` identity path rather than being culled as an ordinary level node.

`80096EF4` constructs an object/model AABB from the measured `+0x2F4/+0x2F6/
+0x2F8` bounds and `+0x2FC` radius, then calls `80096AC8`. The helper performs
the camera-space visibility test and returns the selector result. The callback
uses that result to choose the object render path; it does not queue a separate
PVS leaf list.

This is the key difference from the completed SP path. Underground SP uses the
710-instruction `80099960` selector and writes a 1000-leaf queue at
`800B74B8`. That address and queue are not resident/executed in this MP fixture.
MP W2.1 must therefore preserve the flat scene-list/per-object selector contract
instead of transplanting the SP PVS queue or mask addresses.

## Evidence

- [Compact selector receipt](../../vr/proof/weapon-mp-level-selector-receipt.json)
- Raw receipt:
  `analysis/vr-baseline/weapon-mesh-mapping/w2-level-selector-20261026-final2/receipt.json`
- Probe: `vr/tools/probe_mp_level_selector.py`

The raw receipt records the tested diagnostic executable, probe source hash,
complete disassembly, both player snapshots, zero shot/switch changes and the
cleanup result.

Reproduce with the one diagnostic build and a fresh, nonexistent output child:

```powershell
python vr/tools/probe_mp_level_selector.py analysis/vr-baseline/weapon-mesh-mapping/w2-selector-repro --proof analysis/vr-baseline/weapon-mesh-mapping/w2-selector-repro-proof.json
```

## Limits

- W2.1 is read-only mapping; no MP visibility override has been implemented.
- The flat list and masks are recorded for this fixture and its live scene
  generation. W2.2 must retain complete code/layout guards and fall back native.
- Zero, both 90-degree headings and the near-wall eye-frustum controls passed
  in W2.3; lateral replay remains a separate rendering control.
- MP input converter/dispatcher controls passed in W2.4 and the desktop
  input/lifecycle matrix passed in W2.5. Physical input remains open.
