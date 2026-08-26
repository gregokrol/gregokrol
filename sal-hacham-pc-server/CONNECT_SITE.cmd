@echo off
chcp 65001 >nul
title Sal Hacham - Connect Site
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0windows\connect-site.ps1"
echo.
pause
