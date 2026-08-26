@echo off
chcp 65001 >nul
title Sal Hacham - Server Setup
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0windows\install-server.ps1"
echo.
pause
