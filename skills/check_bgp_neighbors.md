---
name: check_bgp_neighbors
description: Verifies BGP neighbor session state, uptime, and prefix counts.
tags: [bgp, routing, troubleshooting]
---

# Check BGP Neighbors

## Steps

1. List all configured BGP neighbors and their current session state. Focus on any
   neighbors not in the Established state.

2. For each BGP neighbor, check the session uptime. Short uptimes or flapping sessions
   indicate instability that needs investigation.

3. Verify the number of prefixes received from each neighbor. Compare with expected
   counts if known. Unusually low or zero received prefixes can indicate filtering
   issues or problems on the neighbor's side.

4. Check the number of prefixes advertised to each neighbor. Ensure this aligns
   with policy.

5. Examine BGP error messages or logs for any specific issues related to neighbor
   establishment or route exchange (e.g., authentication failures, hold timer expiry,
   notification messages).

6. If a specific neighbor is problematic, check its address family capabilities
   (e.g., IPv4 unicast, IPv6 unicast, VPNv4) and ensure they are correctly configured
   and active.
