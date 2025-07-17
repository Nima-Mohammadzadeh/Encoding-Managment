# Directory Monitoring Performance Guide

## Overview

This application monitors job directories for real-time updates. With multiple users and large directory structures, monitoring can impact performance. This guide explains the optimizations and configuration options available.

## Performance Issues with Multi-User Environments

### Common Problems
- **Network Drive Monitoring**: File system watchers on network drives (Z:, Y:, etc.) are unreliable and slow
- **Excessive Directory Monitoring**: Monitoring 40+ directories consumes system resources
- **Race Conditions**: Multiple users creating jobs simultaneously can cause conflicts
- **Memory Usage**: Each monitored directory consumes memory
- **Network Traffic**: Constant monitoring generates network overhead

## Automatic Optimizations

### Network Drive Detection
The application automatically detects network drives and applies optimizations:

```
Network Drive (Z:\): Uses LIMITED monitoring mode
- Only monitors root directory
- Uses periodic refresh (every 30 seconds)
- Longer debounce timers (2+ seconds)
- Reduced real-time monitoring

Local Drive (C:\): Uses FULL monitoring mode  
- Monitors subdirectories (with limits)
- Real-time file system watching
- Faster debounce timers (500ms)
- Comprehensive monitoring
```

### Monitoring Limits
- **Maximum Directories**: 50 directories (configurable)
- **Maximum Depth**: 3 levels deep (configurable)  
- **Debounce Timer**: 500ms for local, 2000ms+ for network (configurable)

## Configuration Settings

### Available Settings
You can customize monitoring behavior by modifying these settings:

```python
# Enable/disable file system monitoring entirely
ENABLE_FILE_MONITORING = True/False

# Maximum directories to monitor simultaneously  
MAX_MONITORED_DIRECTORIES = 50

# Maximum directory depth to monitor
MAX_MONITORING_DEPTH = 3

# Debounce timer in milliseconds
REFRESH_DEBOUNCE_MS = 500

# Periodic refresh interval for network drives (ms)
PERIODIC_REFRESH_INTERVAL = 30000  # 30 seconds
```

### Recommended Settings by Environment

#### High Performance (Local Drives, Few Users)
```python
ENABLE_FILE_MONITORING = True
MAX_MONITORED_DIRECTORIES = 100
MAX_MONITORING_DEPTH = 4
REFRESH_DEBOUNCE_MS = 250
```

#### Balanced (Mixed Environment)
```python
ENABLE_FILE_MONITORING = True
MAX_MONITORED_DIRECTORIES = 50
MAX_MONITORING_DEPTH = 3
REFRESH_DEBOUNCE_MS = 500
```

#### Conservative (Network Drives, Many Users)
```python
ENABLE_FILE_MONITORING = True
MAX_MONITORED_DIRECTORIES = 25
MAX_MONITORING_DEPTH = 2
REFRESH_DEBOUNCE_MS = 1000
PERIODIC_REFRESH_INTERVAL = 60000  # 1 minute
```

#### Minimal (Large Networks, Performance Critical)
```python
ENABLE_FILE_MONITORING = False  # Disable real-time monitoring
# Users must use "Refresh Jobs" button manually
```

## Manual Refresh Option

### When Real-Time Monitoring is Problematic
If automatic monitoring causes issues, users can:

1. **Use Manual Refresh Button**: Click "Refresh Jobs" to update the list
2. **Disable Monitoring**: Set `ENABLE_FILE_MONITORING = False`
3. **Periodic-Only Mode**: Enable monitoring but rely on periodic refresh

### Benefits of Manual Refresh
- **No Performance Impact**: Zero monitoring overhead
- **Reliable**: Always shows current disk state
- **Multi-User Safe**: No file system conflicts
- **Network Friendly**: Minimal network traffic

## Troubleshooting Performance Issues

### Symptoms of Monitoring Problems
- Slow application startup
- High CPU usage
- Network timeouts
- Jobs not appearing/disappearing randomly
- Application freezing

### Solutions by Problem Type

#### Too Many Directories Being Monitored
```
Solution: Reduce MAX_MONITORED_DIRECTORIES
Current: 50 → Try: 25 or 10
```

#### Network Drive Issues  
```
Solution 1: Use manual refresh only
Set: ENABLE_FILE_MONITORING = False

Solution 2: Increase periodic interval
Set: PERIODIC_REFRESH_INTERVAL = 60000 (1 minute)
```

#### Multiple Users Conflicts
```
Solution 1: Stagger usage times
Solution 2: Use local working directories
Solution 3: Disable real-time monitoring
```

#### Large Directory Structures
```
Solution: Reduce monitoring depth
Set: MAX_MONITORING_DEPTH = 2 or 1
```

## Best Practices for Multi-User Environments

### Directory Structure
- Keep job directories shallow (max 3 levels deep)
- Limit number of subdirectories per level
- Use consistent naming conventions
- Clean up archived jobs regularly

### User Workflow
- Coordinate job creation timing when possible
- Use local directories for temporary work
- Copy to network drives only when complete
- Use manual refresh during heavy usage periods

### System Administration
- Monitor network drive performance
- Consider dedicated job servers for high-volume environments
- Implement automatic cleanup of old job directories
- Use SSD storage for frequently accessed directories

## Monitoring Status Information

### Console Output
The application logs monitoring status:

```
Setting up LIMITED network monitoring (performance mode)
Network debounce timer set to: 2000ms
Enabled periodic refresh every 30 seconds for network drive
Total directories being monitored: 25 (max: 50)
```

### Debug Information
Use the debug button (if enabled) to see:
- Current monitoring status
- Number of directories being watched
- Duplicate detection analysis
- Performance metrics

## Migration Strategies

### From Network to Local Monitoring
1. Set up local active jobs directory
2. Configure periodic sync to network drive
3. Enable full monitoring on local directory
4. Use network drive for archival only

### Gradual Performance Optimization
1. Start with default settings
2. Monitor application performance
3. Reduce limits if issues occur
4. Test with multiple users
5. Fine-tune based on usage patterns

---

For additional support or custom configuration needs, consult the application documentation or contact your system administrator. 