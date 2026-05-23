---
name: review_pe_device
description: Reviews a Provider Edge (PE) device, focusing on customer-facing services and core connectivity.
tags: [pe-router, bgp, vpn, mpls, health]
---

# Review PE Device

## Steps

1. Perform a general device health check: CPU, memory, hardware status, logs for
   critical errors, and uptime.

2. Check the status of all core-facing interfaces (links to P routers). Verify they
   are up, error-free, and appropriately utilized. Note any high utilization or errors.

3. Verify BGP sessions with Route Reflectors (RRs) and other PEs. Ensure sessions are
   established and prefix counts are nominal.

4. Review status of customer-facing interfaces. Note any down interfaces or interfaces
   with significant errors or discards. Investigate any anomalies.

5. Check VRF (VPN Routing and Forwarding) instance status. For key VRFs, verify route
   targets, route distinguishers, and interfaces associated.

6. Examine MPLS LDP or Segment Routing (SR-MPLS) adjacencies and forwarding state
   towards the core. Ensure adjacencies are up and label forwarding tables are
   consistent.

7. Briefly review any configured QoS policies on customer interfaces to ensure they
   are applied and check for drops in critical queues.

8. Check for any alarms specific to PE functionality (e.g., VPLS, L3VPN service
   alarms).
