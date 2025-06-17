# Linux Debugging Commands Reference

A comprehensive guide to Linux commands used for debugging applications, services, and system issues.

## Table of Contents
1. [Process Management](#process-management)
2. [Service Management (systemd)](#service-management-systemd)
3. [Log Analysis](#log-analysis)
4. [File and Directory Operations](#file-and-directory-operations)
5. [Network and Ports](#network-and-ports)
6. [Permissions and Users](#permissions-and-users)
7. [Real-time Monitoring](#real-time-monitoring)
8. [Docker Debugging](#docker-debugging)
9. [Text Processing and Searching](#text-processing-and-searching)
10. [System Information](#system-information)

## Process Management

### ps - Process Status
Shows currently running processes.

```bash
# Show all processes with full details
ps aux

# Find specific process
ps aux | grep python
ps aux | grep crucible

# Show process tree
ps auxf

# Show only your processes
ps u
```

**Common columns:**
- USER: Process owner
- PID: Process ID
- %CPU: CPU usage
- %MEM: Memory usage
- COMMAND: Command that started the process

### kill - Terminate Processes
```bash
# Graceful termination
kill <PID>

# Force kill
kill -9 <PID>

# Kill all processes matching name
killall python
pkill -f "crucible"
```

## Service Management (systemd)

### systemctl - Control systemd Services
```bash
# Check service status
sudo systemctl status crucible-platform

# Start/stop/restart service
sudo systemctl start crucible-platform
sudo systemctl stop crucible-platform
sudo systemctl restart crucible-platform

# Enable/disable service at boot
sudo systemctl enable crucible-platform
sudo systemctl disable crucible-platform

# Reload systemd after config changes
sudo systemctl daemon-reload

# List all services
systemctl list-units --type=service
```

### systemctl cat - View Service Configuration
```bash
# View service file
sudo systemctl cat crucible-platform

# View specific settings
sudo systemctl cat crucible-platform | grep ExecStart
sudo systemctl cat crucible-platform | grep -E "User|Group|WorkingDirectory"
```

### journalctl - View systemd Logs
```bash
# View logs for a service
sudo journalctl -u crucible-platform

# Follow logs in real-time (like tail -f)
sudo journalctl -u crucible-platform -f

# Show last N lines
sudo journalctl -u crucible-platform -n 50

# Show logs since a time
sudo journalctl -u crucible-platform --since "10 minutes ago"
sudo journalctl -u crucible-platform --since "2024-06-16 10:00:00"

# No pager (output all at once)
sudo journalctl -u crucible-platform --no-pager

# Grep through logs
sudo journalctl -u crucible-platform | grep ERROR
sudo journalctl -u crucible-platform | grep -A5 -B5 "permission denied"
```

## Log Analysis

### tail - View End of Files
```bash
# View last 10 lines (default)
tail /var/log/syslog

# View last N lines
tail -n 50 /var/log/syslog
tail -50 /var/log/syslog

# Follow file in real-time
tail -f /var/log/syslog

# Follow multiple files
tail -f /var/log/syslog /var/log/auth.log
```

### head - View Beginning of Files
```bash
# View first 10 lines
head /var/log/syslog

# View first N lines
head -n 20 /var/log/syslog
```

### less/more - Page Through Files
```bash
# Page through file
less /var/log/syslog

# Commands in less:
# /searchterm - Search forward
# ?searchterm - Search backward
# n - Next match
# N - Previous match
# G - Go to end
# g - Go to beginning
# q - Quit
```

## File and Directory Operations

### ls - List Directory Contents
```bash
# Basic listing
ls

# Detailed listing with permissions
ls -la
ls -l

# Sort by time (newest first)
ls -lat

# Human-readable sizes
ls -lah

# Only show directories
ls -ld */

# Show hidden files
ls -a
```

**Understanding ls -la output:**
```
-rw-r--r-- 1 ubuntu ubuntu 1234 Jun 16 10:00 file.txt
│├─┼─┼───┘ │ │      │      │    │            │
││ │ │     │ │      │      │    │            └── Filename
││ │ │     │ │      │      │    └── Modification time
││ │ │     │ │      │      └── Size in bytes
││ │ │     │ │      └── Group owner
││ │ │     │ └── User owner
││ │ │     └── Number of hard links
││ │ └── Other permissions (r=read, w=write, x=execute)
││ └── Group permissions
│└── Owner permissions
└── File type (- = file, d = directory, l = symlink)
```

### find - Search for Files
```bash
# Find files by name
find /path -name "*.py"
find . -name "*.log"

# Find files by type
find /path -type f  # files
find /path -type d  # directories

# Find files modified in last N days
find /path -mtime -7  # modified in last 7 days

# Execute command on found files
find . -name "*.py" -exec grep "TODO" {} \;
find . -name "*.tmp" -exec rm {} \;
```

### du - Disk Usage
```bash
# Show directory sizes
du -sh *
du -sh /var/log

# Show all subdirectories
du -h --max-depth=1
```

### chmod - Change Permissions
```bash
# Make file executable
chmod +x script.sh

# Set specific permissions (owner=rw, group=r, others=r)
chmod 644 file.txt
chmod 755 directory/

# Recursive
chmod -R 755 directory/
```

**Permission numbers:**
- 4 = read (r)
- 2 = write (w)
- 1 = execute (x)
- Sum them: 7=rwx, 6=rw-, 5=r-x, 4=r--

### chown - Change Ownership
```bash
# Change owner
sudo chown ubuntu file.txt

# Change owner and group
sudo chown ubuntu:ubuntu file.txt

# Recursive
sudo chown -R ubuntu:ubuntu directory/
```

## Network and Ports

### ss - Socket Statistics (modern netstat)
```bash
# Show listening TCP ports
sudo ss -tlnp

# Show all connections
ss -a

# Show process using port
sudo ss -tlnp | grep :8080
```

**Common options:**
- -t: TCP
- -u: UDP
- -l: Listening only
- -n: Numeric (don't resolve names)
- -p: Show process

### netstat - Network Statistics (older tool)
```bash
# Show listening ports
sudo netstat -tlnp

# Show all connections
netstat -a
```

### curl - HTTP Client
```bash
# Simple GET
curl http://localhost:8080

# POST with JSON
curl -X POST http://localhost:8080/api/endpoint \
  -H "Content-Type: application/json" \
  -d '{"key": "value"}'

# Follow redirects
curl -L http://example.com

# Show headers
curl -I http://example.com

# Save to file
curl -o output.html http://example.com

# Show request/response details
curl -v http://localhost:8080
```

### lsof - List Open Files
```bash
# Show process using port
sudo lsof -i :8080

# Show files opened by process
sudo lsof -p <PID>

# Show network connections
sudo lsof -i
```

## Permissions and Users

### whoami - Current User
```bash
whoami  # Shows current username
```

### id - User and Group Info
```bash
# Show current user's info
id

# Show specific user's info
id ubuntu
```

### sudo - Execute as Root
```bash
# Run command as root
sudo command

# Run command as specific user
sudo -u www-data command

# Open root shell
sudo -i
sudo su
```

### groups - Show Group Memberships
```bash
# Show current user's groups
groups

# Show specific user's groups
groups ubuntu
```

### umask - Default Permissions
```bash
# Show current umask
umask

# Set umask (e.g., 022 = new files will be 644)
umask 022
```

## Real-time Monitoring

### top/htop - Process Monitor
```bash
# Basic process monitor
top

# Better process monitor (if installed)
htop

# In top:
# Press 'M' - Sort by memory
# Press 'P' - Sort by CPU
# Press 'k' - Kill process
# Press 'q' - Quit
```

### watch - Repeat Command
```bash
# Run command every 2 seconds
watch df -h

# Run every N seconds
watch -n 5 'ls -la /tmp'

# Highlight differences
watch -d 'ls -la /tmp/*.py'
```

### iostat - I/O Statistics
```bash
# Show CPU and I/O stats
iostat

# Update every N seconds
iostat 2
```

### vmstat - Virtual Memory Statistics
```bash
# Show memory stats
vmstat

# Update every N seconds
vmstat 2
```

## Docker Debugging

### docker ps - List Containers
```bash
# Show running containers
docker ps

# Show all containers (including stopped)
docker ps -a

# Show with full command
docker ps --no-trunc
```

### docker logs - Container Logs
```bash
# Show logs
docker logs <container_id>

# Follow logs
docker logs -f <container_id>

# Show last N lines
docker logs --tail 50 <container_id>
```

### docker exec - Execute in Container
```bash
# Run command in container
docker exec <container_id> ls -la

# Open shell in container
docker exec -it <container_id> /bin/bash
docker exec -it <container_id> sh
```

### docker inspect - Container Details
```bash
# Show all details
docker inspect <container_id>

# Get specific field
docker inspect <container_id> -f '{{.State.Status}}'
```

## Text Processing and Searching

### grep - Search Text
```bash
# Basic search
grep "error" file.log

# Case insensitive
grep -i "error" file.log

# Show line numbers
grep -n "error" file.log

# Show context (lines before/after)
grep -A 5 -B 5 "error" file.log  # 5 lines after, 5 lines before
grep -C 3 "error" file.log        # 3 lines context

# Recursive search
grep -r "TODO" .
grep -rn "function_name" /path/to/code

# Exclude files
grep -r "TODO" . --exclude="*.pyc"

# Regular expressions
grep -E "error|warning|fatal" file.log

# Invert match (show lines NOT matching)
grep -v "DEBUG" file.log
```

### awk - Text Processing
```bash
# Print specific columns
ps aux | awk '{print $1, $2}'  # Print user and PID

# Sum column
df | awk '{sum += $3} END {print sum}'

# Filter by condition
ps aux | awk '$3 > 50 {print $0}'  # Processes using >50% CPU
```

### sed - Stream Editor
```bash
# Replace text
sed 's/old/new/g' file.txt

# Delete lines
sed '/pattern/d' file.txt

# In-place edit
sed -i 's/old/new/g' file.txt
```

### cut - Extract Columns
```bash
# Cut by delimiter
cut -d':' -f1 /etc/passwd  # Get usernames

# Cut by character position
cut -c1-10 file.txt
```

### sort/uniq - Sort and Deduplicate
```bash
# Sort lines
sort file.txt

# Sort numerically
sort -n file.txt

# Sort by column
sort -k2 file.txt

# Remove duplicates
sort file.txt | uniq

# Count occurrences
sort file.txt | uniq -c
```

## System Information

### uname - System Info
```bash
# Kernel name
uname

# All info
uname -a

# Kernel version
uname -r
```

### df - Disk Free Space
```bash
# Show disk usage
df

# Human readable
df -h

# Show filesystem type
df -T
```

### free - Memory Usage
```bash
# Show memory
free

# Human readable
free -h

# Show in MB
free -m
```

### uptime - System Uptime
```bash
uptime  # Shows uptime and load average
```

### dmesg - Kernel Messages
```bash
# Show kernel messages
sudo dmesg

# Follow new messages
sudo dmesg -w

# Show last N lines
sudo dmesg | tail -50
```

## Useful Command Combinations

### Finding and Killing Processes
```bash
# Find and kill all python processes
ps aux | grep python | awk '{print $2}' | xargs kill

# Kill process using port
sudo lsof -t -i:8080 | xargs kill
```

### Log Analysis Patterns
```bash
# Count errors by type
grep ERROR app.log | cut -d' ' -f5- | sort | uniq -c | sort -nr

# Show errors with timestamps
grep ERROR app.log | grep "2024-06-16"

# Monitor log for specific pattern
tail -f app.log | grep --line-buffered ERROR
```

### File Cleanup
```bash
# Delete old log files
find /var/log -name "*.log" -mtime +30 -delete

# Find large files
find / -type f -size +100M 2>/dev/null

# Clean temp files
find /tmp -name "*.tmp" -mtime +1 -delete
```

### Service Debugging
```bash
# Full service debug workflow
sudo systemctl status myservice
sudo journalctl -u myservice -n 100 --no-pager
sudo systemctl cat myservice
ps aux | grep myservice
```

## Tips and Tricks

1. **Pipe (`|`)**: Send output of one command to another
   ```bash
   command1 | command2
   ```

2. **Redirect (`>`, `>>`)**: Save output to file
   ```bash
   command > file.txt   # Overwrite
   command >> file.txt  # Append
   ```

3. **Background (`&`)**: Run command in background
   ```bash
   long-running-command &
   ```

4. **Command substitution (`$()` or backticks)**: Use command output as argument
   ```bash
   echo "Current time: $(date)"
   ```

5. **Multiple commands**:
   ```bash
   command1 && command2  # Run command2 only if command1 succeeds
   command1 || command2  # Run command2 only if command1 fails
   command1 ; command2   # Run both regardless
   ```

6. **History navigation**:
   - `!!` - Run last command
   - `!123` - Run command #123 from history
   - `!grep` - Run last command starting with 'grep'
   - `Ctrl+R` - Search command history

Remember: Most commands have a `--help` option or man page (`man command`) for detailed documentation!