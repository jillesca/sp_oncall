---
name: check_interface_status
description: Verifies interface operational state, error counters, and utilization.
tags: [interface, troubleshooting, health]
---

# Check Interface Status

## Steps

1. Retrieve a summary of all interfaces, noting their administrative and operational
   statuses. Identify any interfaces that are administratively up but operationally
   down, or unexpectedly down.

2. For any specific interface mentioned in the query, or for interfaces showing issues,
   obtain detailed statistics including traffic rates (input/output), packet counts, and
   error counts (e.g., CRC errors, input errors, output drops).

3. Analyze error counters. A small number of errors might be normal over a long period,
   but rapidly incrementing errors or specific types (CRCs, giants, runts) indicate
   physical layer or SFP issues. Output drops may indicate congestion.

4. Check the interface description and connected endpoint information (if available via
   LLDP/CDP) to understand its role and connectivity.

5. If an interface is down, investigate logs for messages related to that interface for
   clues about why it went down (e.g., link flap, SFP issue, configuration change).
