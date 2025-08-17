from langchain_core.messages import AIMessage, ToolMessage

mpc_response = {
    "messages": [
        AIMessage(
            content="",
            additional_kwargs={
                "tool_calls": [
                    {
                        "index": 0,
                        "id": "call_E4nYXummW8wFyBKoGRdffwF3",
                        "function": {
                            "arguments": '{"device_name": "xrd-5"}',
                            "name": "get_system_info",
                        },
                        "type": "function",
                    },
                    {
                        "index": 1,
                        "id": "call_hAnzPop4qcXielLLCQwYPUM5",
                        "function": {
                            "arguments": '{"device_name": "xrd-5"}',
                            "name": "get_interface_info",
                        },
                        "type": "function",
                    },
                    {
                        "index": 2,
                        "id": "call_ejuN4FJRtn2JSJYV5MVKGQrg",
                        "function": {
                            "arguments": '{"device_name": "xrd-5", "include_details": false}',
                            "name": "get_mpls_info",
                        },
                        "type": "function",
                    },
                    {
                        "index": 3,
                        "id": "call_1x7s57U3h42tGzj0GTLGw3BO",
                        "function": {
                            "arguments": '{"device_name": "xrd-5", "protocol": "bgp,isis", "include_details": false}',
                            "name": "get_routing_info",
                        },
                        "type": "function",
                    },
                    {
                        "index": 4,
                        "id": "call_ctTQ4a380hy3FQOaqmjvdr9P",
                        "function": {
                            "arguments": '{"device_name": "xrd-5", "include_details": false}',
                            "name": "get_vpn_info",
                        },
                        "type": "function",
                    },
                    {
                        "index": 5,
                        "id": "call_3KJ4PgmWgKyulGDUYoI89oAF",
                        "function": {
                            "arguments": '{"device_name": "xrd-5", "minutes": "5", "show_all_logs": false}',
                            "name": "get_logs",
                        },
                        "type": "function",
                    },
                    {
                        "index": 6,
                        "id": "call_5n0IhO9PiZfLQxJ4qIFKVFFA",
                        "function": {
                            "arguments": '{"device_name": "xrd-5"}',
                            "name": "get_device_profile_api",
                        },
                        "type": "function",
                    },
                ]
            },
            response_metadata={
                "finish_reason": "tool_calls",
                "model_name": "gpt-5-nano-2025-08-07",
                "service_tier": "default",
            },
            id="run--0e2ac365-5e1e-4532-929e-0da2141268f8",
            tool_calls=[
                {
                    "name": "get_system_info",
                    "args": {"device_name": "xrd-5"},
                    "id": "call_E4nYXummW8wFyBKoGRdffwF3",
                    "type": "tool_call",
                },
                {
                    "name": "get_interface_info",
                    "args": {"device_name": "xrd-5"},
                    "id": "call_hAnzPop4qcXielLLCQwYPUM5",
                    "type": "tool_call",
                },
                {
                    "name": "get_mpls_info",
                    "args": {"device_name": "xrd-5", "include_details": False},
                    "id": "call_ejuN4FJRtn2JSJYV5MVKGQrg",
                    "type": "tool_call",
                },
                {
                    "name": "get_routing_info",
                    "args": {
                        "device_name": "xrd-5",
                        "protocol": "bgp,isis",
                        "include_details": False,
                    },
                    "id": "call_1x7s57U3h42tGzj0GTLGw3BO",
                    "type": "tool_call",
                },
                {
                    "name": "get_vpn_info",
                    "args": {"device_name": "xrd-5", "include_details": False},
                    "id": "call_ctTQ4a380hy3FQOaqmjvdr9P",
                    "type": "tool_call",
                },
                {
                    "name": "get_logs",
                    "args": {
                        "device_name": "xrd-5",
                        "minutes": "5",
                        "show_all_logs": False,
                    },
                    "id": "call_3KJ4PgmWgKyulGDUYoI89oAF",
                    "type": "tool_call",
                },
                {
                    "name": "get_device_profile_api",
                    "args": {"device_name": "xrd-5"},
                    "id": "call_5n0IhO9PiZfLQxJ4qIFKVFFA",
                    "type": "tool_call",
                },
            ],
        ),
        ToolMessage(
            content='{\n  "device_name": "xrd-5",\n  "ip_address": "10.10.20.105",\n  "nos": "iosxr",\n  "operation_type": "system_info",\n  "status": "success",\n  "data": {\n    "system_data": {\n      "hostname": "xrd-5",\n      "current_datetime": "2025-08-17T10:04:26.726+00:00",\n      "software_version": "24.4.1.26I",\n      "timezone": "Universal",\n      "memory_physical": "25195245568",\n      "grpc_servers": [\n        {\n          "name": "DEFAULT",\n          "enable": true,\n          "port": 57777,\n          "transport_security": false,\n          "listen_addresses": [\n            "ANY"\n          ]\n        }\n      ],\n      "logging": [],\n      "message": {\n        "msg": "RP/0/RP0/CPU0Aug 17 04:46:38.250 UTC: xrd_freeze_monitor[266]: %PLATFORM-XRD-4-FREEZE_MONITOR_CHECK_WARNING : XRd freeze-monitor hit a delay of 100 ms. Possible freeze of host or VM ",\n        "priority": 188,\n        "app_name": "xrd_freeze_monitor"\n      },\n      "users": [],\n      "boot_time": "1753115100000000000",\n      "boot_time_human": "2025-07-21 16:25:00 UTC",\n      "uptime": "26d 17h 39m 26s"\n    },\n    "summary": {}\n  },\n  "metadata": {},\n  "error_response": null,\n  "feature_not_found_response": null\n}',
            name="get_system_info",
            id="30ddf79e-74bb-41fb-8288-64a4c8439d37",
            tool_call_id="call_E4nYXummW8wFyBKoGRdffwF3",
        ),
        ToolMessage(
            content='{\n  "device_name": "xrd-5",\n  "ip_address": "10.10.20.105",\n  "nos": "iosxr",\n  "operation_type": "interface_brief",\n  "status": "success",\n  "data": {\n    "interfaces": [\n      {\n        "name": "GigabitEthernet0/0/0/0",\n        "admin_status": "UP",\n        "oper_status": "UP",\n        "ip_address": "100.105.106.105/255.255.255.0"\n      },\n      {\n        "name": "Null0",\n        "admin_status": "UP",\n        "oper_status": "UP"\n      },\n      {\n        "name": "Loopback0",\n        "admin_status": "UP",\n        "oper_status": "UP",\n        "ip_address": "100.100.100.105/255.255.255.255"\n      },\n      {\n        "name": "GigabitEthernet0/0/0/1",\n        "admin_status": "UP",\n        "oper_status": "UP",\n        "ip_address": "100.103.105.105/255.255.255.0"\n      },\n      {\n        "name": "GigabitEthernet0/0/0/3",\n        "admin_status": "UP",\n        "oper_status": "UP",\n        "ip_address": "100.105.108.105/255.255.255.0"\n      },\n      {\n        "name": "GigabitEthernet0/0/0/2",\n        "admin_status": "UP",\n        "oper_status": "UP",\n        "ip_address": "100.101.105.105/255.255.255.0"\n      },\n      {\n        "name": "Loopback1",\n        "admin_status": "UP",\n        "oper_status": "UP",\n        "ip_address": "101.103.105.255/255.255.255.255"\n      },\n      {\n        "name": "MgmtEth0/RP0/CPU0/0",\n        "admin_status": "UP",\n        "oper_status": "UP",\n        "ip_address": "10.10.20.105/255.255.255.0"\n      }\n    ],\n    "summary": {\n      "total_interfaces": 8,\n      "admin_up": 8,\n      "admin_down": 0,\n      "oper_up": 8,\n      "oper_down": 0,\n      "with_ip": 7,\n      "with_vrf": 0\n    },\n    "interface_count": 8\n  },\n  "metadata": {\n    "is_single_interface": false,\n    "operation_details": "Retrieved summary of all interfaces"\n  },\n  "error_response": null,\n  "feature_not_found_response": null\n}',
            name="get_interface_info",
            id="61e8af59-2452-4298-863b-a447d9e249fc",
            tool_call_id="call_hAnzPop4qcXielLLCQwYPUM5",
        ),
        ToolMessage(
            content='{\n  "device_name": "xrd-5",\n  "ip_address": "10.10.20.105",\n  "nos": "iosxr",\n  "operation_type": "mpls_info",\n  "status": "success",\n  "data": {\n    "mpls_data": {\n      "enabled": true,\n      "label_blocks": [\n        "NO_LABEL_BLOCKS_CONFIGURED"\n      ],\n      "interfaces": [\n        {\n          "name": "GigabitEthernet0/0/0/0",\n          "mpls_enabled": true\n        },\n        {\n          "name": "GigabitEthernet0/0/0/1",\n          "mpls_enabled": true\n        },\n        {\n          "name": "GigabitEthernet0/0/0/2",\n          "mpls_enabled": true\n        },\n        {\n          "name": "GigabitEthernet0/0/0/3",\n          "mpls_enabled": true\n        }\n      ],\n      "global_settings": {\n        "null_label": "openconfig-mpls-types:IMPLICIT",\n        "ttl_propagation": true\n      },\n      "summary": "MPLS Configuration Summary:\\n- TTL Propagation: Enabled\\n\\nMPLS Label Blocks:\\n- No label blocks configured\\n\\nMPLS-Enabled Interfaces:\\n- GigabitEthernet0/0/0/0\\n- GigabitEthernet0/0/0/1\\n- GigabitEthernet0/0/0/2\\n- GigabitEthernet0/0/0/3"\n    },\n    "summary": {\n      "summary": "MPLS Configuration Summary:\\n- TTL Propagation: Enabled\\n\\nMPLS Label Blocks:\\n- No label blocks configured\\n\\nMPLS-Enabled Interfaces:\\n- GigabitEthernet0/0/0/0\\n- GigabitEthernet0/0/0/1\\n- GigabitEthernet0/0/0/2\\n- GigabitEthernet0/0/0/3"\n    }\n  },\n  "metadata": {\n    "include_details": false\n  },\n  "error_response": null,\n  "feature_not_found_response": null\n}',
            name="get_mpls_info",
            id="5f767633-74de-4086-8b26-b7bad61acb8f",
            tool_call_id="call_ejuN4FJRtn2JSJYV5MVKGQrg",
        ),
        ToolMessage(
            content='{\n  "device_name": "xrd-5",\n  "ip_address": "10.10.20.105",\n  "nos": "iosxr",\n  "operation_type": "routing_info",\n  "status": "partial_success",\n  "data": {\n    "routing_protocols": [\n      {\n        "protocol": "isis",\n        "detailed_data": {},\n        "summary": "ISIS Router Information:\\n  Network Entity Title (NET): 49.0100.0100.0100.0105.00\\n  Level Capability: LEVEL_1_2\\n  Segment Routing: Disabled\\n\\nISIS Interfaces:\\n  GigabitEthernet0/0/0/0: Enabled, Active\\n    Level-2: Enabled\\n  GigabitEthernet0/0/0/1: Enabled, Active\\n    Level-2: Enabled\\n  GigabitEthernet0/0/0/2: Enabled, Active\\n    Level-1: Enabled\\n  GigabitEthernet0/0/0/3: Enabled, Active\\n    Level-2: Enabled\\n  Loopback0: Enabled, Passive\\n    Level-1: Enabled\\n    Level-2: Enabled\\n  Loopback1: Enabled, Passive\\n    Level-1: Enabled\\n    Level-2: Enabled\\n\\nISIS Adjacencies:\\n  GigabitEthernet0/0/0/0 -> 0100.0100.0106 (100.105.106.106)\\n    Level: 2, State: UP\\n  GigabitEthernet0/0/0/1 -> 0100.0100.0103 (100.103.105.103)\\n    Level: 2, State: UP\\n  GigabitEthernet0/0/0/2 -> 0100.0100.0101 (100.101.105.101)\\n    Level: 1, State: UP\\n  GigabitEthernet0/0/0/3 -> 0100.0100.0108 (100.105.108.108)\\n    Level: 2, State: UP"\n      }\n    ]\n  },\n  "metadata": {\n    "protocol": "bgp, isis",\n    "include_details": false,\n    "successful_protocols": 1,\n    "failed_protocols": 0,\n    "feature_not_found_protocols": 1,\n    "total_protocols": 2,\n    "protocol_statuses": {\n      "bgp": "feature_not_available",\n      "isis": "success"\n    },\n    "protocol_errors": {\n      "bgp": {\n        "type": "feature_not_found",\n        "message": "Feature not found on device xrd-5: GRPC ERROR Host: 10.10.20.105:57777, Error: Requested element(s) not found: \'bgp\'"\n      }\n    }\n  },\n  "error_response": null,\n  "feature_not_found_response": null\n}',
            name="get_routing_info",
            id="efa03d44-89bb-4c37-8e6e-9fa8b2613a07",
            tool_call_id="call_1x7s57U3h42tGzj0GTLGw3BO",
        ),
        ToolMessage(
            content='{\n  "device_name": "xrd-5",\n  "ip_address": "10.10.20.105",\n  "nos": "iosxr",\n  "operation_type": "vpn_info",\n  "status": "success",\n  "data": {},\n  "metadata": {\n    "message": "No VRFs found",\n    "total_vrfs_on_device": 0,\n    "vrfs_returned": 0,\n    "vrf_filter_applied": false,\n    "vrf_filter": null,\n    "include_details": false,\n    "excluded_internal_vrfs": [\n      "default",\n      "**iid"\n    ]\n  },\n  "error_response": null,\n  "feature_not_found_response": null\n}',
            name="get_vpn_info",
            id="ba3765ee-c345-4389-8cc3-54748bc7e301",
            tool_call_id="call_ctTQ4a380hy3FQOaqmjvdr9P",
        ),
        ToolMessage(
            content='{\n  "device_name": "xrd-5",\n  "ip_address": "10.10.20.105",\n  "nos": "iosxr",\n  "operation_type": "logs",\n  "status": "success",\n  "data": {\n    "logs": [],\n    "summary": {\n      "count": 0,\n      "filter_info": {\n        "keywords": null,\n        "filter_minutes": 5,\n        "show_all_logs": false\n      }\n    },\n    "filters_applied": {\n      "keywords": null,\n      "filter_minutes": 5,\n      "show_all_logs": false\n    }\n  },\n  "metadata": {},\n  "error_response": null,\n  "feature_not_found_response": null\n}',
            name="get_logs",
            id="93483397-5e64-4dca-9077-ed3bca467d67",
            tool_call_id="call_3KJ4PgmWgKyulGDUYoI89oAF",
        ),
        ToolMessage(
            content='{\n  "device_name": "xrd-5",\n  "ip_address": "10.10.20.105",\n  "nos": "iosxr",\n  "operation_type": "device_profile",\n  "status": "success",\n  "data": {\n    "profile": {\n      "is_mpls_enabled": true,\n      "is_isis_enabled": true,\n      "is_bgp_l3vpn_enabled": false,\n      "is_route_reflector": false,\n      "has_vpn_ipv4_unicast_bgp": false,\n      "role": "P"\n    }\n  },\n  "metadata": {},\n  "error_response": null,\n  "feature_not_found_response": null\n}',
            name="get_device_profile_api",
            id="ea431943-b568-432b-b02c-e94107381e24",
            tool_call_id="call_5n0IhO9PiZfLQxJ4qIFKVFFA",
        ),
        AIMessage(
            content="Here is the general health check for device xrd-5.\n\nExecutive summary\n- Overall status: Healthy and operational. All core services responding, MPLS and ISIS routing active, no VPNs or BGP L3VPN configured, and no recent logs signaling issues.\n- Notable items: A minor XR freeze-monitor warning was observed (delay ~100 ms). This is a low-severity indicator and should be monitored, but it does not reflect an immediate failure.\n\nKey findings\n- System health\n  - Hostname: xrd-5\n  - Software version: 24.4.1.26I\n  - Timezone: Universal\n  - Uptime: 26d 17h 39m 26s\n  - Memory: ~25.2 GB physical\n  - Current time: 2025-08-17T10:04:26Z\n  - gRPC server: ENABLED (DEFAULT, port 57777)\n  - Notable message: XRd freeze-monitor delay of 100 ms detected (possible host/VM freeze). Monitor trend; not an immediate fault.\n\n- Interfaces\n  - Total interfaces: 8\n  - Admin up: 8, Admin down: 0\n  - Operational up: 8, Operational down: 0\n  - Interfaces with IPs: 7\n  - Management interface: MgmtEth0/RP0/CPU0/0 with IP 10.10.20.105/24\n  - Observed interfaces: GigabitEthernet0/0/0/0, 0/1, 0/2, 0/3, Loopback0, Loopback1, Null0\n  - Status: All interfaces UP and RUNNING; IPs appear in the expected ranges for non-managed data links and loopbacks.\n\n- MPLS\n  - MPLS enabled: Yes\n  - Interfaces with MPLS: Gi0/0/0/0, Gi0/0/0/1, Gi0/0/0/2, Gi0/0/0/3\n  - Label blocks: No label blocks configured\n  - TTL propagation: Enabled\n  - Global settings: Default null_label type IMPLICIT\n\n- ISIS routing\n  - ISIS enabled: Yes\n  - NET: 49.0100.0100.0100.0105.00\n  - Levels: 1 and 2 enabled (Level capability: LEVEL_1_2)\n  - Adjacencies (sample): \n    - Gi0/0/0/0 -> 100.105.106.106 (UP, Level 2)\n    - Gi0/0/0/1 -> 100.103.105.103 (UP, Level 2)\n    - Gi0/0/0/2 -> 100.101.105.101 (UP, Level 1)\n    - Gi0/0/0/3 -> 100.105.108.108 (UP, Level 2)\n  - Loopbacks (passive): Loopback0, Loopback1 (Enabled, Passive)\n  - Overall ISIS state: Active and forming adjacencies; protocol healthy.\n\n- BGP L3VPN\n  - BGP L3VPN enabled: False/Unavailable on this device\n  - Device reported as feature_not_available for BGP (BGp feature not found in this device context)\n  - Summary: BGP L3VPN not active or supported in this deployment context\n\n- VPNs/VRFs\n  - VRFs found: 0\n  - VPN IPv4 Unicast via BGP: False\n  - vpn_info response: No VRFs found\n\n- Logs\n  - Recent logs: None (within last 5 minutes)\n  - Log count: 0\n  - Filter: No keywords; last 5 minutes\n\n- Device profile\n  - is_mpls_enabled: true\n  - is_isis_enabled: true\n  - is_bgp_l3vpn_enabled: false\n  - is_route_reflector: false\n  - has_vpn_ipv4_unicast_bgp: false\n  - role: P (Provider)\n  - Notes: Profile aligns with a P-rated router primarily handling MPLS/ISIS transit; no VPN or L3VPN services currently configured.\n\nOperational readiness\n- Forwarding readiness: Good. MPLS and ISIS are healthy; interfaces are up; no MR (management) issues detected.\n- VPN/BGP readiness: Not ready for VPN/L3VPN services or BGP L3VPN addressing without feature enablement/licensing or device capability changes.\n- Observability: System time, memory, and gRPC appear healthy. No recent error logs. Freeze-monitor warning should be watched but is not currently affecting operations.\n\nRecommended actions (optional)\n- If BGP L3VPN or VPN services are required:\n  - Verify device capability/licensing and firmware support for BGP on this IOS-XR release. The feature_not_available indicates tool access limitation or actual feature absence.\n  - If needed, plan for upgrade or licensing changes, or deploy a device that supports BGP L3VPN in this role.\n- Freeze-monitor attention:\n  - Correlate with CPU/memory usage and any virtualization/host health metrics.\n  - If the warning recurs or coincides with spikes in latency or dropped packets, escalate to collect more detailed system and process-level telemetry (CPU/mem, process times, disk I/O).\n- VPN/VRF planning:\n  - If future VPN deployment is planned, define VRF instances and BGP advertisement schemes in alignment with ISIS/LDP/MPLS design.\n- Routine checks:\n  - Schedule periodic health checks (every 6–12 hours) to confirm no change in BGP availability, VPN/VPR presence, and to re-check the freeze-monitor status.\n\nData snapshot (highlights)\n- System: xrd-5 | 24.4.1.26I | uptime 26d 17h 39m 26s | Mem ~25.2 GB\n- Interfaces: 8 total | 8 admin up | 7 with IP | MgmtEth0/RP0/CPU0/0: 10.10.20.105/24\n- MPLS: enabled | TTL propagation: enabled | 4 MPLS-enabled interfaces\n- ISIS: enabled | NET 49.0100.0100.0100.0105.00 | adjacencies up\n- BGP L3VPN: not available\n- VPNs/VRFs: none\n- Logs: none in last 5 minutes\n- Role: P (Provider) | is_route_reflector: false\n\nBottom line\nxrd-5 is operating normally and ready for MPLS/ISIS-based traffic as a P-router. BGP L3VPN and VPN features are not active or supported in its current configuration. The only watchpoint is the occasional XR freeze-monitor warning; monitor that health signal to ensure it doesn’t correlate with intermittent performance degradation. If BGP/L3VPN or VPN services are required, plan for capability/licensing checks or a device upgrade.",
            additional_kwargs={},
            response_metadata={
                "finish_reason": "stop",
                "model_name": "gpt-5-nano-2025-08-07",
                "service_tier": "default",
            },
            id="run--a99cac17-e838-4a46-93c2-0d4d9452ea9c",
        ),
    ]
}
