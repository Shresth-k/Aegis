@echo off
title Google Cloud Authentication - aegis-509604
echo ===================================================================
echo   Authenticating Google Cloud SDK and Application Default Credentials
echo   Target Project: aegis-509604 (435587786147)
echo ===================================================================
echo.
echo Opening browser for Google Cloud authorization...
call "C:\Users\KIIT\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd" auth login --update-adc
echo.
echo Setting active project to aegis-509604...
call "C:\Users\KIIT\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd" config set project aegis-509604
echo.
echo Authentication complete! You may now close this window.
pause
