---
name: check_mpls_state
description: Checks MPLS (LDP, RSVP-TE, or Segment Routing) operational state on a device.
tags: [mpls, segment-routing, ldp, troubleshooting]
---

# Check MPLS State

## Steps

1. Verify that the relevant MPLS protocol (LDP, RSVP-TE, SR) is enabled globally and
   on core-facing interfaces.

2. For LDP: Check LDP neighbor adjacencies. Ensure sessions are Operational with all
   expected neighbors. Verify LDP discovery sources and transport addresses.

3. For LDP: Examine the LDP bindings table (LIB). Ensure local labels are generated
   for IGP prefixes and remote labels are received from LDP neighbors.

4. For Segment Routing (SR-MPLS): Check SR Global Block (SRGB) range and ensure it is
   consistent across the domain. Verify prefix-SIDs are being advertised by the IGP
   (OSPF/IS-IS) and installed in the forwarding plane.

5. For Segment Routing (SR-MPLS): Check adjacency-SIDs for relevant interfaces and
   ensure they are up.

6. For RSVP-TE: List configured TE tunnels. Check their operational state, path, and
   bandwidth allocation. Investigate any down or re-routing tunnels.

7. Examine the MPLS forwarding table (LFIB/FTN). For key prefixes, verify the correct
   labels and next-hops are installed. Look for missing or incorrect entries.

8. Review logs for any MPLS-related errors (e.g., LDP session flaps, label conflicts,
   SR programming errors, RSVP path errors).

9. Check interface statistics for MPLS traffic if available, ensuring packets are being
   labeled and forwarded correctly.
