Option Explicit

Dim shell, fileSystem, scriptFolder, projectFolder, pythonw, appScript, command

Set shell = CreateObject("WScript.Shell")
Set fileSystem = CreateObject("Scripting.FileSystemObject")
scriptFolder = fileSystem.GetParentFolderName(WScript.ScriptFullName)
projectFolder = fileSystem.GetParentFolderName(scriptFolder)
shell.CurrentDirectory = projectFolder
pythonw = projectFolder & "\runtime\pythonw.exe"
appScript = scriptFolder & "\RVC-Realtime-GUI.py"
command = Chr(34) & pythonw & Chr(34) & " -I " & Chr(34) & appScript & Chr(34)

shell.Run command, 0, False
