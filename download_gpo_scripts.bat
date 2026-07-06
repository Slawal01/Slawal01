@echo off
set GPO_DIR=C:\Users\S670847\OneDrive - Owens & Minor\Documents\GPO DATA
set BASE_URL=https://raw.githubusercontent.com/slawal01/slawal01/claude/gpo-repository-0km6v4

echo.
echo Downloading GPO scripts to: %GPO_DIR%
echo.

powershell -Command "Invoke-WebRequest -Uri '%BASE_URL%/vizient_extract.py' -OutFile '%GPO_DIR%\vizient_extract.py'"
echo   vizient_extract.py

powershell -Command "Invoke-WebRequest -Uri '%BASE_URL%/vizient_top_parent_csv.py' -OutFile '%GPO_DIR%\vizient_top_parent_csv.py'"
echo   vizient_top_parent_csv.py

powershell -Command "Invoke-WebRequest -Uri '%BASE_URL%/vizient_top_parent_members_csv.py' -OutFile '%GPO_DIR%\vizient_top_parent_members_csv.py'"
echo   vizient_top_parent_members_csv.py

powershell -Command "Invoke-WebRequest -Uri '%BASE_URL%/vizient_direct_parent_csv.py' -OutFile '%GPO_DIR%\vizient_direct_parent_csv.py'"
echo   vizient_direct_parent_csv.py

powershell -Command "Invoke-WebRequest -Uri '%BASE_URL%/vizient_member_load.py' -OutFile '%GPO_DIR%\vizient_member_load.py'"
echo   vizient_member_load.py

echo.
echo Done. All scripts saved to GPO DATA folder.
echo.
pause
