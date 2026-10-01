@echo off
title Quantum-Safe VPN Testbed
cd /d "%~dp0"
echo ======================================================================
echo           Starting Quantum-Safe VPN Desktop Interface
echo ======================================================================
python quantum_vpn_gui.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [-] An error occurred while launching the VPN app.
    echo Please make sure Python and cryptography are installed:
    echo     pip install cryptography
    echo.
    pause
)
