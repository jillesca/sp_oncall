---
name: review_p_device
description: Reviews a Provider (P) core router, focusing on transit, routing stability, and MPLS.
tags: [p-router, core, isis, mpls, health]
---

# Review P Device

## Steps

1. Perform a general device health check: CPU, memory, hardware status (especially
   line cards and optics), logs for critical errors, and uptime.

2. Check the status of all core-facing interfaces. These are high-capacity links, so
   pay close attention to operational status, error counts (especially CRC, framing
   errors), and utilization. Sustained high utilization may indicate a need for
   capacity planning.

3. Verify IGP (OSPF or IS-IS) adjacencies. Ensure all adjacencies are full/up and
   there are no recent flaps. Check for consistent IGP database size.

4. Verify BGP sessions if the P router peers with RRs or other P devices (e.g., in an
   inter-AS scenario). Ensure sessions are established.

5. Examine MPLS LDP or Segment Routing (SR-MPLS) adjacencies and forwarding state.
   Ensure all LDP/SR adjacencies are up with neighbors, and that the LFIB/MPLS
   forwarding table is populated correctly. Check for stale or missing entries.

6. Review core-facing interface QoS counters if applicable, especially for drops in
   high-priority traffic classes.

7. Check for any hardware alarms or packet forwarding engine issues.
