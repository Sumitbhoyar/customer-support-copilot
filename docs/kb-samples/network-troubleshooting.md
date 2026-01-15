---
title: Network connectivity troubleshooting
product: Connectivity Suite
version: 1.0
---

# Symptoms
- Cannot connect to VPN.
- Intermittent packet loss.
- High latency when accessing internal apps.

# Quick checks
1) Verify the VPN client is on the latest version.
2) Confirm credentials are not expired or locked.
3) Test another network (mobile hotspot) to rule out local ISP issues.

# Step-by-step resolution
1) Restart the VPN client and retry.
2) Flush DNS cache:
   - Windows: `ipconfig /flushdns`
   - macOS: `sudo dscacheutil -flushcache; sudo killall -HUP mDNSResponder`
3) Switch VPN protocol:
   - Try WireGuard → OpenVPN (UDP) → OpenVPN (TCP) in that order.
4) Check firewall:
   - Allow outbound UDP 1194 and TCP 443 to `vpn.example.com`.
5) Collect logs if still failing:
   - VPN client logs
   - `traceroute vpn.example.com`
   - Timestamp of failure and user ID

# When to escalate
- Repro on multiple networks and protocols.
- Consistent failure after credential reset.
- Packet loss >5% to VPN gateway.
