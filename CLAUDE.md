# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a PyQt5-based automation tool (自动化任务管理工具) for managing automated tasks including software launching, window control, coordinate clicking, and account pool management via Redis. The tool is designed for game automation workflows.

## Development Commands

### Running the Application
```bash
python main.py
```

### Installing Dependencies
```bash
pip install -r requirements.txt
```

### Building Executable
```bash
# Using batch script (recommended)
打包exe_v3.bat

# Or directly with Python
python build_exe_v3.py
```


## Architecture Overview

### Core Components

- **main.py**: Main PyQt5 GUI application
- **window_controller.py**: Handles window finding, activation, and positioning
- **click_sequence.py**: Executes automated mouse clicks and text input
- **account_manager.py**: Redis-based account pool management
- **process_monitor.py**: Monitors target process lifecycle
- **coordinate_recorder.py**: Records screen coordinates using Ctrl+3 hotkey
- **runtime_logger.py**: Logs runtime statistics

### Automation Flow

1. Load configuration from config.json (software paths, Redis connection, coordinates)
2. Acquire idle account from Redis pool
3. Launch target software and position window
4. Execute coordinate-based clicks (username/password input)
5. Monitor secondary process launch and lifecycle
6. Return account to pool when process exits
7. Loop continues

### Configuration

Configuration is stored in `config.json` with:
- Software paths and process names
- Redis connection details
- Recorded coordinates for automation
- Timing intervals and retry limits

### Packaging

Uses PyInstaller with custom spec file (`自动化任务管理工具_v3.spec`) to create standalone executable in `release_v3/` directory. The build process is automated through `build_exe_v3.py`.

## Key Technical Details

### Mouse & Keyboard Automation
- Uses pyautogui with fast movement (`duration=0.1`)
- Clipboard-based text input to avoid IME issues
- Absolute screen coordinates recorded via global hotkey

### Window Management
- Multiple window activation strategies for reliability
- Automatic centering and focus management
- Process-based window finding

### Account Management
- Redis-based account pool with idle/busy status
- Automatic account acquisition and release
- Support for multiple concurrent instances

### Error Handling
- Comprehensive logging throughout all components
- Retry mechanisms for network and automation operations
- Graceful fallbacks for input methods