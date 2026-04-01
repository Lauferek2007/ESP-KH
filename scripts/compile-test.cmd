@echo off
setlocal
"%~dp0esphome.cmd" compile "%~dp0..\esphome\test-esp32.yaml"
