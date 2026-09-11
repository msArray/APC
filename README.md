# APC
Singapore RP 2026 Summer internship

put credentials.json

create exe  

`uv run pyarmor gen --pack onefile -r main.py`

if main.spec file's EXE arg console isn't False, Please fix to False.

``
exe = EXE(
    ...
    console=False,
    ...
)
``

exe file will output dist dirctory.

to work this APC, you need put credentials.json at same directory existing exe file.