# Debug Configuration Examples

Reference this file when starting debug sessions for specific languages, frameworks, or environments.

## Python

### Basic Script
```json
{
  "type": "python",
  "request": "launch",
  "program": "${file}",
  "stopOnEntry": false
}
```

### Django Application
```json
{
  "type": "python",
  "request": "launch",
  "program": "${workspaceFolder}/manage.py",
  "args": ["runserver", "--noreload"],
  "django": true,
  "justMyCode": false
}
```

### Flask Application
```json
{
  "type": "python",
  "request": "launch",
  "module": "flask",
  "env": {
    "FLASK_APP": "app.py",
    "FLASK_ENV": "development"
  },
  "args": ["run", "--no-debugger", "--no-reload"],
  "jinja": true
}
```

### FastAPI Application
```json
{
  "type": "python",
  "request": "launch",
  "module": "uvicorn",
  "args": ["main:app", "--reload"],
  "jinja": true
}
```

### Pytest Tests
```json
{
  "type": "python",
  "request": "launch",
  "module": "pytest",
  "args": ["tests/", "-v"]
}
```

### Attach to Running Process
```json
{
  "type": "python",
  "request": "attach",
  "connect": {
    "host": "localhost",
    "port": 5678
  }
}
```

## JavaScript/Node.js

### Basic Node Script
```json
{
  "type": "node",
  "request": "launch",
  "program": "${file}",
  "skipFiles": ["<node_internals>/**"]
}
```

### Express Application
```json
{
  "type": "node",
  "request": "launch",
  "program": "${workspaceFolder}/app.js",
  "skipFiles": ["<node_internals>/**"],
  "env": {
    "NODE_ENV": "development"
  }
}
```

### Node with TypeScript
```json
{
  "type": "node",
  "request": "launch",
  "program": "${workspaceFolder}/src/index.ts",
  "preLaunchTask": "tsc: build - tsconfig.json",
  "outFiles": ["${workspaceFolder}/dist/**/*.js"],
  "sourceMaps": true
}
```

### Jest Tests
```json
{
  "type": "node",
  "request": "launch",
  "program": "${workspaceFolder}/node_modules/.bin/jest",
  "args": ["--runInBand"],
  "console": "integratedTerminal",
  "internalConsoleOptions": "neverOpen"
}
```

### Next.js Application
```json
{
  "type": "node",
  "request": "launch",
  "program": "${workspaceFolder}/node_modules/.bin/next",
  "args": ["dev"],
  "cwd": "${workspaceFolder}",
  "runtimeArgs": ["--inspect"]
}
```

### Electron Application
```json
{
  "type": "node",
  "request": "launch",
  "name": "Electron Main",
  "runtimeExecutable": "${workspaceFolder}/node_modules/.bin/electron",
  "program": "${workspaceFolder}/main.js",
  "skipFiles": ["<node_internals>/**"]
}
```

## TypeScript (Direct)

### ts-node Script
```json
{
  "type": "node",
  "request": "launch",
  "runtimeArgs": ["-r", "ts-node/register"],
  "args": ["${file}"],
  "cwd": "${workspaceRoot}",
  "protocol": "inspector"
}
```

### Deno
```json
{
  "type": "node",
  "request": "launch",
  "program": "${file}",
  "runtimeExecutable": "deno",
  "runtimeArgs": ["run", "--inspect-wait", "--allow-all"],
  "attachSimplePort": 9229
}
```

## Rust

### Cargo Project
```json
{
  "type": "lldb",
  "request": "launch",
  "program": "${workspaceFolder}/target/debug/${workspaceFolderBasename}",
  "args": [],
  "cwd": "${workspaceFolder}",
  "preLaunchTask": "cargo build"
}
```

### Cargo Test
```json
{
  "type": "lldb",
  "request": "launch",
  "program": "${workspaceFolder}/target/debug/deps/${workspaceFolderBasename}-*",
  "args": ["--nocapture"],
  "cwd": "${workspaceFolder}",
  "preLaunchTask": "cargo test --no-run"
}
```

## Go

### Basic Go Program
```json
{
  "type": "go",
  "request": "launch",
  "mode": "debug",
  "program": "${file}"
}
```

### Go Tests
```json
{
  "type": "go",
  "request": "launch",
  "mode": "test",
  "program": "${workspaceFolder}",
  "args": ["-v"]
}
```

### Go Package
```json
{
  "type": "go",
  "request": "launch",
  "mode": "debug",
  "program": "${workspaceFolder}/cmd/myapp"
}
```

## C/C++

### GCC/Clang (Linux/macOS)
```json
{
  "type": "cppdbg",
  "request": "launch",
  "program": "${workspaceFolder}/build/myapp",
  "args": [],
  "stopAtEntry": false,
  "cwd": "${workspaceFolder}",
  "environment": [],
  "externalConsole": false,
  "MIMode": "gdb",
  "preLaunchTask": "build"
}
```

### LLDB (macOS)
```json
{
  "type": "lldb",
  "request": "launch",
  "program": "${workspaceFolder}/build/myapp",
  "args": [],
  "cwd": "${workspaceFolder}"
}
```

### MSVC (Windows)
```json
{
  "type": "cppvsdbg",
  "request": "launch",
  "program": "${workspaceFolder}/Debug/myapp.exe",
  "args": [],
  "stopAtEntry": false,
  "cwd": "${workspaceFolder}",
  "environment": []
}
```

## Java

### Java Application
```json
{
  "type": "java",
  "request": "launch",
  "mainClass": "com.example.Main",
  "projectName": "myproject"
}
```

### Spring Boot
```json
{
  "type": "java",
  "request": "launch",
  "mainClass": "com.example.Application",
  "projectName": "myproject",
  "args": "--spring.profiles.active=dev"
}
```

## C#/.NET

### .NET Console App
```json
{
  "type": "coreclr",
  "request": "launch",
  "program": "${workspaceFolder}/bin/Debug/net6.0/MyApp.dll",
  "args": [],
  "cwd": "${workspaceFolder}",
  "stopAtEntry": false,
  "console": "internalConsole"
}
```

### ASP.NET Core
```json
{
  "type": "coreclr",
  "request": "launch",
  "program": "${workspaceFolder}/bin/Debug/net6.0/MyWebApp.dll",
  "args": [],
  "cwd": "${workspaceFolder}",
  "env": {
    "ASPNETCORE_ENVIRONMENT": "Development"
  }
}
```

## Ruby

### Basic Ruby Script
```json
{
  "type": "Ruby",
  "request": "launch",
  "program": "${file}"
}
```

### Rails Application
```json
{
  "type": "Ruby",
  "request": "launch",
  "program": "${workspaceFolder}/bin/rails",
  "args": ["server"],
  "useBundler": true
}
```

## PHP

### PHP Script
```json
{
  "type": "php",
  "request": "launch",
  "program": "${file}",
  "cwd": "${workspaceFolder}",
  "port": 9003
}
```

### Laravel Application
```json
{
  "type": "php",
  "request": "launch",
  "program": "${workspaceFolder}/artisan",
  "args": ["serve"],
  "cwd": "${workspaceFolder}",
  "port": 9003
}
```

## Common Configuration Options

### Environment Variables
```json
{
  "env": {
    "DEBUG": "true",
    "API_KEY": "dev-key-123"
  }
}
```

### Working Directory
```json
{
  "cwd": "${workspaceFolder}/src"
}
```

### Command-Line Arguments
```json
{
  "args": ["--config", "dev.json", "--verbose"]
}
```

### Stop at Entry Point
```json
{
  "stopOnEntry": true  // Pause before executing first line
}
```

### Skip Files (Node.js)
```json
{
  "skipFiles": [
    "<node_internals>/**",
    "${workspaceFolder}/node_modules/**"
  ]
}
```

### Source Maps
```json
{
  "sourceMaps": true,
  "outFiles": ["${workspaceFolder}/dist/**/*.js"]
}
```

### Console Output
```json
{
  "console": "integratedTerminal",  // or "internalConsole", "externalTerminal"
  "internalConsoleOptions": "openOnSessionStart"
}
```

## VS Code Variables

Common variables usable in configurations:

- `${file}` - Current file path
- `${workspaceFolder}` - Workspace root path
- `${workspaceFolderBasename}` - Workspace folder name
- `${fileBasename}` - Current file name
- `${fileDirname}` - Current file's directory
- `${fileExtname}` - Current file extension
- `${cwd}` - Task runner's working directory
- `${env:VARIABLE}` - Environment variable

## Attach Configurations

### Python (Remote)
```json
{
  "type": "python",
  "request": "attach",
  "connect": {
    "host": "localhost",
    "port": 5678
  },
  "pathMappings": [
    {
      "localRoot": "${workspaceFolder}",
      "remoteRoot": "/app"
    }
  ]
}
```

### Node.js (Remote)
```json
{
  "type": "node",
  "request": "attach",
  "port": 9229,
  "address": "localhost",
  "localRoot": "${workspaceFolder}",
  "remoteRoot": "/usr/src/app"
}
```

### Docker Container
```json
{
  "type": "python",
  "request": "attach",
  "connect": {
    "host": "127.0.0.1",
    "port": 5678
  },
  "pathMappings": [
    {
      "localRoot": "${workspaceFolder}",
      "remoteRoot": "/code"
    }
  ]
}
```
