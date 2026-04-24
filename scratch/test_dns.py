import socket
import sys

host = "db.nlbrnvmswldccvwdfiqj.supabase.co"
print(f"Resolving {host}...")

try:
    # Try IPv4
    print("Trying IPv4 (AF_INET)...")
    addr_info = socket.getaddrinfo(host, 5432, socket.AF_INET)
    print(f"IPv4 addresses: {addr_info}")
except Exception as e:
    print(f"IPv4 failed: {e}")

try:
    # Try IPv6
    print("Trying IPv6 (AF_INET6)...")
    addr_info = socket.getaddrinfo(host, 5432, socket.AF_INET6)
    print(f"IPv6 addresses: {addr_info}")
except Exception as e:
    print(f"IPv6 failed: {e}")

try:
    # Try default
    print("Trying default (AF_UNSPEC)...")
    addr_info = socket.getaddrinfo(host, 5432, socket.AF_UNSPEC)
    print(f"Default addresses: {addr_info}")
except Exception as e:
    print(f"Default failed: {e}")
