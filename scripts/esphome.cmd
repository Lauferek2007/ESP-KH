@echo off
setlocal

if exist "%~dp0..\..\.venv-esphome\Scripts\python.exe" (
  "%~dp0..\..\.venv-esphome\Scripts\python.exe" -m esphome %*
  exit /b %errorlevel%
)

py -3.13 -m esphome %*
