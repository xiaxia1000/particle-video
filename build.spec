# -*- mode: python ; coding: utf-8 -*-

# block_cipher = None

# a = Analysis(
#     ['main.py'],
#     pathex=[],  # 修改为项目实际路径
#     binaries=[],
#     datas=[
#         ('C:/Users/xiayi/Desktop/vvv/test001/ffmpeg', 'ffmpeg'),
#         ('app_icon.ico', '.')
#     ],
#     hiddenimports=['win32timezone'],
#     hookspath=[],
#     hooksconfig={},
#     runtime_hooks=[],
#     excludes=[],
#     win_no_prefer_redirects=False,
#     win_private_assemblies=False,
#     cipher=block_cipher,
#     noarchive=False,
# )
# pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# exe = EXE(
#     pyz,
#     a.scripts,
#     a.binaries,
#     a.zipfiles,
#     a.datas,
#     [],
#     name='MyApp',
#     debug=False,
#     bootloader_ignore_signals=False,
#     strip=False,
#     upx=True,
#     upx_exclude=[],
#     runtime_tmpdir=None,
#     console=False,
#     icon='app_icon.ico',
#     disable_windowed_traceback=False,
#     argv_emulation=False,
#     target_arch=None,
#     codesign_identity=None,
#     entitlements_file=None,
# )



# -*- mode: python ; coding: utf-8 -*-

# block_cipher = None

# a = Analysis(
#     ['main.py'],
#     pathex=[],
#     binaries=[],
#     datas=[
#         ('ffmpeg/**/*', 'ffmpeg'),
#         ('app_icon.ico', '.'),
#     ],
#     hiddenimports=[
#         'win32timezone',
#         'cv2',
#         'PyQt5',
#         'numpy',
#         'PyQt5.QtCore',
#         'PyQt5.QtGui',
#         'PyQt5.QtWidgets'
#     ],
#     hookspath=[],
#     hooksconfig={},
#     runtime_hooks=[],
#     excludes=[],
#     win_no_prefer_redirects=False,
#     win_private_assemblies=False,
#     cipher=block_cipher,
#     noarchive=False,
# )
# pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# exe = EXE(
#     pyz,
#     a.scripts,
#     a.binaries,
#     a.zipfiles,
#     a.datas,
#     [],
#     name='VideoConverter',
#     debug=False,
#     bootloader_ignore_signals=False,
#     strip=False,
#     upx=True,
#     upx_exclude=[],
#     runtime_tmpdir=None,
#     console=False,
#     icon='app_icon.ico',  # 图标文件路径
#     disable_windowed_traceback=False,
#     argv_emulation=False,
#     target_arch=None,
#     codesign_identity=None,
#     entitlements_file=None,
# )



# -*- mode: python ; coding: utf-8 -*-


block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('ffmpeg/**/*', 'ffmpeg'),  # 递归包含所有FFmpeg文件
        ('app_icon.ico', '.'),
    ],
    hiddenimports=[
        'win32timezone',
        'cv2',
        'PyQt5',
        'numpy',
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtWidgets'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='VideoConverter',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False, # 控制台模式
    icon='app_icon.ico',
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)