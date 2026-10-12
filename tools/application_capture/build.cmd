@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat"
cd /d "%~dp0"
cl /nologo /std:c++20 /O2 /MT /EHsc /LD application_input.cc bridge.cc /link /OUT:application_capture.dll ole32.lib Mmdevapi.lib
