---
name: troubleshoot_vpn_vrf
description: Troubleshoots a specific VPN VRF instance, focusing on routing, interfaces, and connectivity.
tags: [vpn, vrf, l3vpn, routing, troubleshooting]
---

# Troubleshoot VPN VRF

## Steps

1. Identify the specific VRF name from the query. Verify the VRF exists on the device.

2. Check the interfaces associated with this VRF. Ensure they are operationally up and
   configured correctly for the VRF.

3. Inspect the VRF routing table for expected prefixes. Check how routes are learned
   (e.g., BGP, static, connected, IGP within VRF if applicable).

4. Verify route targets (import/export) and route distinguishers for the VRF. Ensure
   they match the intended VPN topology.

5. If BGP is used for route distribution within the VRF context (e.g., PE-CE BGP or
   VPNv4 routes from core), check BGP neighbor status specific to this VRF. Verify
   prefixes are received and advertised as expected.

6. Attempt to ping or trace to key destinations within the VRF, or from the VRF to
   destinations reachable via it, if source ping/trace from VRF is supported.

7. Review logs for any messages specific to this VRF or its associated interfaces and
   routing protocols.

8. Check MPLS label information for prefixes in this VRF, ensuring proper VPN labels
   are associated.
