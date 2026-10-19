@echo off
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -Command "& '.\iniciar.ps1' -PopularBanco"
if errorlevel 1 pause

