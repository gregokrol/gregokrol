@echo off
chcp 65001 >nul
title Sal Hacham - Server Status
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0windows\check-status.ps1"
echo.
pause
