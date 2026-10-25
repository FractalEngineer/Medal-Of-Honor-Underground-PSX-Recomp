@echo off
setlocal
rem Local players must not inherit the diagnostic keyboard/all-controller merge.
set "PSX_DEV_INPUT=0"
rem Flat launch from the packaged root or the local build-release target.
for %%V in (
  PSX_OPENXR PSX_OPENXR_ENABLE PSX_LOAD_SLOT PSX_STEREO_SHED
  PSX_RENDER_PASS_VERIFY PSX_OPENXR_READY_FILE XR_RUNTIME_JSON
  MOHU_VR_OPENXR MOHU_VR_LEVEL_OFFSET_X MOHU_VR_STEREO_PROOF
  MOHU_VR_EYE_OFFSET MOHU_VR_EYE_OFFSET_ALL_SPANS MOHU_VR_EYE_RENDER_VIEW
  MOHU_VR_EYE_VIEW_OFFSET MOHU_VR_EYE_YAW_MDEG MOHU_VR_EYE_PITCH_MDEG
  MOHU_VR_EYE_HEAD_X_MILLI MOHU_VR_EYE_HEAD_Y_MILLI MOHU_VR_EYE_HEAD_Z_MILLI
  MOHU_VR_EYE_GUEST_SUBMIT MOHU_VR_REPLAY_FRAME_DRIVER
  MOHU_VR_STEREO_OT_ONLY MOHU_VR_STEREO_DUMP_DIR MOHU_VR_UNITS_PER_METER
  MOHU_VR_MENU_DISTANCE MOHU_VR_MENU_WIDTH
  PSX_VR_WEAPON_POSE MOHU_VR_WEAPON_POSE MOHU_VR_WEAPON_FLAT_PROBE
  MOHU_VR_WEAPON_SYNTHETIC_X MOHU_VR_WEAPON_SYNTHETIC_YAW_MDEG
  MOHU_VR_WEAPON_FORCE_TRACKING_LOSS MOHU_VR_WEAPON_TRACE
  MOHU_VR_MP_CONTROL
) do set "%%V="
set "FLAT_EXE=%~dp0Medal_of_Honor_Underground_Recompiled.exe"
if not exist "%FLAT_EXE%" set "FLAT_EXE=%~dp0build-release\Medal_of_Honor_Underground_Recompiled.exe"
if not exist "%FLAT_EXE%" (
    echo Game executable missing. Build build-release first.
    pause
    exit /b 1
)
pushd "%~dp0"
"%FLAT_EXE%" --game game.toml --no-launcher %*
set "FLAT_EXIT_CODE=%ERRORLEVEL%"
popd
if not "%FLAT_EXIT_CODE%"=="0" (
    echo Flat launch failed with code %FLAT_EXIT_CODE%.
    pause
)
exit /b %FLAT_EXIT_CODE%
